from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import importlib
import json
import os
import subprocess
import sys
import tempfile
import threading


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _run_process(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        command,
        cwd=cwd,
        env=merged_env,
        capture_output=True,
        text=True,
        check=False,
    )


def _extract_json_output(output: str) -> dict:
    first_brace = output.find("{")
    payload = output[first_brace:] if first_brace >= 0 else output
    return json.loads(payload)


def _compile_java_cli() -> None:
    completed = _run_process(
        ["cmd", "/c", "mvn", "-q", "compile", "dependency:copy-dependencies"],
        ROOT / "javaspider",
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


class _ReverseHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        body = {
            "/api/anti-bot/detect": {"success": True, "signals": ["vendor:test"], "level": "medium"},
            "/api/anti-bot/profile": {"success": True, "signals": ["vendor:test"], "level": "medium"},
            "/api/fingerprint/spoof": {"success": True, "fingerprint": {"ua": "mock"}},
            "/api/tls/fingerprint": {"success": True, "fingerprint": {"ja3": "mock-ja3"}},
            "/api/crypto/analyze": {
                "success": True,
                "cryptoTypes": [{"name": "AES", "confidence": 0.9}],
                "crypto_types": [{"name": "AES", "confidence": 0.9}],
            },
        }.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        payload = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):  # noqa: A003
        return


def _start_reverse_server() -> tuple[HTTPServer, str]:
    server = HTTPServer(("127.0.0.1", 0), _ReverseHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}"


def _write_helper(path: Path) -> None:
    path.write_text(
        """
import json, pathlib, sys
args = sys.argv[1:]
def value(flag):
    if flag in args:
        i = args.index(flag)
        return args[i + 1]
    return ""
for target in [value("--save-storage-state"), value("--save-cookies-file"), value("--html"), value("--screenshot")]:
    if not target:
        continue
    p = pathlib.Path(target)
    p.parent.mkdir(parents=True, exist_ok=True)
    if target.endswith(".json"):
        p.write_text("{}" if target.endswith("state.json") else "[]", encoding="utf-8")
    elif target.endswith(".html"):
        p.write_text("<html><head><title>capture</title></head><body><script>const aesKey='demo';</script></body></html>", encoding="utf-8")
    else:
        p.write_text("artifact", encoding="utf-8")
print(json.dumps({"title":"capture","url":value("--url"),"html_path":value("--html"),"screenshot_path":value("--screenshot")}))
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _seed_project(project_dir: Path, runtime: str, reverse_url: str) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "python": "scrapy_demo.py",
        "go": "cmd/gospider/main.go",
        "rust": "src/main.rs",
        "java": "src/main/java/com/javaspider/EnhancedSpider.java",
    }[runtime]
    manifest_runtime = {"python": "python", "go": "go", "rust": "rust", "java": "java"}[runtime]
    (project_dir / "scrapy-project.json").write_text(
        json.dumps({"name": f"{runtime}-project", "runtime": manifest_runtime, "entry": entry, "url": "https://example.com"}),
        encoding="utf-8",
    )
    (project_dir / "ai-auth.json").write_text(
        json.dumps(
            {
                "actions": [
                    {"type": "assert", "url_contains": "/dashboard"},
                    {"type": "save_as", "value": "url", "save_as": "final_url"},
                ],
                "node_reverse_base_url": reverse_url,
                "capture_reverse_profile": True,
            }
        ),
        encoding="utf-8",
    )


def _assert_auth_capture_result(project_dir: Path, payload: dict) -> None:
    assert payload["command"] == "scrapy auth-capture"
    auth_payload = (project_dir / "ai-auth.json").read_text(encoding="utf-8")
    assert "\"actions\"" in auth_payload
    assert "\"action_examples\"" in auth_payload
    assert "\"reverse_runtime\"" in auth_payload
    assert "\"crypto_analysis\"" in auth_payload
    assert "\"AES\"" in auth_payload
    assert "\"mock-ja3\"" in auth_payload
    assert "\"final_url\"" in auth_payload
    assert (project_dir / "artifacts" / "auth" / "auth-state.json").exists()
    assert (project_dir / "artifacts" / "auth" / "auth-cookies.json").exists()


def test_cross_runtime_auth_capture_matrix(monkeypatch):
    server, reverse_url = _start_reverse_server()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            helper = tmp / "fake_playwright_helper.py"
            _write_helper(helper)

            module = importlib.import_module("pyspider.cli.main")
            python_project = tmp / "py-project"
            _seed_project(python_project, "python", reverse_url)

            class FakeBrowser:
                page = None

                def __init__(self, *args, **kwargs):
                    self.page = self

                def start(self):
                    return None

                def load_cookies_file(self, path: str):
                    return None

                def navigate(self, url: str, wait_until: str = "networkidle"):
                    return None

                def save_storage_state(self, path: str):
                    Path(path).parent.mkdir(parents=True, exist_ok=True)
                    Path(path).write_text("{}", encoding="utf-8")

                def save_cookies(self, path: str):
                    Path(path).parent.mkdir(parents=True, exist_ok=True)
                    Path(path).write_text("[]", encoding="utf-8")

                def get_content(self):
                    return "<html><head><title>capture</title></head><body><script>const aesKey='demo';</script></body></html>"

                def get_url(self):
                    return "https://example.com/dashboard"

                def close(self):
                    return None

            class FakeNodeReverseClient:
                def __init__(self, base_url: str = None):
                    self.base_url = base_url

                def detect_anti_bot(self, **kwargs):
                    return {"success": True, "signals": ["vendor:test"], "level": "medium"}

                def profile_anti_bot(self, **kwargs):
                    return {"success": True, "signals": ["vendor:test"], "level": "medium"}

                def spoof_fingerprint(self, browser: str = "chrome", platform: str = "windows"):
                    return {"success": True, "fingerprint": {"ua": "mock"}}

                def generate_tls_fingerprint(self, browser: str = "chrome", version: str = "120"):
                    return {"success": True, "fingerprint": {"ja3": "mock-ja3"}}

                def analyze_crypto(self, code: str):
                    return {"success": True, "cryptoTypes": [{"name": "AES", "confidence": 0.9}]}

            monkeypatch.setattr("pyspider.browser.playwright_browser.PlaywrightBrowser", FakeBrowser)
            monkeypatch.setattr("pyspider.node_reverse.client.NodeReverseClient", FakeNodeReverseClient)
            with redirect_stdout(StringIO()) as buffer:
                exit_code = module.main(
                    [
                        "scrapy",
                        "auth-capture",
                        "--project",
                        str(python_project),
                        "--url",
                        "https://example.com/dashboard",
                    ]
                )
            assert exit_code == 0
            _assert_auth_capture_result(python_project, _extract_json_output(buffer.getvalue()))

            go_project = tmp / "go-project"
            _seed_project(go_project, "go", reverse_url)
            go_completed = _run_process(
                ["go", "run", "./cmd/gospider", "scrapy", "auth-capture", "--project", str(go_project), "--url", "https://example.com/dashboard"],
                ROOT / "gospider",
                {"GOSPIDER_PLAYWRIGHT_HELPER": str(helper)},
            )
            assert go_completed.returncode == 0, go_completed.stderr or go_completed.stdout
            _assert_auth_capture_result(go_project, _extract_json_output(go_completed.stdout))

            rust_project = tmp / "rust-project"
            _seed_project(rust_project, "rust", reverse_url)
            rust_completed = _run_process(
                ["cargo", "run", "--quiet", "--", "scrapy", "auth-capture", "--project", str(rust_project), "--url", "https://example.com/dashboard"],
                ROOT / "rustspider",
                {"RUSTSPIDER_PLAYWRIGHT_HELPER": str(helper)},
            )
            assert rust_completed.returncode == 0, rust_completed.stderr or rust_completed.stdout
            _assert_auth_capture_result(rust_project, _extract_json_output(rust_completed.stdout))

            _compile_java_cli()
            java_project = tmp / "java-project"
            _seed_project(java_project, "java", reverse_url)
            java_completed = _run_process(
                [
                    "java",
                    "-cp",
                    f"target/classes{os.pathsep}target/dependency/*",
                    "com.javaspider.EnhancedSpider",
                    "scrapy",
                    "auth-capture",
                    "--project",
                    str(java_project),
                    "--url",
                    "https://example.com/dashboard",
                ],
                ROOT / "javaspider",
                {"JAVASPIDER_PLAYWRIGHT_HELPER": str(helper)},
            )
            assert java_completed.returncode == 0, java_completed.stderr or java_completed.stdout
            _assert_auth_capture_result(java_project, _extract_json_output(java_completed.stdout))
    finally:
        server.shutdown()
        server.server_close()
