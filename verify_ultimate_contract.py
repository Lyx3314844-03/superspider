from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


FRAMEWORKS = ("javaspider", "pyspider", "gospider", "rustspider")
ALLOWED_SUMMARIES = {"passed", "failed"}


def framework_runtime(framework: str) -> str:
    return {
        "javaspider": "java",
        "pyspider": "python",
        "gospider": "go",
        "rustspider": "rust",
    }[framework]


def _extract_json_payload(stdout: str) -> str:
    stripped = stdout.strip()
    first_brace = stripped.find("{")
    return stripped[first_brace:] if first_brace >= 0 else stripped


def _run_process(command: list[str], cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def _prepare_java(root: Path) -> tuple[bool, str]:
    classes_dir = root / "javaspider" / "target" / "classes" / "com" / "javaspider" / "EnhancedSpider.class"
    dependency_dir = root / "javaspider" / "target" / "dependency"
    if classes_dir.exists() and dependency_dir.exists():
        return True, "reused existing java build artifacts"

    command = ["mvn", "-q", "compile", "dependency:copy-dependencies"]
    if platform.system() == "Windows":
        command = ["cmd", "/c", *command]
    try:
        completed = _run_process(command, root / "javaspider", timeout=120)
    except FileNotFoundError as exc:
        return False, f"command not found: {exc}"
    except subprocess.TimeoutExpired:
        return False, "java build timed out"
    if completed.returncode == 0:
        return True, completed.stdout.strip()
    details = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part).strip()
    return False, details or "java compile failed"


def validate_ultimate_payload(payload: dict, expected_runtime: str) -> list[str]:
    errors: list[str] = []
    if payload.get("command") != "ultimate":
        errors.append("command must be 'ultimate'")
    if payload.get("runtime") != expected_runtime:
        errors.append(f"runtime mismatch: expected {expected_runtime!r}, got {payload.get('runtime')!r}")
    if payload.get("summary") not in ALLOWED_SUMMARIES:
        errors.append("summary must be 'passed' or 'failed'")
    if payload.get("exit_code") not in {0, 1}:
        errors.append("exit_code must be 0 or 1")
    if not isinstance(payload.get("summary_text"), str) or not payload.get("summary_text"):
        errors.append("summary_text must be a non-empty string")
    if not isinstance(payload.get("url_count"), int) or payload["url_count"] < 0:
        errors.append("url_count must be an integer >= 0")
    if not isinstance(payload.get("result_count"), int) or payload["result_count"] < 0:
        errors.append("result_count must be an integer >= 0")
    results = payload.get("results")
    if not isinstance(results, list):
        errors.append("results must be an array")
        return errors
    if payload.get("result_count") != len(results):
        errors.append("result_count must match the number of results")
    for index, item in enumerate(results):
        if not isinstance(item, dict):
            errors.append(f"results[{index}] must be an object")
            continue
        for key in ("task_id", "url", "success", "error", "duration", "anti_bot_level", "anti_bot_signals"):
            if key not in item:
                errors.append(f"results[{index}] missing {key}")
        if "task_id" in item and not isinstance(item["task_id"], str):
            errors.append(f"results[{index}].task_id must be a string")
        if "url" in item and (not isinstance(item["url"], str) or not item["url"]):
            errors.append(f"results[{index}].url must be a non-empty string")
        if "success" in item and not isinstance(item["success"], bool):
            errors.append(f"results[{index}].success must be boolean")
        if "error" in item and item["error"] is not None and not isinstance(item["error"], str):
            errors.append(f"results[{index}].error must be string or null")
        if "duration" in item and not isinstance(item["duration"], str):
            errors.append(f"results[{index}].duration must be a string")
        if "anti_bot_level" in item and item["anti_bot_level"] is not None and not isinstance(item["anti_bot_level"], str):
            errors.append(f"results[{index}].anti_bot_level must be string or null")
        if "anti_bot_signals" in item and not isinstance(item["anti_bot_signals"], list):
            errors.append(f"results[{index}].anti_bot_signals must be an array")
    return errors


class _PageHandler(BaseHTTPRequestHandler):
    page_html = "<html><title>Ultimate Contract</title><script>navigator.userAgent; CryptoJS.AES.encrypt('x','y')</script></html>"

    def do_GET(self) -> None:  # noqa: N802
        encoded = self.page_html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class _ReverseHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.send_error(404)
            return
        body = b'{"status":"ok"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        responses = {
            "/api/anti-bot/detect": {
                "success": True,
                "detection": {"hasCloudflare": True},
                "signals": ["vendor:test"],
                "level": "medium",
                "score": 7,
                "vendors": [],
                "challenges": [],
                "recommendations": ["keep cookies"],
            },
            "/api/anti-bot/profile": {
                "success": True,
                "signals": ["vendor:test"],
                "level": "medium",
                "score": 7,
                "vendors": [],
                "challenges": [],
                "recommendations": ["keep cookies"],
                "requestBlueprint": {},
                "mitigationPlan": {},
            },
            "/api/browser/simulate": {
                "success": True,
                "result": {"ok": True},
                "cookies": "session=1",
                "error": "",
            },
            "/api/crypto/analyze": {
                "success": True,
                "cryptoTypes": [{"name": "AES", "confidence": 0.9, "modes": ["CBC"]}],
                "crypto_types": [{"name": "AES", "confidence": 0.9, "modes": ["CBC"]}],
                "keys": ["secret"],
                "ivs": ["iv"],
                "analysis": {},
            },
            "/api/tls/fingerprint": {
                "success": True,
                "browser": "chrome",
                "version": "120",
                "fingerprint": {"ja3": "mock-ja3"},
                "ja3": "mock-ja3",
            },
            "/api/fingerprint/spoof": {
                "success": True,
                "browser": "chrome",
                "platform": "windows",
                "fingerprint": {"userAgent": "mock-ua"},
            },
            "/api/canvas/fingerprint": {
                "success": True,
                "hash": "mock-canvas",
            },
        }
        payload = responses.get(self.path)
        if payload is None:
            self.send_error(404)
            return
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class LocalServer:
    def __init__(self, handler_cls: type[BaseHTTPRequestHandler]):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        addr, port = sock.getsockname()
        sock.close()
        self.server = ThreadingHTTPServer((addr, port), handler_cls)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def _framework_command(root: Path, framework: str, page_url: str, reverse_url: str, checkpoint_dir: Path) -> tuple[list[str], Path]:
    if framework == "gospider":
        return (
            ["go", "run", "./cmd/gospider", "ultimate", "--url", page_url, "--reverse-service-url", reverse_url],
            root / "gospider",
        )
    if framework == "pyspider":
        return (
            [sys.executable, "-m", "pyspider", "ultimate", page_url, "--reverse-service-url", reverse_url],
            root,
        )
    if framework == "rustspider":
        return (
            ["cargo", "run", "--quiet", "--", "ultimate", "--url", page_url, "--reverse-service-url", reverse_url],
            root / "rustspider",
        )
    classpath = f"target/classes{os.pathsep}target/dependency/*"
    return (
        [
            "java",
            "-cp",
            classpath,
            "com.javaspider.EnhancedSpider",
            "ultimate",
            page_url,
            "--reverse-service-url",
            reverse_url,
            "--checkpoint-dir",
            str(checkpoint_dir),
        ],
        root / "javaspider",
    )


def run_framework_ultimate(root: Path, framework: str, page_url: str, reverse_url: str, checkpoint_dir: Path) -> dict:
    runtime = framework_runtime(framework)
    if framework == "javaspider":
        prepared, details = _prepare_java(root)
        if not prepared:
            return {
                "name": framework,
                "runtime": runtime,
                "summary": "failed",
                "exit_code": 1,
                "stdout": "",
                "stderr": details,
                "report": None,
            }

    command, cwd = _framework_command(root, framework, page_url, reverse_url, checkpoint_dir)
    try:
        completed = _run_process(command, cwd)
    except FileNotFoundError as exc:
        return {
            "name": framework,
            "runtime": runtime,
            "summary": "failed",
            "exit_code": 1,
            "stdout": "",
            "stderr": f"command not found: {exc}",
            "report": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "name": framework,
            "runtime": runtime,
            "summary": "failed",
            "exit_code": 1,
            "stdout": "",
            "stderr": "ultimate command timed out",
            "report": None,
        }

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if completed.returncode not in {0, 1}:
        return {
            "name": framework,
            "runtime": runtime,
            "summary": "failed",
            "exit_code": 1,
            "stdout": stdout,
            "stderr": stderr or f"unexpected exit code {completed.returncode}",
            "report": None,
        }

    try:
        payload = json.loads(_extract_json_payload(stdout))
    except json.JSONDecodeError as exc:
        return {
            "name": framework,
            "runtime": runtime,
            "summary": "failed",
            "exit_code": 1,
            "stdout": stdout,
            "stderr": stderr or f"invalid JSON output: {exc}",
            "report": None,
        }

    errors = validate_ultimate_payload(payload, runtime)
    return {
        "name": framework,
        "runtime": runtime,
        "summary": "passed" if not errors else "failed",
        "exit_code": 0 if not errors else 1,
        "stdout": stdout,
        "stderr": stderr if not errors else "\n".join(errors),
        "report": payload,
    }


def collect_ultimate_contract_report(root: Path) -> dict:
    page_server = LocalServer(_PageHandler)
    reverse_server = LocalServer(_ReverseHandler)
    try:
        frameworks = []
        for framework in FRAMEWORKS:
            with tempfile.TemporaryDirectory() as tmpdir_str:
                tmpdir = Path(tmpdir_str)
                frameworks.append(
                    run_framework_ultimate(root, framework, page_server.url, reverse_server.url, tmpdir / "checkpoints")
                )
    finally:
        page_server.close()
        reverse_server.close()

    failed = sum(1 for framework in frameworks if framework["summary"] != "passed")
    return {
        "command": "verify-ultimate-contract",
        "summary": "failed" if failed else "passed",
        "summary_text": f"{len(frameworks) - failed} frameworks passed, {failed} frameworks failed",
        "exit_code": 1 if failed else 0,
        "frameworks": frameworks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify four-framework ultimate contract")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = collect_ultimate_contract_report(args.root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"{report['command']} summary: {report['summary']}")
        for framework in report["frameworks"]:
            print(f"- {framework['name']}: {framework['summary']}")
            if framework["summary"] != "passed" and framework["stderr"]:
                print(f"  {framework['stderr']}")
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
