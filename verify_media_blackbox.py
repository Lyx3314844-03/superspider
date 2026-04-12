from __future__ import annotations

import argparse
import json
import os
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler
from pathlib import Path


def _resolve_command(command: list[str]) -> list[str]:
    if not command:
        return command
    executable = (
        shutil.which(command[0])
        or shutil.which(f"{command[0]}.cmd")
        or shutil.which(f"{command[0]}.exe")
    )
    if executable:
        return [executable, *command[1:]]
    return command


def _run(command: list[str], cwd: Path, extra_env: dict[str, str] | None = None) -> dict:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    resolved = _resolve_command(command)
    completed = subprocess.run(
        resolved,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    details = "\n".join(
        part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
    ).strip()
    return {
        "command": resolved,
        "exit_code": completed.returncode,
        "status": "passed" if completed.returncode == 0 else "failed",
        "details": details or "command completed",
    }


class _FixtureHandler(BaseHTTPRequestHandler):
    routes: dict[str, tuple[bytes, str]] = {}

    def do_GET(self) -> None:  # noqa: N802
        body, content_type = self.routes.get(
            self.path,
            (b"not found", "text/plain; charset=utf-8"),
        )
        status = 200 if self.path in self.routes else 404
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class FixtureServer:
    def __init__(self, routes: dict[str, tuple[bytes, str]] | None = None):
        self._server = socketserver.TCPServer(("127.0.0.1", 0), _FixtureHandler)
        self.port = self._server.server_address[1]
        self.base_url = f"http://127.0.0.1:{self.port}"
        _FixtureHandler.routes = routes or {}
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> "FixtureServer":
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


def _fixture_routes() -> dict[str, tuple[bytes, str]]:
    m3u8 = b"#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:4\n#EXTINF:4,\n/seg0.ts\n#EXTINF:4,\n/seg1.ts\n#EXT-X-ENDLIST\n"
    iqiyi_html = (
        """
        <html>
          <head>
            <title>Fixture IQIYI - 爱奇艺</title>
            <meta property="og:image" content="http://127.0.0.1:{port}/cover.jpg" />
            <script>
              var player = {{
                "duration": 8,
                "quality": ["1080p", "720p"],
                "playList": "http://127.0.0.1:{port}/master.m3u8"
              }};
            </script>
          </head>
          <body>fixture iqiyi page</body>
        </html>
        """
    ).strip()
    generic_html = (
        """
        <html>
          <head>
            <title>Fixture Generic Media</title>
          </head>
          <body>
            <video src="http://127.0.0.1:{port}/master.m3u8"></video>
            <img src="http://127.0.0.1:{port}/cover.jpg" />
          </body>
        </html>
        """
    ).strip()
    bilibili_html = (
        """
        <html>
          <head>
            <title>Fixture Bilibili</title>
            <meta property="og:image" content="http://127.0.0.1:{port}/cover.jpg" />
            <script>
              window.__INITIAL_STATE__ = {{
                "duration": 18,
                "cover": "http://127.0.0.1:{port}/cover.jpg",
                "desc": "Fixture Bilibili Description",
                "baseUrl": "http://127.0.0.1:{port}/bili-video.mpd"
              }};
            </script>
          </head>
          <body>fixture bilibili page</body>
        </html>
        """
    ).strip()
    douyin_html = (
        """
        <html>
          <head>
            <title>Fixture Douyin</title>
          </head>
          <body>
            <script>
              window.__DATA__ = {{
                "duration": 12,
                "dynamic_cover": "http://127.0.0.1:{port}/cover.jpg",
                "desc": "Fixture Douyin Description",
                "playAddr": "http:\\/\\/127.0.0.1:{port}\\/douyin.mp4"
              }};
            </script>
          </body>
        </html>
        """
    ).strip()

    return {
        "/master.m3u8": (m3u8, "application/vnd.apple.mpegurl"),
        "/seg0.ts": (b"segment-0-", "video/mp2t"),
        "/seg1.ts": (b"segment-1", "video/mp2t"),
        "/bili-video.mpd": (b"<MPD/>", "application/dash+xml"),
        "/douyin.mp4": (b"fake-mp4", "video/mp4"),
        "/cover.jpg": (b"fake-jpg", "image/jpeg"),
        "/v_fixture123.html": (iqiyi_html.encode("utf-8"), "text/html; charset=utf-8"),
        "/generic-media.html": (generic_html.encode("utf-8"), "text/html; charset=utf-8"),
        "/video/BV1demo": (bilibili_html.encode("utf-8"), "text/html; charset=utf-8"),
        "/video/123456789": (douyin_html.encode("utf-8"), "text/html; charset=utf-8"),
    }


def _materialize_routes(port: int) -> dict[str, tuple[bytes, str]]:
    routes = _fixture_routes()
    materialized: dict[str, tuple[bytes, str]] = {}
    for path, (body, content_type) in routes.items():
        materialized[path] = (body.replace(b"{port}", str(port).encode("utf-8")), content_type)
    return materialized


def collect_report(root: Path) -> dict:
    python_env = {"PYTHONPATH": str(root)}
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        go_output = tmpdir / "gospider"
        py_output = tmpdir / "pyspider"
        go_artifacts = tmpdir / "gospider-artifacts"
        py_artifacts = tmpdir / "pyspider-artifacts"
        rust_artifacts = tmpdir / "rustspider-artifacts"
        java_artifacts = tmpdir / "javaspider-artifacts"
        go_output.mkdir()
        py_output.mkdir()
        go_artifacts.mkdir()
        py_artifacts.mkdir()
        rust_artifacts.mkdir()
        java_artifacts.mkdir()

        with FixtureServer() as server:
            materialized = _materialize_routes(server.port)
            _FixtureHandler.routes = materialized
            iqiyi_url = f"{server.base_url}/v_fixture123.html"
            generic_url = "https://example.com/watch/generic"
            rust_info_url = "https://www.bilibili.com/video/BV1demo"
            java_info_url = "https://www.douyin.com/video/123456789"

            checks = []

            (go_artifacts / "page.html").write_bytes(materialized["/v_fixture123.html"][0])
            (go_artifacts / "network.json").write_text(
                json.dumps({"m3u8Url": f"{server.base_url}/master.m3u8"}, ensure_ascii=False),
                encoding="utf-8",
            )
            (py_artifacts / "page.html").write_bytes(materialized["/generic-media.html"][0])
            (py_artifacts / "network.json").write_text(
                json.dumps({"playAddr": f"{server.base_url}/master.m3u8"}, ensure_ascii=False),
                encoding="utf-8",
            )
            (rust_artifacts / "page.html").write_bytes(materialized["/video/BV1demo"][0])
            (rust_artifacts / "trace.har").write_text(
                json.dumps({"log": {"entries": [{"request": {"url": f"{server.base_url}/bili-video.mpd"}}]}}, ensure_ascii=False),
                encoding="utf-8",
            )
            (java_artifacts / "page.html").write_bytes(materialized["/video/123456789"][0])
            (java_artifacts / "network.json").write_text(
                json.dumps({"playAddr": f"{server.base_url}/douyin.mp4"}, ensure_ascii=False),
                encoding="utf-8",
            )

            go_check = _run(
                [
                    "go",
                    "run",
                    "./cmd/gospider",
                    "media",
                    "artifact",
                    "--url",
                    iqiyi_url,
                    "--artifact-dir",
                    str(go_artifacts),
                    "-download",
                    "-output",
                    str(go_output),
                ],
                root / "gospider",
            )
            go_files = sorted(go_output.glob("*.ts"))
            if go_check["status"] == "passed" and len(go_files) == 1:
                content = go_files[0].read_bytes()
                if content == b"segment-0-segment-1":
                    go_check["details"] = (go_check["details"] + "\nblackbox artifact validated").strip()
                else:
                    go_check["status"] = "failed"
                    go_check["exit_code"] = 1
                    go_check["details"] = f"unexpected gospider artifact content: {content!r}"
            else:
                go_check["status"] = "failed"
                go_check["exit_code"] = 1
                go_check["details"] = f"{go_check['details']}\nexpected exactly one .ts artifact in {go_output}"
            checks.append({"name": "gospider-iqiyi-download", **go_check})

            py_check = _run(
                [
                    sys.executable,
                    "-m",
                    "pyspider",
                    "artifact",
                    "--url",
                    generic_url,
                    "--artifact-dir",
                    str(py_artifacts),
                    "--download",
                    "--output-dir",
                    str(py_output),
                ],
                root,
                extra_env=python_env,
            )
            py_files = sorted(py_output.glob("*.ts"))
            if py_check["status"] == "passed" and len(py_files) == 1:
                content = py_files[0].read_bytes()
                if content == b"segment-0-segment-1":
                    py_check["details"] = (py_check["details"] + "\nblackbox artifact validated").strip()
                else:
                    py_check["status"] = "failed"
                    py_check["exit_code"] = 1
                    py_check["details"] = f"unexpected pyspider artifact content: {content!r}"
            else:
                py_check["status"] = "failed"
                py_check["exit_code"] = 1
                py_check["details"] = f"{py_check['details']}\nexpected exactly one .ts artifact in {py_output}"
            checks.append({"name": "pyspider-generic-hls-download", **py_check})

            rust_check = _run(
                [
                    "cargo",
                    "run",
                    "--quiet",
                    "--",
                    "media",
                    "artifact",
                    "--url",
                    rust_info_url,
                    "--artifact-dir",
                    str(rust_artifacts),
                ],
                root / "rustspider",
            )
            if rust_check["status"] == "passed":
                try:
                    payload = json.loads(rust_check["details"])
                    parsed = payload.get("video") or {}
                    if (
                        parsed.get("platform") == "bilibili"
                        and parsed.get("dash_url") == f"{server.base_url}/bili-video.mpd"
                        and parsed.get("cover_url") == f"{server.base_url}/cover.jpg"
                    ):
                        rust_check["details"] = (rust_check["details"] + "\nblackbox metadata validated").strip()
                    else:
                        rust_check["status"] = "failed"
                        rust_check["exit_code"] = 1
                        rust_check["details"] = f"{rust_check['details']}\nunexpected rustspider parsed payload"
                except json.JSONDecodeError:
                    rust_check["status"] = "failed"
                    rust_check["exit_code"] = 1
                    rust_check["details"] = f"{rust_check['details']}\ninvalid rustspider json output"
            checks.append({"name": "rustspider-bilibili-info", **rust_check})

            java_prepare = _run(
                ["mvn", "-q", "-DskipTests", "compile", "dependency:copy-dependencies"],
                root / "javaspider",
            )
            java_check = {
                "command": [],
                "exit_code": java_prepare["exit_code"],
                "status": java_prepare["status"],
                "details": java_prepare["details"],
            }
            if java_prepare["status"] == "passed":
                classpath = f"target/classes{os.pathsep}target/dependency/*"
                java_check = _run(
                    [
                        "java",
                        "-cp",
                        classpath,
                        "com.javaspider.cli.MediaDownloaderCLI",
                        "artifact",
                        "--url",
                        java_info_url,
                        "--artifact-dir",
                        str(java_artifacts),
                    ],
                    root / "javaspider",
                )
                if java_check["status"] == "passed":
                    details = java_check["details"]
                    try:
                        payload = json.loads(details)
                        video = payload.get("video") or {}
                        if (
                            video.get("platform") == "Douyin"
                            and video.get("title") == "Fixture Douyin"
                            and video.get("description") == "Fixture Douyin Description"
                        ):
                            java_check["details"] = (details + "\nblackbox metadata validated").strip()
                        else:
                            java_check["status"] = "failed"
                            java_check["exit_code"] = 1
                            java_check["details"] = f"{details}\nunexpected javaspider media artifact payload"
                    except json.JSONDecodeError:
                        java_check["status"] = "failed"
                        java_check["exit_code"] = 1
                        java_check["details"] = f"{details}\ninvalid javaspider json output"
            checks.append({"name": "javaspider-douyin-info", **java_check})

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-media-blackbox",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 0 if failed == 0 else 1,
        "checks": checks,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Media Blackbox Report",
        "",
        f"Summary: {report['summary_text']}",
        "",
        "| Check | Status |",
        "| --- | --- |",
    ]
    for check in report["checks"]:
        lines.append(f"| {check['name']} | {check['status']} |")
    lines.append("")
    for check in report["checks"]:
        lines.append(f"## {check['name']}")
        lines.append("")
        lines.append(f"- Status: {check['status']}")
        lines.append(f"- Command: `{' '.join(check['command'])}`")
        lines.append(f"- Details: {check['details']}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local blackbox media download checks for spider frameworks")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-media-blackbox:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
