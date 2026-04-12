from pathlib import Path
import os

from pyspider.core.contracts import (
    AutoscaledFrontier,
    FailureClassifier,
    FileArtifactStore,
    FrontierConfig,
    ObservabilityCollector,
    RequestFingerprint,
)
from pyspider.core.incremental import IncrementalCrawler
from pyspider.core.models import Request, Response
from pyspider.core.spider import Spider


def test_request_fingerprint_is_stable_for_same_request():
    first = Request(
        url="https://example.com", headers={"Accept": "text/html"}, meta={"page": 1}
    )
    second = Request(
        url="https://example.com", headers={"Accept": "text/html"}, meta={"page": 1}
    )

    assert RequestFingerprint.from_request(first) == RequestFingerprint.from_request(
        second
    )


def test_frontier_respects_per_domain_backpressure_and_restores_checkpoint(tmp_path):
    frontier = AutoscaledFrontier(
        FrontierConfig(
            checkpoint_dir=str(tmp_path / "checkpoints"),
            checkpoint_id="demo-frontier",
            max_inflight_per_domain=1,
            max_concurrency=4,
        )
    )
    first = Request(url="https://example.com/a", priority=10)
    second = Request(url="https://example.com/b", priority=5)
    other = Request(url="https://other.example.com/c", priority=1)

    assert frontier.push(first) is True
    assert frontier.push(second) is True
    assert frontier.push(other) is True

    leased_first = frontier.lease()
    leased_other = frontier.lease()

    assert leased_first is not None
    assert leased_other is not None
    assert leased_first.url == "https://example.com/a"
    assert leased_other.url == "https://other.example.com/c"

    frontier.persist()

    restored = AutoscaledFrontier(
        FrontierConfig(
            checkpoint_dir=str(tmp_path / "checkpoints"),
            checkpoint_id="demo-frontier",
            max_inflight_per_domain=1,
        )
    )
    assert restored.load() is True
    pending = restored.snapshot()["pending"]
    assert [item["url"] for item in pending] == ["https://example.com/b"]


def test_frontier_autoscales_down_on_failures():
    frontier = AutoscaledFrontier(FrontierConfig(max_concurrency=6))
    request = Request(url="https://example.com/a")
    frontier.push(request)
    leased = frontier.lease()
    assert leased is not None

    frontier.ack(
        leased, success=False, latency_ms=5000, error="rate limit", status_code=429
    )

    assert frontier.recommended_concurrency == 1
    assert frontier.dead_letter_count == 0


def test_frontier_synthetic_soak_and_recovery_metrics(tmp_path):
    frontier = AutoscaledFrontier(
        FrontierConfig(
            checkpoint_dir=str(tmp_path / "checkpoints"),
            checkpoint_id="soak-frontier",
            min_concurrency=1,
            max_concurrency=8,
            max_inflight_per_domain=2,
        )
    )
    requests = [
        Request(
            url=f"https://example.com/item/{idx}",
            priority=idx % 3,
            meta={"mode": "dead-letter" if idx % 7 == 0 else "success"},
        )
        for idx in range(24)
    ]
    for request in requests:
        assert frontier.push(request) is True

    processed = 0
    failed = 0
    dead_lettered = 0
    for idx in range(80):
        leased = frontier.lease()
        if leased is None:
            break
        if leased.meta.get("mode") == "dead-letter":
            failed += 1
            frontier.ack(
                leased,
                success=False,
                latency_ms=1800,
                error="synthetic timeout",
                status_code=408,
                max_retries=1,
            )
        else:
            processed += 1
            frontier.ack(
                leased, success=True, latency_ms=40, status_code=200, max_retries=1
            )
        dead_lettered = frontier.dead_letter_count

    frontier.persist()
    restored = AutoscaledFrontier(
        FrontierConfig(
            checkpoint_dir=str(tmp_path / "checkpoints"),
            checkpoint_id="soak-frontier",
            min_concurrency=1,
            max_concurrency=8,
            max_inflight_per_domain=2,
        )
    )
    assert restored.load() is True
    snapshot = restored.snapshot()

    assert processed > 0
    assert failed > 0
    assert dead_lettered >= 1
    assert snapshot["dead_letters"]
    assert 1 <= frontier.recommended_concurrency <= 8


def test_incremental_crawler_persists_and_restores_delta_state(tmp_path):
    store_path = tmp_path / "incremental.json"
    crawler = IncrementalCrawler(store_path=str(store_path))
    changed = crawler.update_cache(
        "https://example.com/a",
        etag="etag-1",
        last_modified="Sat, 11 Apr 2026 00:00:00 GMT",
        content=b"alpha",
        status_code=200,
    )

    assert changed is True
    first_token = crawler.delta_token("https://example.com/a")
    assert first_token

    crawler.save()

    restored = IncrementalCrawler(store_path=str(store_path))
    assert restored.delta_token("https://example.com/a") == first_token
    assert restored.get_conditional_headers("https://example.com/a") == {
        "If-None-Match": "etag-1",
        "If-Modified-Since": "Sat, 11 Apr 2026 00:00:00 GMT",
    }


def test_observability_and_artifact_store_capture_runtime_evidence(tmp_path):
    observability = ObservabilityCollector()
    trace_id = observability.start_trace("crawl")
    record = FileArtifactStore(tmp_path).put_bytes("frontier-state", "json", b"{}")

    classification = observability.record_result(
        request=Request(url="https://example.com"),
        latency_ms=50,
        status_code=403,
        error="captcha challenge",
        trace_id=trace_id,
    )
    observability.end_trace(trace_id, artifact=record.path)

    assert classification == "blocked"
    assert FailureClassifier.classify(error="captcha challenge") == "anti_bot"
    assert Path(record.path).exists()
    assert observability.summary()["traces"] == 1
    assert "spider_runtime_events_total" in observability.to_prometheus_text()
    assert (
        observability.to_otel_payload()["resource"]["service.name"] == "spider-runtime"
    )


def test_spider_runtime_uses_frontier_and_observability(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    spider = Spider(name="contract-spider", thread_count=1, max_retries=0)
    spider.configure_frontier(
        checkpoint_dir=str(tmp_path / "checkpoints"),
        checkpoint_id="contract-spider",
        max_inflight_per_domain=1,
    )
    spider.set_incremental(store_path=str(tmp_path / "cache" / "incremental.json"))
    spider._artifact_store = FileArtifactStore(tmp_path / "observability")

    def fake_download(req: Request) -> Response:
        return Response(
            url=req.url,
            status_code=200,
            headers={"Content-Type": "text/html"},
            content=b"<html><title>ok</title></html>",
            text="<html><title>ok</title></html>",
            request=req,
            duration=0.01,
            error=None,
        )

    spider.downloader.download = fake_download
    spider.set_start_urls("https://example.com")
    spider.start()

    stats = spider.get_runtime_stats()
    assert stats["frontier"]["pending"] == 0
    assert stats["observability"]["events"] >= 2
    assert os.path.exists(tmp_path / "cache" / "incremental.json")
    artifacts = spider._artifact_store.list()
    assert any(record.name.endswith("-graph") for record in artifacts)
