from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def run_tool(script: str, *args: str) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, "-B", str(TOOLS / script), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(completed.stdout)
    return completed.returncode, payload


def test_jobdir_tool_round_trip(tmp_path: Path) -> None:
    jobdir = tmp_path / "jobdir"

    code, payload = run_tool(
        "jobdir_tool.py",
        "init",
        "--path",
        str(jobdir),
        "--runtime",
        "python",
        "--url",
        "https://example.com",
    )
    assert code == 0
    assert payload["state"] == "running"
    assert (jobdir / "job-state.json").exists()

    code, payload = run_tool("jobdir_tool.py", "pause", "--path", str(jobdir))
    assert code == 0
    assert payload["state"] == "paused"

    code, payload = run_tool("jobdir_tool.py", "resume", "--path", str(jobdir))
    assert code == 0
    assert payload["state"] == "running"

    code, payload = run_tool("jobdir_tool.py", "status", "--path", str(jobdir))
    assert code == 0
    assert payload["runtime"] == "python"
    assert payload["urls"] == ["https://example.com"]

    code, payload = run_tool("jobdir_tool.py", "clear", "--path", str(jobdir))
    assert code == 0
    assert payload["removed"]
    assert not (jobdir / "job-state.json").exists()


def test_http_cache_tool_seed_status_and_clear(tmp_path: Path) -> None:
    cache_path = tmp_path / "incremental.json"

    code, payload = run_tool(
        "http_cache_tool.py",
        "seed",
        "--path",
        str(cache_path),
        "--url",
        "https://example.com",
        "--status-code",
        "304",
        "--etag",
        "demo",
    )
    assert code == 0
    assert payload["status_code"] == 304

    code, payload = run_tool("http_cache_tool.py", "status", "--path", str(cache_path))
    assert code == 0
    assert payload["entry_count"] == 1
    assert payload["urls"] == ["https://example.com"]

    code, payload = run_tool("http_cache_tool.py", "clear", "--path", str(cache_path))
    assert code == 0
    assert payload["entry_count"] == 0


def test_runtime_console_snapshot_and_tail(tmp_path: Path) -> None:
    control_plane = tmp_path / "control-plane"
    control_plane.mkdir()
    (control_plane / "events.jsonl").write_text(
        json.dumps({"topic": "job.started"}) + "\n",
        encoding="utf-8",
    )
    (control_plane / "results.jsonl").write_text(
        json.dumps({"state": "succeeded"}) + "\n",
        encoding="utf-8",
    )
    jobdir = tmp_path / "jobdir"
    jobdir.mkdir()
    (jobdir / "job-state.json").write_text(
        json.dumps({"state": "running"}) + "\n",
        encoding="utf-8",
    )

    code, payload = run_tool(
        "runtime_console.py",
        "snapshot",
        "--control-plane",
        str(control_plane),
        "--jobdir",
        str(jobdir),
        "--lines",
        "5",
    )
    assert code == 0
    assert payload["events"][0]["topic"] == "job.started"
    assert payload["results"][0]["state"] == "succeeded"
    assert payload["job_state"]["state"] == "running"

    code, payload = run_tool(
        "runtime_console.py",
        "tail",
        "--control-plane",
        str(control_plane),
        "--stream",
        "events",
        "--lines",
        "5",
    )
    assert code == 0
    assert "events" in payload
    assert "results" not in payload


def test_audit_console_snapshot_and_tail(tmp_path: Path) -> None:
    control_plane = tmp_path / "control-plane"
    control_plane.mkdir()
    (control_plane / "events.jsonl").write_text(
        json.dumps({"topic": "job.started"}) + "\n",
        encoding="utf-8",
    )
    (control_plane / "results.jsonl").write_text(
        json.dumps({"state": "succeeded"}) + "\n",
        encoding="utf-8",
    )
    (control_plane / "demo-audit.jsonl").write_text(
        json.dumps({"type": "job.result", "payload": {"job_name": "demo"}}) + "\n",
        encoding="utf-8",
    )
    (control_plane / "demo-connector.jsonl").write_text(
        json.dumps({"job_name": "demo", "state": "succeeded"}) + "\n",
        encoding="utf-8",
    )

    code, payload = run_tool(
        "audit_console.py",
        "snapshot",
        "--control-plane",
        str(control_plane),
        "--job-name",
        "demo",
        "--lines",
        "5",
    )
    assert code == 0
    assert payload["events"][0]["topic"] == "job.started"
    assert payload["results"][0]["state"] == "succeeded"
    assert payload["audit_files"][0]["name"] == "demo-audit.jsonl"
    assert payload["connector_files"][0]["name"] == "demo-connector.jsonl"

    code, payload = run_tool(
        "audit_console.py",
        "tail",
        "--control-plane",
        str(control_plane),
        "--job-name",
        "demo",
        "--stream",
        "audit",
        "--lines",
        "5",
    )
    assert code == 0
    assert payload["stream"] == "audit"
    assert "audit_files" in payload
    assert "results" not in payload


def test_spider_contracts_init_and_validate(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "scrapy-project.json").write_text(
        json.dumps({"name": "demo", "runtime": "python"}) + "\n",
        encoding="utf-8",
    )
    (project / "spider-framework.yaml").write_text(
        "version: 1\nproject:\n  name: demo\nruntime: python\n",
        encoding="utf-8",
    )

    code, payload = run_tool("spider_contracts.py", "init", "--project", str(project))
    assert code == 0
    assert Path(payload["contracts_manifest"]).exists()
    assert Path(payload["routes_manifest"]).exists()

    code, payload = run_tool(
        "spider_contracts.py", "validate", "--project", str(project)
    )
    assert code == 0
    assert payload["summary"] == "passed"


def test_playwright_fetch_trace_and_codegen(tmp_path: Path) -> None:
    page = tmp_path / "fixture.html"
    page.write_text(
        "<html><head><title>Fixture</title></head><body>ok</body></html>",
        encoding="utf-8",
    )
    url = page.resolve().as_uri()
    trace_path = tmp_path / "artifacts" / "page.trace.zip"
    har_path = tmp_path / "artifacts" / "page.har"
    html_path = tmp_path / "artifacts" / "page.html"
    screenshot_path = tmp_path / "artifacts" / "page.png"
    code_path = tmp_path / "artifacts" / "codegen.py"
    routes_path = tmp_path / "contracts" / "routes.json"
    routes_path.parent.mkdir(parents=True, exist_ok=True)
    routes_path.write_text(json.dumps({"routes": []}) + "\n", encoding="utf-8")

    code, payload = run_tool(
        "playwright_fetch.py",
        "--tooling-command",
        "trace",
        "--url",
        url,
        "--trace-path",
        str(trace_path),
        "--har-path",
        str(har_path),
        "--html",
        str(html_path),
        "--screenshot",
        str(screenshot_path),
    )
    assert code == 0
    assert Path(payload["artifacts"]["trace"]).exists()
    assert Path(payload["artifacts"]["har"]).exists()
    assert Path(payload["artifacts"]["html"]).exists()
    assert Path(payload["artifacts"]["screenshot"]).exists()
    with zipfile.ZipFile(trace_path) as archive:
        assert "trace.json" in archive.namelist()

    code, payload = run_tool(
        "playwright_fetch.py",
        "--tooling-command",
        "codegen",
        "--url",
        url,
        "--route-manifest",
        str(routes_path),
        "--codegen-out",
        str(code_path),
        "--codegen-language",
        "python",
    )
    assert code == 0
    assert Path(payload["output"]).exists()
    assert "async_playwright" in code_path.read_text(encoding="utf-8")
