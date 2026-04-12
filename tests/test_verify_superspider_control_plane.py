from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_superspider_control_plane
from superspider_control_plane import build_worker_catalog


ROOT = Path(__file__).resolve().parents[1]


def _capability_payload(runtime: str) -> dict:
    return {
        "command": "capabilities",
        "runtime": runtime,
        "runtimes": ["http", "browser", "media", "ai"],
        "shared_contracts": [
            "shared-cli",
            "runtime-core",
            "web-control-plane",
        ],
        "operator_products": {
            "debug_console": {"control_plane_jsonl": True},
        },
    }


def test_build_worker_catalog_expands_framework_payloads_into_runtime_workers():
    workers = build_worker_catalog(
        {
            "javaspider": _capability_payload("java"),
            "pyspider": _capability_payload("python"),
        }
    )

    java_workers = [worker for worker in workers if "javaspider" in worker.tags]
    python_workers = [worker for worker in workers if "pyspider" in worker.tags]

    assert sorted({worker.runtime for worker in java_workers}) == ["ai", "browser", "http", "media"]
    assert all(worker.graph for worker in java_workers)
    assert all(worker.http and worker.browser and worker.media and worker.ai for worker in python_workers)


def test_collect_superspider_control_plane_report_uses_runtime_payloads(monkeypatch):
    monkeypatch.setattr(
        verify_superspider_control_plane,
        "_load_runtime_capability_payloads",
        lambda root: (
            {
                "javaspider": _capability_payload("java"),
                "gospider": _capability_payload("go"),
                "pyspider": _capability_payload("python"),
                "rustspider": _capability_payload("rust"),
            },
            [{"name": "payloads", "status": "passed", "details": "loaded"}],
        ),
    )

    report = verify_superspider_control_plane.collect_superspider_control_plane_report(ROOT)

    assert report["command"] == "verify-superspider-control-plane"
    assert report["summary"] == "passed"
    assert report["frameworks"]["pyspider"]["summary"] == "passed"
    assert any(check["name"] == "browser-route" and check["status"] == "passed" for check in report["checks"])


def test_main_prints_json(monkeypatch, capsys):
    monkeypatch.setattr(
        verify_superspider_control_plane,
        "collect_superspider_control_plane_report",
        lambda root: {
            "command": "verify-superspider-control-plane",
            "summary": "passed",
            "summary_text": "3 passed, 0 failed",
            "exit_code": 0,
            "checks": [],
            "frameworks": {},
            "dispatch_plans": [],
        },
    )

    exit_code = verify_superspider_control_plane.main(["--root", str(ROOT), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["command"] == "verify-superspider-control-plane"


def test_superspider_control_plane_schema_exists():
    schema = json.loads(
        (ROOT / "schemas" / "spider-superspider-control-plane-report.schema.json").read_text(encoding="utf-8")
    )

    assert schema["properties"]["command"]["const"] == "verify-superspider-control-plane"
