import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from pyspider import __main__ as cli


class PySpiderCLITest(unittest.TestCase):
    def _run(self, *args: str) -> dict:
        buffer = StringIO()
        with redirect_stdout(buffer):
            exit_code = cli.main(list(args))
        self.assertEqual(exit_code, 0)
        return json.loads(buffer.getvalue())

    def test_legacy_url_mode_still_works(self):
        payload = self._run(
            "https://example.com",
            "--schema",
            json.dumps({"properties": {"title": {"type": "string"}}}),
            "--content",
            "<title>Legacy Demo</title>",
        )
        self.assertEqual(payload["extract"]["title"], "Legacy Demo")

    def test_job_command_runs_normalized_spec(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_path = Path(tmpdir) / "job.json"
            output_path = Path(tmpdir) / "job-output.json"
            job_path.write_text(
                json.dumps(
                    {
                        "name": "py-job",
                        "runtime": "ai",
                        "target": {"url": "https://example.com"},
                        "extract": [{"field": "title", "type": "ai"}],
                        "output": {"format": "json", "path": str(output_path)},
                        "metadata": {"content": "<title>Job Demo</title>"},
                    }
                ),
                encoding="utf-8",
            )

            payload = self._run("job", "--file", str(job_path))
            self.assertEqual(payload["job_name"], "py-job")
            self.assertEqual(payload["runtime"], "ai")
            self.assertEqual(payload["state"], "succeeded")
            self.assertEqual(payload["url"], "https://example.com")
            self.assertEqual(payload["error"], "")
            self.assertGreaterEqual(payload["metrics"]["latency_ms"], 0)
            self.assertEqual(payload["extract"]["title"], "Job Demo")
            self.assertEqual(payload["output"]["path"], str(output_path))
            self.assertTrue(output_path.exists())
            self.assertIn("Job Demo", output_path.read_text(encoding="utf-8"))

    def test_job_command_includes_reverse_summary_when_mocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_path = Path(tmpdir) / "job.json"
            job_path.write_text(
                json.dumps(
                    {
                        "name": "py-job-reverse",
                        "runtime": "ai",
                        "target": {"url": "https://example.com"},
                        "extract": [{"field": "title", "type": "ai"}],
                        "output": {"format": "json"},
                        "metadata": {
                            "content": "<title>Job Demo</title>",
                            "mock_reverse": {
                                "detect": {"success": True},
                                "profile": {"success": True, "level": "medium"},
                                "fingerprint_spoof": {"success": True},
                                "tls_fingerprint": {
                                    "success": True,
                                    "fingerprint": {"ja3": "mock-ja3"},
                                },
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            payload = self._run("job", "--file", str(job_path))

        self.assertEqual(payload["reverse"]["profile"]["level"], "medium")
        self.assertEqual(
            payload["reverse"]["tls_fingerprint"]["fingerprint"]["ja3"], "mock-ja3"
        )

    def test_async_job_command_runs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_path = Path(tmpdir) / "job.json"
            job_path.write_text(
                json.dumps(
                    {
                        "name": "py-async-job",
                        "runtime": "browser",
                        "target": {"url": "https://example.com"},
                        "extract": [{"field": "title", "type": "css"}],
                        "output": {"format": "json"},
                        "metadata": {"content": "<title>Async Demo</title>"},
                    }
                ),
                encoding="utf-8",
            )

            payload = self._run("async-job", "--file", str(job_path))
            self.assertEqual(payload["extract"]["title"], "Async Demo")

    def test_capabilities_command_lists_integrated_modules(self):
        payload = self._run("capabilities")
        self.assertIn("runtime.async_runtime", payload["modules"])
        self.assertIn("web.app", payload["modules"])
        self.assertIn("api.server", payload["modules"])
        self.assertIn("core.curlconverter", payload["modules"])
        self.assertIn("ai", payload["runtimes"])
        self.assertIn("ultimate", payload["entrypoints"])
        self.assertIn("scrapy", payload["entrypoints"])
        self.assertIn("curl", payload["entrypoints"])
        self.assertIn("web", payload["entrypoints"])
        self.assertIn("jobdir", payload["entrypoints"])
        self.assertIn("http-cache", payload["entrypoints"])
        self.assertIn("console", payload["entrypoints"])
        self.assertIn("operator_products", payload)
        self.assertIn("node-reverse", payload["entrypoints"])
        self.assertIn("anti-bot", payload["entrypoints"])

    def test_node_reverse_health_command_uses_framework_cli_surface(self):
        with patch(
            "pyspider.node_reverse.client.NodeReverseClient.health_check",
            return_value=True,
        ):
            payload = self._run("node-reverse", "health")

        self.assertTrue(payload["healthy"])
        self.assertEqual(payload["command"], "node-reverse health")

    def test_node_reverse_detect_command_uses_framework_cli_surface(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "blocked.html"
            html_path.write_text(
                "<html><body>challenge</body></html>", encoding="utf-8"
            )
            with patch(
                "pyspider.node_reverse.client.NodeReverseClient.detect_anti_bot",
                return_value={
                    "success": True,
                    "signals": ["vendor:cloudflare"],
                    "level": "high",
                },
            ):
                payload = self._run(
                    "node-reverse",
                    "detect",
                    "--html-file",
                    str(html_path),
                    "--status-code",
                    "403",
                )

        self.assertEqual(payload["signals"], ["vendor:cloudflare"])
        self.assertEqual(payload["level"], "high")

    def test_node_reverse_fingerprint_spoof_command_uses_framework_cli_surface(self):
        with patch(
            "pyspider.node_reverse.client.NodeReverseClient.spoof_fingerprint",
            return_value={
                "success": True,
                "browser": "chrome",
                "platform": "windows",
                "fingerprint": {"ua": "x"},
            },
        ):
            payload = self._run(
                "node-reverse",
                "fingerprint-spoof",
                "--browser",
                "chrome",
                "--platform",
                "windows",
            )

        self.assertEqual(payload["browser"], "chrome")
        self.assertEqual(payload["platform"], "windows")

    def test_node_reverse_tls_fingerprint_command_uses_framework_cli_surface(self):
        with patch(
            "pyspider.node_reverse.client.NodeReverseClient.generate_tls_fingerprint",
            return_value={
                "success": True,
                "browser": "chrome",
                "version": "120",
                "fingerprint": {"ja3": "mock-ja3"},
            },
        ):
            payload = self._run(
                "node-reverse",
                "tls-fingerprint",
                "--browser",
                "chrome",
                "--version",
                "120",
            )

        self.assertEqual(payload["version"], "120")
        self.assertEqual(payload["fingerprint"]["ja3"], "mock-ja3")

    def test_anti_bot_headers_command_uses_framework_cli_surface(self):
        payload = self._run("anti-bot", "headers", "--profile", "cloudflare")

        self.assertEqual(payload["command"], "anti-bot headers")
        self.assertEqual(payload["runtime"], "python")
        self.assertEqual(payload["profile"], "cloudflare")
        self.assertIn("User-Agent", payload["headers"])

    def test_profile_site_command_uses_profiler_surface(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "detail.html"
            html_path.write_text(
                "<html><title>X</title><article>author price</article></html>",
                encoding="utf-8",
            )
            with patch(
                "pyspider.node_reverse.client.NodeReverseClient.detect_anti_bot",
                return_value={"success": True, "signals": ["vendor:test"]},
            ), patch(
                "pyspider.node_reverse.client.NodeReverseClient.profile_anti_bot",
                return_value={
                    "success": True,
                    "signals": ["vendor:test"],
                    "level": "medium",
                },
            ), patch(
                "pyspider.node_reverse.client.NodeReverseClient.spoof_fingerprint",
                return_value={"success": True, "browser": "chrome"},
            ), patch(
                "pyspider.node_reverse.client.NodeReverseClient.generate_tls_fingerprint",
                return_value={"success": True, "fingerprint": {"ja3": "mock-ja3"}},
            ):
                payload = self._run("profile-site", "--html-file", str(html_path))

        self.assertEqual(payload["command"], "profile-site")
        self.assertEqual(payload["runtime"], "python")
        self.assertEqual(payload["page_type"], "detail")
        self.assertIn("title", payload["candidate_fields"])
        self.assertEqual(payload["reverse"]["profile"]["level"], "medium")

    def test_sitemap_discover_command_reads_local_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sitemap_path = Path(tmpdir) / "sitemap.xml"
            sitemap_path.write_text(
                '<?xml version="1.0"?><urlset><url><loc>https://example.com/a</loc></url><url><loc>https://example.com/b</loc></url></urlset>',
                encoding="utf-8",
            )

            payload = self._run("sitemap-discover", "--sitemap-file", str(sitemap_path))

        self.assertEqual(payload["command"], "sitemap-discover")
        self.assertEqual(payload["runtime"], "python")
        self.assertEqual(payload["url_count"], 2)

    def test_plugins_list_command_reads_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest_path.write_text(
                json.dumps({"entrypoints": [{"id": "shared-cli"}]}), encoding="utf-8"
            )

            payload = self._run("plugins", "list", "--manifest", str(manifest_path))

        self.assertEqual(payload["command"], "plugins list")
        self.assertEqual(payload["runtime"], "python")
        self.assertEqual(payload["plugins"][0]["id"], "shared-cli")

    def test_plugins_run_dispatches_builtin_plugin(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "page.html"
            html_path.write_text("<html><title>Demo</title></html>", encoding="utf-8")

            payload = self._run(
                "plugins",
                "run",
                "--plugin",
                "selector-studio",
                "--",
                "--html-file",
                str(html_path),
                "--type",
                "css",
                "--expr",
                "title",
            )

        self.assertEqual(payload["command"], "selector-studio")
        self.assertEqual(payload["count"], 1)

    def test_selector_studio_command_extracts_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "page.html"
            html_path.write_text(
                "<html><title>Demo</title><article><h1>Title</h1></article></html>",
                encoding="utf-8",
            )

            payload = self._run(
                "selector-studio",
                "--html-file",
                str(html_path),
                "--type",
                "css",
                "--expr",
                "title",
            )

        self.assertEqual(payload["command"], "selector-studio")
        self.assertEqual(payload["runtime"], "python")
        self.assertEqual(payload["count"], 1)

    def test_anti_bot_profile_command_detects_blocked_fixture(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "blocked.html"
            html_path.write_text(
                "<html><title>Blocked</title><body>Access denied captcha</body></html>",
                encoding="utf-8",
            )

            buffer = StringIO()
            with redirect_stdout(buffer):
                exit_code = cli.main(
                    [
                        "anti-bot",
                        "profile",
                        "--html-file",
                        str(html_path),
                        "--status-code",
                        "403",
                    ]
                )
            self.assertEqual(exit_code, 1)
            payload = json.loads(buffer.getvalue())
            self.assertTrue(payload["blocked"])
            self.assertIn("captcha", payload["signals"])

    def test_ultimate_command_uses_integrated_runtime(self):
        class FakeResult:
            def __init__(self, task_id: str, url: str):
                self.task_id = task_id
                self.url = url
                self.success = True
                self.error = None
                self.duration = 0.01
                self.anti_bot_level = "medium"
                self.anti_bot_signals = ["vendor:test"]

        class FakeSpider:
            async def start(self, urls):
                return [FakeResult("task_0", urls[0])]

        with patch(
            "pyspider.advanced.ultimate.create_ultimate_spider",
            return_value=FakeSpider(),
        ):
            payload = self._run("ultimate", "https://example.com")

        self.assertEqual(payload["command"], "ultimate")
        self.assertEqual(payload["runtime"], "python")
        self.assertEqual(payload["summary"], "passed")
        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(payload["result_count"], 1)
        self.assertEqual(payload["results"][0]["url"], "https://example.com")

    def test_version_command_uses_framework_cli_surface(self):
        buffer = StringIO()
        with redirect_stdout(buffer):
            exit_code = cli.main(["version"])

        self.assertEqual(exit_code, 0)
        self.assertIn("pyspider 1.0.0", buffer.getvalue())

    def test_config_init_command_uses_framework_cli_surface(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "spider-framework.yaml"
            buffer = StringIO()

            with redirect_stdout(buffer):
                exit_code = cli.main(["config", "init", "--output", str(output_path)])

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("runtime: python", output_path.read_text(encoding="utf-8"))
            self.assertIn("Wrote shared config", buffer.getvalue())

    def test_job_command_supports_failure_injection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_path = Path(tmpdir) / "job.json"
            job_path.write_text(
                json.dumps(
                    {
                        "name": "py-job-fail",
                        "runtime": "ai",
                        "target": {"url": "https://example.com"},
                        "output": {"format": "json"},
                        "metadata": {"fail_job": "synthetic failure"},
                    }
                ),
                encoding="utf-8",
            )

            buffer = StringIO()
            with redirect_stdout(buffer):
                exit_code = cli.main(["job", "--file", str(job_path)])
            self.assertEqual(exit_code, 1)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["state"], "failed")
            self.assertIn("synthetic failure", payload["error"])

    def test_job_command_rejects_blocked_allowed_domain(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_path = Path(tmpdir) / "job.json"
            job_path.write_text(
                json.dumps(
                    {
                        "name": "py-job-domain-fail",
                        "runtime": "ai",
                        "target": {
                            "url": "https://example.com",
                            "allowed_domains": ["blocked.com"],
                        },
                        "output": {"format": "json"},
                    }
                ),
                encoding="utf-8",
            )

            buffer = StringIO()
            with redirect_stdout(buffer):
                exit_code = cli.main(["job", "--file", str(job_path)])
            self.assertEqual(exit_code, 1)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["state"], "failed")
            self.assertIn("allowed_domains", payload["error"])

    def test_job_command_rejects_byte_budget_overflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            job_path = Path(tmpdir) / "job.json"
            job_path.write_text(
                json.dumps(
                    {
                        "name": "py-job-budget-fail",
                        "runtime": "ai",
                        "target": {"url": "https://example.com"},
                        "policy": {"budget": {"bytes_in": 8}},
                        "output": {"format": "json"},
                        "metadata": {"content": "<title>Budget Overflow</title>"},
                    }
                ),
                encoding="utf-8",
            )

            buffer = StringIO()
            with redirect_stdout(buffer):
                exit_code = cli.main(["job", "--file", str(job_path)])
            self.assertEqual(exit_code, 1)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["state"], "failed")
            self.assertIn("budget.bytes_in", payload["error"])

    def test_job_command_extracts_json_path_and_writes_control_plane_sink(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "result.json"
            job_path = Path(tmpdir) / "job.json"
            job_path.write_text(
                json.dumps(
                    {
                        "name": "py-json-extract",
                        "runtime": "ai",
                        "target": {
                            "url": "https://example.com",
                            "body": json.dumps(
                                {"product": {"name": "Capsule", "price": 199}}
                            ),
                        },
                        "extract": [
                            {
                                "field": "name",
                                "type": "json_path",
                                "path": "$.product.name",
                                "required": True,
                                "schema": {"type": "string"},
                            },
                            {
                                "field": "price",
                                "type": "json_path",
                                "path": "$.product.price",
                                "required": True,
                                "schema": {"type": "number"},
                            },
                        ],
                        "output": {"format": "json", "path": str(output_path)},
                    }
                ),
                encoding="utf-8",
            )

            payload = self._run("job", "--file", str(job_path))
            self.assertEqual(payload["extract"]["name"], "Capsule")
            self.assertEqual(payload["extract"]["price"], 199)
            control_plane = output_path.parent / "control-plane"
            self.assertTrue((control_plane / "results.jsonl").exists())
            self.assertTrue((control_plane / "py-json-extract-audit.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
