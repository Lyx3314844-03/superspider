from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import subprocess
import sys
import tempfile
import threading


ROOT = Path(__file__).resolve().parents[1]


def _run_process(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _run(command: list[str], cwd: Path) -> str:
    completed = _run_process(command, cwd)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return _extract_json_output(completed.stdout)


def _extract_json_output(output: str) -> str:
    first_brace = output.find("{")
    return output[first_brace:] if first_brace >= 0 else output


def _compile_java_cli() -> None:
    completed = _run_process(
        ["cmd", "/c", "mvn", "-q", "compile", "dependency:copy-dependencies"],
        ROOT / "javaspider",
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


class _GraphHTMLHandler(BaseHTTPRequestHandler):
    html = "<html><head><title>Matrix Graph Title</title></head><body><a href='https://example.com/docs'>Docs</a><img src='https://example.com/image.png'/></body></html>"

    def do_GET(self):  # noqa: N802
        body = self.html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A003
        return


def _start_matrix_server() -> tuple[HTTPServer, str]:
    server = HTTPServer(("127.0.0.1", 0), _GraphHTMLHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}"


def _assert_common_job_envelope(payload: dict, *, job_name: str, runtime: str, url: str) -> None:
    assert payload["job_name"] == job_name
    assert payload["runtime"] == runtime
    if "url" in payload:
        assert payload["url"] == url
    if "state" in payload:
        assert payload["state"] == "succeeded"
    if "error" in payload:
        assert payload["error"] in ("", None)
    if "metrics" in payload:
        latency = payload["metrics"].get("latency_ms", 0)
        assert latency >= 0


def test_go_job_runtime_matrix_command():
    with tempfile.TemporaryDirectory() as tmpdir:
        job_path = Path(tmpdir) / "go-job.json"
        output_path = Path(tmpdir) / "go-output.json"
        job_path.write_text(json.dumps({
            "name": "go-matrix-job",
            "runtime": "ai",
            "target": {"url": "https://example.com"},
            "output": {"format": "json", "path": str(output_path)},
            "metadata": {"mock_extract": {"title": "Go Matrix Title"}},
        }), encoding="utf-8")

        output = _run(
            ["go", "run", "./cmd/gospider", "job", "--file", str(job_path)],
            ROOT / "gospider",
        )
        payload = json.loads(output)
        _assert_common_job_envelope(
            payload,
            job_name="go-matrix-job",
            runtime="ai",
            url="https://example.com",
        )
        assert payload["extract"]["title"] == "Go Matrix Title"
        assert output_path.exists()
        assert "Go Matrix Title" in output_path.read_text(encoding="utf-8")


def test_python_job_runtime_matrix_command():
    with tempfile.TemporaryDirectory() as tmpdir:
        job_path = Path(tmpdir) / "py-job.json"
        output_path = Path(tmpdir) / "py-output.json"
        job_path.write_text(json.dumps({
            "name": "py-matrix-job",
            "runtime": "ai",
            "target": {"url": "https://example.com"},
            "extract": [{"field": "title", "type": "ai"}],
            "output": {"format": "json", "path": str(output_path)},
            "metadata": {"content": "<title>Py Matrix Title</title>"},
        }), encoding="utf-8")

        output = _run(
            [sys.executable, "-m", "pyspider", "job", "--file", str(job_path)],
            ROOT,
        )
        payload = json.loads(output)
        _assert_common_job_envelope(
            payload,
            job_name="py-matrix-job",
            runtime="ai",
            url="https://example.com",
        )
        assert payload["extract"]["title"] == "Py Matrix Title"
        assert payload["output"]["format"] == "json"
        assert payload["output"]["path"] == str(output_path)
        assert output_path.exists()
        assert "Py Matrix Title" in output_path.read_text(encoding="utf-8")


def test_rust_job_runtime_matrix_command():
    with tempfile.TemporaryDirectory() as tmpdir:
        job_path = Path(tmpdir) / "rust-job.json"
        output_path = Path(tmpdir) / "rust-output.json"
        job_path.write_text(json.dumps({
            "name": "rust-matrix-job",
            "runtime": "media",
            "target": {
                "url": "https://example.com",
                "body": "playlist.m3u8",
            },
            "output": {"format": "json", "path": str(output_path)},
        }), encoding="utf-8")

        output = _run(
            ["cargo", "run", "--quiet", "--", "job", "--file", str(job_path)],
            ROOT / "rustspider",
        )
        payload = json.loads(output)
        _assert_common_job_envelope(
            payload,
            job_name="rust-matrix-job",
            runtime="media",
            url="https://example.com",
        )
        assert "hls" in payload["detected_media"]
        assert output_path.exists()
        assert "\"state\": \"succeeded\"" in output_path.read_text(encoding="utf-8")


def test_java_job_runtime_matrix_command():
    with tempfile.TemporaryDirectory() as tmpdir:
        job_path = Path(tmpdir) / "java-job.json"
        output_path = Path(tmpdir) / "java-output.json"
        job_path.write_text(json.dumps({
            "name": "java-matrix-job",
            "runtime": "browser",
            "target": {"url": "https://example.com"},
            "extract": [{"field": "title", "type": "css", "expr": "title"}],
            "output": {"format": "json", "path": str(output_path)},
            "metadata": {"mock_extract": {"title": "Java Matrix Title"}},
        }), encoding="utf-8")

        _compile_java_cli()

        output = _run(
            [
                "java",
                "-cp",
                "target/classes;target/dependency/*",
                "com.javaspider.EnhancedSpider",
                "job",
                "--file",
                str(job_path),
            ],
            ROOT / "javaspider",
        )
        payload = json.loads(output)
        _assert_common_job_envelope(
            payload,
            job_name="java-matrix-job",
            runtime="browser",
            url="https://example.com",
        )
        assert payload["extract"]["title"] == "Java Matrix Title"
        assert payload["output"]["path"] == str(output_path)
        assert output_path.exists()
        assert "Java Matrix Title" in output_path.read_text(encoding="utf-8")


def test_cross_runtime_job_commands_support_failure_injection_contract():
    with tempfile.TemporaryDirectory() as tmpdir:
        _compile_java_cli()
        reason = "synthetic failure"

        cases = [
            (
                ["go", "run", "./cmd/gospider", "job", "--file", str(Path(tmpdir) / "go-fail.json")],
                ROOT / "gospider",
                {
                    "name": "go-fail",
                    "runtime": "ai",
                    "target": {"url": "https://example.com"},
                    "output": {"format": "json", "path": str(Path(tmpdir) / "go-fail-output.json")},
                    "metadata": {"fail_job": reason},
                },
            ),
            (
                [sys.executable, "-m", "pyspider", "job", "--file", str(Path(tmpdir) / "py-fail.json")],
                ROOT,
                {
                    "name": "py-fail",
                    "runtime": "ai",
                    "target": {"url": "https://example.com"},
                    "output": {"format": "json", "path": str(Path(tmpdir) / "py-fail-output.json")},
                    "metadata": {"fail_job": reason},
                },
            ),
            (
                ["cargo", "run", "--quiet", "--", "job", "--file", str(Path(tmpdir) / "rust-fail.json")],
                ROOT / "rustspider",
                {
                    "name": "rust-fail",
                    "runtime": "media",
                    "target": {"url": "https://example.com"},
                    "output": {"format": "json", "path": str(Path(tmpdir) / "rust-fail-output.json")},
                    "metadata": {"fail_job": reason},
                },
            ),
            (
                [
                    "java",
                    "-cp",
                    "target/classes;target/dependency/*",
                    "com.javaspider.EnhancedSpider",
                    "job",
                    "--file",
                    str(Path(tmpdir) / "java-fail.json"),
                ],
                ROOT / "javaspider",
                {
                    "name": "java-fail",
                    "runtime": "browser",
                    "target": {"url": "https://example.com"},
                    "output": {"format": "json", "path": str(Path(tmpdir) / "java-fail-output.json")},
                    "metadata": {"fail_job": reason},
                },
            ),
        ]

        for command, cwd, payload in cases:
            Path(command[-1]).write_text(json.dumps(payload), encoding="utf-8")
            completed = _run_process(command, cwd)
            assert completed.returncode != 0, command
            payload = json.loads(_extract_json_output(completed.stdout))
            assert payload["state"] == "failed"
            assert "synthetic failure" in payload["error"].lower()


def test_cross_runtime_job_commands_support_mock_antibot_envelope():
    with tempfile.TemporaryDirectory() as tmpdir:
        _compile_java_cli()
        anti_bot = {
            "challenge": "captcha",
            "fingerprint_profile": "synthetic",
            "session_mode": "sticky",
            "stealth": True,
        }
        warnings = ["synthetic anti-bot recovery"]
        cases = [
            (
                ["go", "run", "./cmd/gospider", "job", "--file", str(Path(tmpdir) / "go-antibot.json")],
                ROOT / "gospider",
                {
                    "name": "go-antibot",
                    "runtime": "ai",
                    "target": {"url": "https://example.com"},
                    "output": {"format": "json", "path": str(Path(tmpdir) / "go-antibot-output.json")},
                    "metadata": {
                        "mock_extract": {"title": "Go AntiBot"},
                        "mock_antibot": anti_bot,
                        "mock_warnings": warnings,
                    },
                },
            ),
            (
                [sys.executable, "-m", "pyspider", "job", "--file", str(Path(tmpdir) / "py-antibot.json")],
                ROOT,
                {
                    "name": "py-antibot",
                    "runtime": "ai",
                    "target": {"url": "https://example.com"},
                    "extract": [{"field": "title", "type": "ai"}],
                    "output": {"format": "json", "path": str(Path(tmpdir) / "py-antibot-output.json")},
                    "metadata": {
                        "content": "<title>Py AntiBot</title>",
                        "mock_antibot": anti_bot,
                        "mock_warnings": warnings,
                    },
                },
            ),
            (
                ["cargo", "run", "--quiet", "--", "job", "--file", str(Path(tmpdir) / "rust-antibot.json")],
                ROOT / "rustspider",
                {
                    "name": "rust-antibot",
                    "runtime": "media",
                    "target": {"url": "https://example.com", "body": "playlist.m3u8"},
                    "output": {"format": "json", "path": str(Path(tmpdir) / "rust-antibot-output.json")},
                    "metadata": {
                        "mock_antibot": anti_bot,
                        "mock_warnings": warnings,
                    },
                },
            ),
            (
                [
                    "java",
                    "-cp",
                    "target/classes;target/dependency/*",
                    "com.javaspider.EnhancedSpider",
                    "job",
                    "--file",
                    str(Path(tmpdir) / "java-antibot.json"),
                ],
                ROOT / "javaspider",
                {
                    "name": "java-antibot",
                    "runtime": "browser",
                    "target": {"url": "https://example.com"},
                    "extract": [{"field": "title", "type": "css", "expr": "title"}],
                    "output": {"format": "json", "path": str(Path(tmpdir) / "java-antibot-output.json")},
                    "metadata": {
                        "mock_extract": {"title": "Java AntiBot"},
                        "mock_antibot": anti_bot,
                        "mock_warnings": warnings,
                    },
                },
            ),
        ]

        for command, cwd, payload in cases:
            Path(command[-1]).write_text(json.dumps(payload), encoding="utf-8")
            completed = _run_process(command, cwd)
            assert completed.returncode == 0, completed.stderr or completed.stdout
            output_payload = json.loads(_extract_json_output(completed.stdout))
            assert output_payload["anti_bot"]["challenge"] == "captcha"
            assert output_payload["anti_bot"]["session_mode"] == "sticky"
            assert output_payload["anti_bot"]["stealth"] is True
            assert "synthetic anti-bot recovery" in output_payload["warnings"]


def test_cross_runtime_job_commands_support_mock_recovery_envelope():
    with tempfile.TemporaryDirectory() as tmpdir:
        _compile_java_cli()
        anti_bot = {
            "challenge": "captcha",
            "fingerprint_profile": "synthetic",
            "session_mode": "sticky",
            "stealth": True,
        }
        recovery = {
            "strategy": "captcha-solve",
            "recovered": True,
            "events": [
                {"phase": "detect", "signal": "captcha", "status": "passed"},
                {"phase": "mitigate", "action": "solve", "status": "passed"},
                {"phase": "resume", "action": "continue", "status": "passed"},
            ],
        }
        cases = [
            (
                ["go", "run", "./cmd/gospider", "job", "--file", str(Path(tmpdir) / "go-recovery.json")],
                ROOT / "gospider",
                {
                    "name": "go-recovery",
                    "runtime": "ai",
                    "target": {"url": "https://example.com"},
                    "output": {"format": "json", "path": str(Path(tmpdir) / "go-recovery-output.json")},
                    "metadata": {
                        "mock_extract": {"title": "Go Recovery"},
                        "mock_antibot": anti_bot,
                        "mock_recovery": recovery,
                    },
                },
            ),
            (
                [sys.executable, "-m", "pyspider", "job", "--file", str(Path(tmpdir) / "py-recovery.json")],
                ROOT,
                {
                    "name": "py-recovery",
                    "runtime": "ai",
                    "target": {"url": "https://example.com"},
                    "extract": [{"field": "title", "type": "ai"}],
                    "output": {"format": "json", "path": str(Path(tmpdir) / "py-recovery-output.json")},
                    "metadata": {
                        "content": "<title>Py Recovery</title>",
                        "mock_antibot": anti_bot,
                        "mock_recovery": recovery,
                    },
                },
            ),
            (
                ["cargo", "run", "--quiet", "--", "job", "--file", str(Path(tmpdir) / "rust-recovery.json")],
                ROOT / "rustspider",
                {
                    "name": "rust-recovery",
                    "runtime": "media",
                    "target": {"url": "https://example.com", "body": "playlist.m3u8"},
                    "output": {"format": "json", "path": str(Path(tmpdir) / "rust-recovery-output.json")},
                    "metadata": {
                        "mock_antibot": anti_bot,
                        "mock_recovery": recovery,
                    },
                },
            ),
            (
                [
                    "java",
                    "-cp",
                    "target/classes;target/dependency/*",
                    "com.javaspider.EnhancedSpider",
                    "job",
                    "--file",
                    str(Path(tmpdir) / "java-recovery.json"),
                ],
                ROOT / "javaspider",
                {
                    "name": "java-recovery",
                    "runtime": "browser",
                    "target": {"url": "https://example.com"},
                    "extract": [{"field": "title", "type": "css", "expr": "title"}],
                    "output": {"format": "json", "path": str(Path(tmpdir) / "java-recovery-output.json")},
                    "metadata": {
                        "mock_extract": {"title": "Java Recovery"},
                        "mock_antibot": anti_bot,
                        "mock_recovery": recovery,
                    },
                },
            ),
        ]

        for command, cwd, payload in cases:
            Path(command[-1]).write_text(json.dumps(payload), encoding="utf-8")
            completed = _run_process(command, cwd)
            assert completed.returncode == 0, completed.stderr or completed.stdout
            output_payload = json.loads(_extract_json_output(completed.stdout))
            assert output_payload["recovery"]["strategy"] == "captcha-solve"
            assert output_payload["recovery"]["recovered"] is True
            assert output_payload["recovery"]["events"][0]["phase"] == "detect"
            assert output_payload["recovery"]["events"][-1]["action"] == "continue"


def test_cross_runtime_job_commands_reject_malformed_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        job_path = Path(tmpdir) / "broken-job.json"
        job_path.write_text("{ invalid-json", encoding="utf-8")

        _compile_java_cli()

        cases = [
            (["go", "run", "./cmd/gospider", "job", "--file", str(job_path)], ROOT / "gospider"),
            ([sys.executable, "-m", "pyspider", "job", "--file", str(job_path)], ROOT),
            (["cargo", "run", "--quiet", "--", "job", "--file", str(job_path)], ROOT / "rustspider"),
            (
                [
                    "java",
                    "-cp",
                    "target/classes;target/dependency/*",
                    "com.javaspider.EnhancedSpider",
                    "job",
                    "--file",
                    str(job_path),
                ],
                ROOT / "javaspider",
            ),
        ]

        for command, cwd in cases:
            completed = _run_process(command, cwd)
            assert completed.returncode != 0, command
            combined = (completed.stdout + completed.stderr).lower()
            assert any(keyword in combined for keyword in ("invalid", "json", "failed", "exception")), combined


def test_cross_runtime_graph_artifact_blackbox_matrix():
    _compile_java_cli()
    server, url = _start_matrix_server()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            cases = [
                (
                    "go",
                    ["go", "run", "./cmd/gospider", "job", "--file", str(tmp / "go-graph.json")],
                    ROOT / "gospider",
                    {
                        "name": "go-graph-job",
                        "runtime": "http",
                        "target": {"url": url, "method": "GET"},
                        "extract": [{"field": "title", "type": "css", "expr": "title"}],
                        "output": {"format": "json", "path": str(tmp / "go-graph-output.json")},
                    },
                ),
                (
                    "python",
                    [sys.executable, "-m", "pyspider", "job", "--file", str(tmp / "py-graph.json")],
                    ROOT,
                    {
                        "name": "py-graph-job",
                        "runtime": "ai",
                        "target": {"url": url},
                        "extract": [{"field": "title", "type": "ai"}],
                        "output": {"format": "json", "path": str(tmp / "py-graph-output.json")},
                        "metadata": {"content": _GraphHTMLHandler.html},
                    },
                ),
                (
                    "rust",
                    ["cargo", "run", "--quiet", "--", "job", "--file", str(tmp / "rust-graph.json")],
                    ROOT / "rustspider",
                    {
                        "name": "rust-graph-job",
                        "runtime": "http",
                        "target": {"url": url, "method": "GET"},
                        "output": {"format": "json", "path": str(tmp / "rust-graph-output.json")},
                    },
                ),
                (
                    "java",
                    ["java", "-cp", "target/classes;target/dependency/*", "com.javaspider.cli.SuperSpiderCLI", "job", "--file", str(tmp / "java-graph.json")],
                    ROOT / "javaspider",
                    {
                        "name": "java-graph-job",
                        "runtime": "browser",
                        "target": {"url": url},
                        "extract": [{"field": "title", "type": "css", "expr": "title"}],
                        "output": {"format": "json", "path": str(tmp / "java-graph-output.json")},
                        "metadata": {"mock_html": _GraphHTMLHandler.html},
                    },
                ),
            ]

            for runtime_name, command, cwd, payload in cases:
                Path(command[-1]).write_text(json.dumps(payload), encoding="utf-8")
                output = _run(command, cwd)
                result = json.loads(output)
                refs = result["artifact_refs"]
                assert "graph" in refs, runtime_name
                assert refs["graph"]["kind"] == "graph", runtime_name
                assert refs["graph"]["path"], runtime_name
                assert refs["graph"]["root_id"] == "document", runtime_name
                assert refs["graph"]["stats"]["total_nodes"] >= 1, runtime_name
                graph_path = Path(refs["graph"]["path"])
                if not graph_path.is_absolute():
                    graph_path = cwd / graph_path
                assert graph_path.exists(), runtime_name
                assert result["artifacts"]["graph"]["kind"] == "graph", runtime_name
    finally:
        server.shutdown()
        server.server_close()
