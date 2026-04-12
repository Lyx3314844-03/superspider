from __future__ import annotations

import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_tool(name: str):
    path = ROOT / "tools" / name
    spec = importlib.util.spec_from_file_location(name.replace(".", "_"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _capture_json(func, *args):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = func(*args)
    return exit_code, json.loads(buffer.getvalue())


def test_jobdir_tool_manages_pause_resume_manifest(tmp_path):
    tool = _load_tool("jobdir_tool.py")
    jobdir = tmp_path / "jobdir"

    exit_code, payload = _capture_json(
        tool.main, ["init", "--path", str(jobdir), "--runtime", "python", "--url", "https://example.com"]
    )
    assert exit_code == 0
    assert payload["state"] == "ready"

    exit_code, payload = _capture_json(tool.main, ["pause", "--path", str(jobdir)])
    assert exit_code == 0
    assert payload["state"] == "paused"

    exit_code, payload = _capture_json(tool.main, ["resume", "--path", str(jobdir)])
    assert exit_code == 0
    assert payload["state"] == "running"

    manifest = json.loads((jobdir / "job-state.json").read_text(encoding="utf-8"))
    assert manifest["runtime"] == "python"
    assert manifest["state"] == "running"
    assert manifest["crawl"]["pending_urls"] == ["https://example.com"]


def test_http_cache_tool_seeds_reports_and_clears_entries(tmp_path):
    tool = _load_tool("http_cache_tool.py")
    cache_path = tmp_path / "cache" / "incremental.json"

    exit_code, payload = _capture_json(
        tool.main,
        [
            "seed",
            "--path",
            str(cache_path),
            "--url",
            "https://example.com",
            "--status-code",
            "304",
            "--etag",
            "demo-etag",
        ],
    )
    assert exit_code == 0
    assert payload["url"] == "https://example.com"

    exit_code, payload = _capture_json(tool.main, ["status", "--path", str(cache_path)])
    assert exit_code == 0
    assert payload["entries"] == 1
    assert payload["keys"] == ["https://example.com"]

    exit_code, payload = _capture_json(tool.main, ["clear", "--path", str(cache_path)])
    assert exit_code == 0
    assert payload["cleared"] is True
    assert not cache_path.exists()


def test_runtime_console_tool_reads_control_plane_and_jobdir(tmp_path):
    tool = _load_tool("runtime_console.py")
    control_plane = tmp_path / "artifacts" / "control-plane"
    control_plane.mkdir(parents=True)
    (control_plane / "results.jsonl").write_text('{"id":"r1"}\n{"id":"r2"}\n', encoding="utf-8")
    (control_plane / "events.jsonl").write_text('{"event":"start"}\n{"event":"done"}\n', encoding="utf-8")

    jobdir = tmp_path / "jobdir"
    jobdir.mkdir()
    (jobdir / "job-state.json").write_text(json.dumps({"state": "paused", "runtime": "go"}), encoding="utf-8")

    exit_code, payload = _capture_json(
        tool.main,
        [
            "snapshot",
            "--control-plane",
            str(control_plane),
            "--jobdir",
            str(jobdir),
            "--lines",
            "1",
        ],
    )
    assert exit_code == 0
    assert payload["results_exists"] is True
    assert payload["events_exists"] is True
    assert payload["results_tail"] == ['{"id":"r2"}']
    assert payload["jobdir"]["state"] == "paused"

    exit_code, payload = _capture_json(
        tool.main,
        ["tail", "--control-plane", str(control_plane), "--stream", "events", "--lines", "1"],
    )
    assert exit_code == 0
    assert payload["streams"]["events"] == ['{"event":"done"}']


def test_spider_contracts_tool_initializes_and_validates_project(tmp_path):
    tool = _load_tool("spider_contracts.py")
    project = tmp_path / "project"

    exit_code, payload = _capture_json(tool.main, ["init", "--project", str(project)])
    assert exit_code == 0
    assert payload["command"] == "scrapy contracts init"

    exit_code, payload = _capture_json(tool.main, ["validate", "--project", str(project)])
    assert exit_code == 0
    assert payload["summary"] == "passed"
