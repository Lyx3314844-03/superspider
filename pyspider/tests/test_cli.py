from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
import json
import tempfile
import sys
import importlib
import yaml
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pyspider.spider.plugins import clear_registry_for_tests


def test_cli_entrypoint_module_exposes_main():
    module = importlib.import_module("pyspider.cli.main")

    assert callable(module.main)


def test_default_contract_config_uses_shared_defaults():
    module = importlib.import_module("pyspider.cli.main")

    config = module.default_contract_config()

    assert config["runtime"] == "python"
    assert config["crawl"]["concurrency"] == 5
    assert config["crawl"]["max_depth"] == 3
    assert config["doctor"]["network_targets"] == ["https://example.com"]
    assert config["anti_bot"]["profile"] == "chrome-stealth"
    assert config["node_reverse"]["base_url"] == "http://localhost:3000"


def test_load_contract_config_rejects_runtime_mismatch(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    config_path = tmp_path / "wrong-runtime.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "project": {"name": "wrong-runtime"},
                "runtime": "go",
                "crawl": {"urls": ["https://example.com"]},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    try:
        module.load_contract_config(str(config_path))
    except ValueError as exc:
        assert "runtime mismatch" in str(exc)
    else:
        raise AssertionError("expected invalid runtime config to be rejected")


def test_cli_main_job_command_matches_module_entrypoint_contract():
    module = importlib.import_module("pyspider.cli.main")

    with tempfile.TemporaryDirectory() as tmpdir:
        job_path = Path(tmpdir) / "job.json"
        output_path = Path(tmpdir) / "job-output.json"
        job_path.write_text(
            json.dumps(
                {
                    "name": "cli-job",
                    "runtime": "ai",
                    "target": {"url": "https://example.com"},
                    "extract": [{"field": "title", "type": "ai"}],
                    "output": {"format": "json", "path": str(output_path)},
                    "metadata": {"content": "<title>CLI Job Title</title>"},
                }
            ),
            encoding="utf-8",
        )

        buffer = StringIO()
        with redirect_stdout(buffer):
            exit_code = module.main(["job", "--file", str(job_path)])

        payload = json.loads(buffer.getvalue())
        assert exit_code == 0
        assert payload["job_name"] == "cli-job"
        assert payload["extract"]["title"] == "CLI Job Title"
        assert output_path.exists()


def test_cli_main_capabilities_command_surfaces_runtime_modules():
    module = importlib.import_module("pyspider.cli.main")

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(["capabilities"])

    payload = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert "runtime.async_runtime" in payload["modules"]
    assert "kernel_contracts" in payload
    assert "ai" in payload["runtimes"]
    assert "browser_compatibility" in payload


def test_cli_main_ai_command_falls_back_to_heuristics(tmp_path, monkeypatch):
    module = importlib.import_module("pyspider.cli.main")
    html_path = tmp_path / "page.html"
    html_path.write_text(
        "<html><head><title>Py AI Demo</title><meta name='description' content='Py summary'></head><body><h1>Py AI Demo</h1></body></html>",
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(
            [
                "ai",
                "--html-file",
                str(html_path),
                "--instructions",
                "提取标题和摘要",
                "--schema-json",
                '{"type":"object","properties":{"title":{"type":"string"},"summary":{"type":"string"},"url":{"type":"string"}}}',
            ]
        )

    payload = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert payload["command"] == "ai"
    assert payload["runtime"] == "python"
    assert payload["engine"] == "heuristic-fallback"
    assert payload["result"]["title"] == "Py AI Demo"
    assert payload["result"]["summary"] == "Py summary"


def test_scrapy_init_generates_ai_starter_files(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    project_path = tmp_path / "ai-project"

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(["scrapy", "init", "--path", str(project_path)])

    assert exit_code == 0
    assert (project_path / "ai-schema.json").exists()
    assert (project_path / "ai-job.json").exists()
    readme = (project_path / "README.md").read_text(encoding="utf-8")
    assert "AI Starter" in readme


def test_scrapy_genspider_ai_generates_ai_template(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    project_path = tmp_path / "ai-project"
    project_path.mkdir()
    (project_path / "scrapy-project.json").write_text(
        json.dumps({"name": "ai-project", "runtime": "python", "entry": "scrapy_demo.py"}),
        encoding="utf-8",
    )

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(
            [
                "scrapy",
                "genspider",
                "demo_ai",
                "example.com",
                "--project",
                str(project_path),
                "--ai",
            ]
        )

    assert exit_code == 0
    generated = (project_path / "spiders" / "demo_ai.py").read_text(encoding="utf-8")
    assert "AIExtractor" in generated
    assert "extract_structured" in generated
    assert "load_ai_project_assets" in generated
    assert "iter_ai_follow_requests" in generated


def test_scrapy_plan_ai_writes_plan_files(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    project_path = tmp_path / "ai-project"
    project_path.mkdir()
    (project_path / "scrapy-project.json").write_text(
        json.dumps({"name": "ai-project", "runtime": "python", "entry": "scrapy_demo.py", "url": "https://example.com"}),
        encoding="utf-8",
    )
    html_path = project_path / "page.html"
    html_path.write_text(
        "<html><head><title>Plan Demo</title><meta name='description' content='Plan summary'></head><body><article>hello</article></body></html>",
        encoding="utf-8",
    )

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(
            [
                "scrapy",
                "plan-ai",
                "--project",
                str(project_path),
                "--html-file",
                str(html_path),
                "--name",
                "planned_ai",
            ]
        )

    assert exit_code == 0
    assert (project_path / "ai-plan.json").exists()
    assert (project_path / "ai-schema.json").exists()
    assert (project_path / "ai-blueprint.json").exists()
    assert (project_path / "ai-extract-prompt.txt").exists()
    assert (project_path / "ai-auth.json").exists()
    payload = json.loads(buffer.getvalue())
    assert payload["command"] == "scrapy plan-ai"
    assert payload["spider_name"] == "planned_ai"
    assert payload["page_profile"]["crawler_type"] == "static_detail"
    assert payload["blueprint"]["crawler_type"] == "static_detail"
    assert payload["blueprint"]["job_templates"]
    assert "blueprint" in payload


def test_scrapy_scaffold_ai_writes_plan_schema_and_spider(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    project_path = tmp_path / "ai-project"
    project_path.mkdir()
    (project_path / "scrapy-project.json").write_text(
        json.dumps({"name": "ai-project", "runtime": "python", "entry": "scrapy_demo.py", "url": "https://example.com"}),
        encoding="utf-8",
    )
    html_path = project_path / "page.html"
    html_path.write_text(
        "<html><head><title>Scaffold Demo</title><meta name='description' content='Scaffold summary'></head><body><article>hello</article></body></html>",
        encoding="utf-8",
    )

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(
            [
                "scrapy",
                "scaffold-ai",
                "--project",
                str(project_path),
                "--html-file",
                str(html_path),
                "--name",
                "scaffold_ai",
            ]
        )

    assert exit_code == 0
    assert (project_path / "ai-plan.json").exists()
    assert (project_path / "ai-schema.json").exists()
    assert (project_path / "ai-blueprint.json").exists()
    assert (project_path / "ai-extract-prompt.txt").exists()
    assert (project_path / "ai-auth.json").exists()
    spider_path = project_path / "spiders" / "scaffold_ai.py"
    assert spider_path.exists()
    generated = spider_path.read_text(encoding="utf-8")
    assert "AIExtractor" in generated
    assert "load_ai_project_assets" in generated
    payload = json.loads(buffer.getvalue())
    assert payload["command"] == "scrapy scaffold-ai"
    assert payload["spider_name"] == "scaffold_ai"
    assert "blueprint" in payload


def test_scrapy_sync_ai_writes_ai_job_for_existing_project(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    project_path = tmp_path / "ai-project"
    project_path.mkdir()
    (project_path / "scrapy-project.json").write_text(
        json.dumps({"name": "ai-project", "runtime": "python", "entry": "scrapy_demo.py", "url": "https://example.com"}),
        encoding="utf-8",
    )
    html_path = project_path / "page.html"
    html_path.write_text(
        "<html><head><title>Sync Demo</title><meta name='description' content='Sync summary'></head><body><article>hello</article></body></html>",
        encoding="utf-8",
    )

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(
            [
                "scrapy",
                "sync-ai",
                "--project",
                str(project_path),
                "--html-file",
                str(html_path),
                "--name",
                "sync_ai",
            ]
        )

    assert exit_code == 0
    assert (project_path / "ai-job.json").exists()
    assert (project_path / "ai-blueprint.json").exists()
    assert (project_path / "ai-auth.json").exists()
    payload = json.loads(buffer.getvalue())
    assert payload["command"] == "scrapy sync-ai"


def test_scrapy_auth_validate_reports_authenticated_for_non_login_fixture(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    project_path = tmp_path / "ai-project"
    project_path.mkdir()
    (project_path / "scrapy-project.json").write_text(
        json.dumps({"name": "ai-project", "runtime": "python", "entry": "scrapy_demo.py", "url": "https://example.com"}),
        encoding="utf-8",
    )
    html_path = project_path / "page.html"
    html_path.write_text(
        "<html><head><title>Dashboard</title></head><body><article>hello</article></body></html>",
        encoding="utf-8",
    )

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(
            [
                "scrapy",
                "auth-validate",
                "--project",
                str(project_path),
                "--html-file",
                str(html_path),
            ]
        )

    assert exit_code == 0
    payload = json.loads(buffer.getvalue())
    assert payload["command"] == "scrapy auth-validate"
    assert payload["authenticated"] is True


def test_scrapy_auth_capture_writes_auth_assets(tmp_path, monkeypatch):
    module = importlib.import_module("pyspider.cli.main")
    project_path = tmp_path / "ai-project"
    project_path.mkdir()
    (project_path / "scrapy-project.json").write_text(
        json.dumps({"name": "ai-project", "runtime": "python", "entry": "scrapy_demo.py", "url": "https://example.com"}),
        encoding="utf-8",
    )
    html_path = project_path / "page.html"
    html_path.write_text(
        "<html><head><title>Capture</title></head><body><article>hello</article></body></html>",
        encoding="utf-8",
    )
    (project_path / "ai-auth.json").write_text(
        json.dumps(
            {
                "headers": {},
                "cookies": {},
                "storage_state_file": "",
                "cookies_file": "",
                "session": "auth",
                "actions": [
                    {
                        "type": "if",
                        "when": {"url_contains": "example.com"},
                        "then": [{"type": "click", "selector": "#login"}],
                    },
                        {"type": "type", "selector": "#username", "value": "demo"},
                        {"type": "mfa_totp", "selector": "#otp", "totp_secret": "JBSWY3DPEHPK3PXP"},
                        {"type": "click", "selector": "#unstable", "retry": 1},
                        {"type": "captcha_solve", "challenge": "turnstile", "site_key": "site-key", "action": "login", "c_data": "demo", "page_data": "page", "save_as": "captcha_token"},
                        {"type": "reverse_profile", "base_url": "http://localhost:3000", "save_as": "reverse_profile"},
                        {"type": "save_as", "value": "url", "save_as": "final_url"},
                    ],
                }
            ),
        encoding="utf-8",
    )

    class FakeBrowser:
        actions = []
        page = None
        unstable_attempts = 0

        def __init__(self, *args, **kwargs):
            self.started = False
            self.page = self

        def start(self):
            self.started = True

        def load_cookies_file(self, path: str):
            return None

        def navigate(self, url: str, wait_until: str = "networkidle"):
            return None

        def click(self, selector: str):
            if selector == "#unstable" and self.unstable_attempts == 0:
                type(self).unstable_attempts += 1
                raise RuntimeError("temporary click failure")
            self.actions.append(("click", selector))

        def fill(self, selector: str, value: str):
            self.actions.append(("type", selector, value))

        def save_storage_state(self, path: str):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text("{}", encoding="utf-8")

        def save_cookies(self, path: str):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text("[]", encoding="utf-8")

        def close(self):
            return None

        class locator:
            pass

        def locator(self, selector: str):
            class First:
                def text_content(self):
                    return "ok"

                def get_attribute(self, attr: str):
                    return "ok"

                def press(self, key: str, timeout: int | None = None):
                    return None

            class Wrapper:
                first = First()

            return Wrapper()

        class keyboard:
            @staticmethod
            def press(key: str):
                return None

        def get_url(self):
            return "https://example.com/dashboard"

        def get_content(self):
            return "<html><head><title>Dashboard</title></head><body>ok</body></html>"

    class FakeSolveResult:
        success = True
        text = "captcha-token"
        error = None

    class FakeCaptchaSolver:
        def __init__(self, api_key: str, service: str = "2captcha"):
            self.api_key = api_key
            self.service = service

        def solve_turnstile(self, site_key: str, page_url: str, *, action: str = "", c_data: str = "", page_data: str = ""):
            return FakeSolveResult()

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

    monkeypatch.setattr(
        "pyspider.browser.playwright_browser.PlaywrightBrowser",
        FakeBrowser,
    )
    monkeypatch.setattr(
        "pyspider.captcha.solver.CaptchaSolver",
        FakeCaptchaSolver,
    )
    monkeypatch.setattr(
        "pyspider.node_reverse.client.NodeReverseClient",
        FakeNodeReverseClient,
    )
    monkeypatch.setattr("pyspider.cli.main.time.time", lambda: 0)

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(
            [
                "scrapy",
                "auth-capture",
                "--project",
                str(project_path),
                "--html-file",
                str(html_path),
            ]
        )

    assert exit_code == 0
    assert (project_path / "ai-auth.json").exists()
    auth_payload = json.loads((project_path / "ai-auth.json").read_text(encoding="utf-8"))
    assert auth_payload["storage_state_file"]
    assert auth_payload["cookies_file"]
    assert auth_payload["action_examples"]
    assert auth_payload["captures"]["final_url"] == "https://example.com/dashboard"
    assert auth_payload["captures"]["captcha_token"] == "captcha-token"
    assert auth_payload["captures"]["reverse_profile"]["profile"]["level"] == "medium"
    assert auth_payload["captures"]["reverse_profile"]["crypto_analysis"]["cryptoTypes"][0]["name"] == "AES"
    assert ("click", "#login") in FakeBrowser.actions
    assert ("type", "#username", "demo") in FakeBrowser.actions
    assert ("type", "#otp", "282760") in FakeBrowser.actions
    assert ("click", "#unstable") in FakeBrowser.actions
    payload = json.loads(buffer.getvalue())
    assert payload["command"] == "scrapy auth-capture"


def test_scrapy_auth_capture_can_store_reverse_runtime(tmp_path, monkeypatch):
    module = importlib.import_module("pyspider.cli.main")
    project_path = tmp_path / "ai-project"
    project_path.mkdir()
    (project_path / "scrapy-project.json").write_text(
        json.dumps({"name": "ai-project", "runtime": "python", "entry": "scrapy_demo.py", "url": "https://example.com"}),
        encoding="utf-8",
    )
    html_path = project_path / "page.html"
    html_path.write_text(
        "<html><head><title>Capture</title></head><body><article>hello</article></body></html>",
        encoding="utf-8",
    )
    (project_path / "ai-auth.json").write_text(
        json.dumps(
            {
                "headers": {},
                "cookies": {},
                "storage_state_file": "",
                "cookies_file": "",
                "session": "auth",
                "actions": [],
                "node_reverse_base_url": "http://localhost:3000",
                "capture_reverse_profile": True,
            }
        ),
        encoding="utf-8",
    )

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
            return "<html>done</html>"

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

    monkeypatch.setattr(
        "pyspider.browser.playwright_browser.PlaywrightBrowser",
        FakeBrowser,
    )
    monkeypatch.setattr(
        "pyspider.node_reverse.client.NodeReverseClient",
        FakeNodeReverseClient,
    )

    with redirect_stdout(StringIO()):
        exit_code = module.main(
            [
                "scrapy",
                "auth-capture",
                "--project",
                str(project_path),
                "--html-file",
                str(html_path),
            ]
        )

    assert exit_code == 0
    auth_payload = json.loads((project_path / "ai-auth.json").read_text(encoding="utf-8"))
    assert auth_payload["reverse_runtime"]["profile"]["level"] == "medium"
    assert auth_payload["reverse_runtime"]["tls_fingerprint"]["fingerprint"]["ja3"] == "mock-ja3"
    assert auth_payload["reverse_runtime"]["crypto_analysis"]["cryptoTypes"][0]["name"] == "AES"


def test_cli_main_jobdir_command_delegates_to_shared_tool_with_init_shape():
    module = importlib.import_module("pyspider.cli.main")

    with patch.object(module, "run_shared_python_tool", return_value=0) as runner:
        exit_code = module.main(
            [
                "jobdir",
                "init",
                "--path",
                "artifacts/jobs/demo",
                "--runtime",
                "python",
                "--url",
                "https://example.com",
            ]
        )

    assert exit_code == 0
    runner.assert_called_once_with(
        "jobdir_tool.py",
        [
            "init",
            "--path",
            "artifacts/jobs/demo",
            "--runtime",
            "python",
            "--url",
            "https://example.com",
        ],
    )


def test_cli_main_http_cache_command_delegates_to_shared_tool():
    module = importlib.import_module("pyspider.cli.main")

    with patch.object(module, "run_shared_python_tool", return_value=0) as runner:
        exit_code = module.main(
            [
                "http-cache",
                "seed",
                "--path",
                "artifacts/cache/incremental.json",
                "--url",
                "https://example.com",
                "--status-code",
                "304",
                "--etag",
                "demo",
            ]
        )

    assert exit_code == 0
    runner.assert_called_once_with(
        "http_cache_tool.py",
        [
            "seed",
            "--path",
            "artifacts/cache/incremental.json",
            "--url",
            "https://example.com",
            "--status-code",
            "304",
            "--etag",
            "demo",
        ],
    )


def test_cli_main_console_command_uses_snapshot_and_tail_shapes():
    module = importlib.import_module("pyspider.cli.main")

    with patch.object(module, "run_shared_python_tool", return_value=0) as runner:
        assert (
            module.main(
                [
                    "console",
                    "snapshot",
                    "--control-plane",
                    "artifacts/control-plane",
                    "--jobdir",
                    "artifacts/jobs/demo",
                ]
            )
            == 0
        )
        assert (
            module.main(
                [
                    "console",
                    "tail",
                    "--control-plane",
                    "artifacts/control-plane",
                    "--stream",
                    "events",
                    "--lines",
                    "5",
                ]
            )
            == 0
        )

    assert runner.call_args_list[0].args == (
        "runtime_console.py",
        [
            "snapshot",
            "--control-plane",
            "artifacts/control-plane",
            "--lines",
            "20",
            "--jobdir",
            "artifacts/jobs/demo",
        ],
    )
    assert runner.call_args_list[1].args == (
        "runtime_console.py",
        [
            "tail",
            "--control-plane",
            "artifacts/control-plane",
            "--lines",
            "5",
            "--stream",
            "events",
        ],
    )


def test_cli_main_audit_command_and_preflight_alias_delegate_correctly():
    module = importlib.import_module("pyspider.cli.main")

    with patch.object(module, "run_shared_python_tool", return_value=0) as runner:
        assert (
            module.main(
                [
                    "audit",
                    "tail",
                    "--control-plane",
                    "artifacts/control-plane",
                    "--job-name",
                    "demo",
                    "--stream",
                    "audit",
                    "--lines",
                    "7",
                ]
            )
            == 0
        )
    assert runner.call_args.args == (
        "audit_console.py",
        [
            "tail",
            "--control-plane",
            "artifacts/control-plane",
            "--job-name",
            "demo",
            "--lines",
            "7",
            "--stream",
            "audit",
        ],
    )

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(["preflight", "--json"])
    assert exit_code in {0, 1}
    payload = json.loads(buffer.getvalue())
    assert payload["command"] == "preflight"


def test_cli_main_browser_tooling_and_scrapy_contracts_delegate_to_shared_tools():
    module = importlib.import_module("pyspider.cli.main")

    with patch.object(module, "run_shared_python_tool", return_value=0) as runner:
        assert (
            module.main(
                [
                    "browser",
                    "trace",
                    "--url",
                    "https://example.com",
                    "--trace-path",
                    "artifacts/browser/page.trace.zip",
                    "--har-path",
                    "artifacts/browser/page.har",
                ]
            )
            == 0
        )
        assert (
            module.main(
                [
                    "browser",
                    "mock",
                    "--url",
                    "https://example.com",
                    "--route-manifest",
                    "contracts/routes.json",
                ]
            )
            == 0
        )
        assert (
            module.main(
                [
                    "browser",
                    "codegen",
                    "--url",
                    "https://example.com",
                    "--output",
                    "artifacts/browser/codegen.py",
                    "--language",
                    "python",
                ]
            )
            == 0
        )
        assert (
            module.main(
                ["scrapy", "contracts", "validate", "--project", "demo-project"]
            )
            == 0
        )

    assert runner.call_args_list[0].args == (
        "playwright_fetch.py",
        [
            "--tooling-command",
            "trace",
            "--url",
            "https://example.com",
            "--trace-path",
            "artifacts/browser/page.trace.zip",
            "--har-path",
            "artifacts/browser/page.har",
        ],
    )
    assert runner.call_args_list[1].args == (
        "playwright_fetch.py",
        [
            "--tooling-command",
            "mock",
            "--url",
            "https://example.com",
            "--route-manifest",
            "contracts/routes.json",
        ],
    )
    assert runner.call_args_list[2].args == (
        "playwright_fetch.py",
        [
            "--tooling-command",
            "codegen",
            "--url",
            "https://example.com",
            "--codegen-out",
            "artifacts/browser/codegen.py",
            "--codegen-language",
            "python",
        ],
    )
    assert runner.call_args_list[3].args == (
        "spider_contracts.py",
        ["validate", "--project", "demo-project"],
    )


def test_cli_main_web_command_launches_ui_server():
    module = importlib.import_module("pyspider.cli.main")

    with patch("pyspider.web.app.init_db") as init_db, patch(
        "pyspider.web.app.app.run"
    ) as run:
        exit_code = module.main(
            ["web", "--mode", "ui", "--host", "127.0.0.1", "--port", "7070", "--debug"]
        )

    assert exit_code == 0
    init_db.assert_called_once_with()
    run.assert_called_once_with(
        host="127.0.0.1",
        port=7070,
        debug=True,
        use_reloader=False,
        use_debugger=True,
    )


def test_cli_main_web_command_launches_api_server():
    module = importlib.import_module("pyspider.cli.main")

    with patch("flask.app.Flask.run") as run:
        exit_code = module.main(
            [
                "web",
                "--mode",
                "api",
                "--host",
                "127.0.0.1",
                "--port",
                "8080",
                "--auth-token",
                "secret",
            ]
        )

    assert exit_code == 0
    run.assert_called_once_with(
        host="127.0.0.1",
        port=8080,
        debug=False,
        use_reloader=False,
        use_debugger=False,
        threaded=True,
    )


def test_cli_main_curl_convert_returns_python_code():
    module = importlib.import_module("pyspider.cli.main")

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(
            [
                "curl",
                "convert",
                "--command",
                'curl -X POST "https://example.com/api" -H "Accept: application/json" --data "a=1"',
                "--target",
                "aiohttp",
            ]
        )

    payload = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert payload["command"] == "curl convert"
    assert payload["runtime"] == "python"
    assert payload["target"] == "aiohttp"
    assert "aiohttp.ClientSession" in payload["code"]
    assert "https://example.com/api" in payload["code"]


def test_cli_main_workflow_run_persists_control_plane_artifacts(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(
        json.dumps(
            {
                "id": "py-workflow",
                "name": "py-workflow",
                "steps": [
                    {"id": "goto", "type": "goto", "selector": "https://example.com"},
                    {
                        "id": "title",
                        "type": "extract",
                        "selector": "title",
                        "metadata": {"value": "Workflow Title"},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(["workflow", "run", "--file", str(workflow_path)])

    payload = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert payload["command"] == "workflow run"
    assert payload["extract"]["title"] == "Workflow Title"
    assert Path(payload["events_path"]).exists()
    assert Path(payload["connector_path"]).exists()


def test_cli_main_scrapy_demo_command_exports_results(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    html_path = tmp_path / "page.html"
    output_path = tmp_path / "scrapy-demo.json"
    html_path.write_text("<html><title>Demo</title></html>", encoding="utf-8")

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(
            [
                "scrapy",
                "demo",
                "--url",
                "https://example.com",
                "--html-file",
                str(html_path),
                "--output",
                str(output_path),
            ]
        )

    payload = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert payload["command"] == "scrapy demo"
    assert output_path.exists()
    assert "Demo" in output_path.read_text(encoding="utf-8")


def test_cli_main_scrapy_run_command_reads_project_manifest(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    html_path = tmp_path / "page.html"
    html_path.write_text("<html><title>Manifest Demo</title></html>", encoding="utf-8")
    output_path = project_dir / "artifacts" / "exports" / "items.json"
    (project_dir / "scrapy-project.json").write_text(
        json.dumps(
            {
                "name": "demo-project",
                "runtime": "python",
                "entry": "scrapy_demo.py",
                "url": "https://example.com",
                "output": "artifacts/exports/items.json",
            }
        ),
        encoding="utf-8",
    )

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(
            [
                "scrapy",
                "run",
                "--project",
                str(project_dir),
                "--html-file",
                str(html_path),
            ]
        )

    payload = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert payload["command"] == "scrapy run"
    assert output_path.exists()
    assert "Manifest Demo" in output_path.read_text(encoding="utf-8")


def test_cli_main_scrapy_run_loads_real_spider_class_and_shared_pipeline(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    project_dir = tmp_path / "project"
    spiders_dir = project_dir / "spiders"
    spiders_dir.mkdir(parents=True)
    html_path = tmp_path / "page.html"
    html_path.write_text("<html><title>Loaded News</title></html>", encoding="utf-8")

    (project_dir / "scrapy-project.json").write_text(
        json.dumps(
            {
                "name": "real-project",
                "runtime": "python",
                "entry": "scrapy_demo.py",
                "url": "https://example.com",
                "output": "artifacts/exports/items.json",
            }
        ),
        encoding="utf-8",
    )
    (project_dir / "scrapy_demo.py").write_text(
        "from pyspider.spider.spider import Item, Spider\n\n"
        "class DemoSpider(Spider):\n"
        "    name = 'demo'\n"
        "    start_urls = ['https://example.com']\n\n"
        "    def parse(self, page):\n"
        "        yield Item(title='demo')\n",
        encoding="utf-8",
    )
    (project_dir / "spider-framework.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "project": {"name": "real-project"},
                "runtime": "python",
                "crawl": {"urls": ["https://example.com"]},
                "scrapy": {
                    "settings": {"marker": "project"},
                    "plugins": ["plugins:ProjectPlugin"],
                    "pipelines": ["pipelines:UpperTitlePipeline"],
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (project_dir / "pipelines.py").write_text(
        "from pyspider.spider.spider import Item, ItemPipeline\n\n"
        "class UpperTitlePipeline(ItemPipeline):\n"
        "    def process_item(self, item, spider):\n"
        "        item['title'] = item['title'].upper()\n"
        "        return item\n",
        encoding="utf-8",
    )
    (project_dir / "plugins.py").write_text(
        "from pyspider.spider.spider import ItemPipeline, ScrapyPlugin\n\n"
        "class PluginPipeline(ItemPipeline):\n"
        "    def process_item(self, item, spider):\n"
        "        item['plugin_pipeline'] = 'active'\n"
        "        return item\n\n"
        "class ProjectPlugin(ScrapyPlugin):\n"
        "    name = 'project-plugin'\n\n"
        "    def configure(self, config):\n"
        "        config.setdefault('scrapy', {}).setdefault('settings', {})['plugin_flag'] = 'enabled'\n"
        "        return config\n\n"
        "    def provide_pipelines(self):\n"
        "        return [PluginPipeline()]\n\n"
        "    def on_spider_opened(self, spider):\n"
        "        spider.settings['opened_by_plugin'] = 'yes'\n\n"
        "    def process_item(self, item, spider):\n"
        "        item['plugin_item'] = spider.settings['opened_by_plugin']\n"
        "        return item\n",
        encoding="utf-8",
    )
    (project_dir / "scrapy-plugins.json").write_text(
        json.dumps({"plugins": ["project-plugin"]}),
        encoding="utf-8",
    )
    (spiders_dir / "news.py").write_text(
        "# scrapy: url=https://news.example.com\n"
        "from pyspider.spider.spider import Item, Spider\n\n"
        "class NewsSpider(Spider):\n"
        "    name = 'news'\n"
        "    custom_settings = {'marker': 'spider', 'extra': 'yes'}\n"
        "    start_urls = ['https://news.example.com']\n\n"
        "    def parse(self, page):\n"
        "        yield Item(title=page.response.selector.title(), marker=self.settings['marker'], extra=self.settings['extra'])\n",
        encoding="utf-8",
    )

    list_buffer = StringIO()
    with redirect_stdout(list_buffer):
        assert module.main(["scrapy", "list", "--project", str(project_dir)]) == 0
    list_payload = json.loads(list_buffer.getvalue())
    news_entry = next(
        spider for spider in list_payload["spiders"] if spider["name"] == "news"
    )
    assert news_entry["class_name"] == "NewsSpider"

    run_buffer = StringIO()
    with redirect_stdout(run_buffer):
        exit_code = module.main(
            [
                "scrapy",
                "run",
                "--project",
                str(project_dir),
                "--spider",
                "news",
                "--html-file",
                str(html_path),
            ]
        )

    payload = json.loads(run_buffer.getvalue())
    assert exit_code == 0
    assert payload["spider"] == "news"
    assert payload["spider_class"] == "NewsSpider"
    assert payload["plugins"] == ["ProjectPlugin"]
    assert "UpperTitlePipeline" in payload["pipelines"]
    assert "PluginPipeline" in payload["pipelines"]
    output_path = Path(payload["output"])
    content = output_path.read_text(encoding="utf-8")
    assert "LOADED NEWS" in content
    assert '"marker": "spider"' in content
    assert '"extra": "yes"' in content


def test_cli_main_scrapy_run_loads_registered_plugin_by_name(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    clear_registry_for_tests()
    project_dir = tmp_path / "project"
    spiders_dir = project_dir / "spiders"
    spiders_dir.mkdir(parents=True)
    html_path = tmp_path / "page.html"
    html_path.write_text("<html><title>Plugin Demo</title></html>", encoding="utf-8")

    (project_dir / "scrapy-project.json").write_text(
        json.dumps(
            {
                "name": "plugin-project",
                "runtime": "python",
                "entry": "scrapy_demo.py",
                "url": "https://example.com",
                "output": "artifacts/exports/items.json",
            }
        ),
        encoding="utf-8",
    )
    (project_dir / "scrapy_demo.py").write_text(
        "from pyspider.spider.spider import Item, Spider\n\n"
        "class DemoSpider(Spider):\n"
        "    name = 'demo'\n"
        "    start_urls = ['https://example.com']\n\n"
        "    def parse(self, page):\n"
        "        yield Item(title='demo')\n",
        encoding="utf-8",
    )
    (project_dir / "spider-framework.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "project": {"name": "plugin-project"},
                "runtime": "python",
                "crawl": {"urls": ["https://example.com"]},
                "scrapy": {
                    "plugins": ["project-plugin"],
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (project_dir / "plugins.py").write_text(
        "from pyspider.spider.plugins import register_plugin\n"
        "from pyspider.spider.spider import ScrapyPlugin\n\n"
        "@register_plugin('project-plugin')\n"
        "class ProjectPlugin(ScrapyPlugin):\n"
        "    name = 'project-plugin'\n"
        "    def process_item(self, item, spider):\n"
        "        item['plugin_marker'] = 'enabled'\n"
        "        return item\n",
        encoding="utf-8",
    )
    (project_dir / "scrapy-plugins.json").write_text(
        json.dumps({"plugins": ["project-plugin"]}),
        encoding="utf-8",
    )
    (spiders_dir / "news.py").write_text(
        "from pyspider.spider.spider import Item, Spider\n\n"
        "class NewsSpider(Spider):\n"
        "    name = 'news'\n"
        "    start_urls = ['https://news.example.com']\n\n"
        "    def parse(self, page):\n"
        "        yield Item(title=page.response.selector.title())\n",
        encoding="utf-8",
    )

    run_buffer = StringIO()
    with redirect_stdout(run_buffer):
        exit_code = module.main(
            [
                "scrapy",
                "run",
                "--project",
                str(project_dir),
                "--spider",
                "news",
                "--html-file",
                str(html_path),
            ]
        )

    payload = json.loads(run_buffer.getvalue())
    assert exit_code == 0
    assert payload["plugins"] == ["ProjectPlugin"]
    output_path = Path(payload["output"])
    assert '"plugin_marker": "enabled"' in output_path.read_text(encoding="utf-8")
    clear_registry_for_tests()


def test_cli_main_scrapy_run_uses_project_browser_runner(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    project_dir = tmp_path / "project"
    spiders_dir = project_dir / "spiders"
    spiders_dir.mkdir(parents=True)

    (project_dir / "scrapy-project.json").write_text(
        json.dumps(
            {
                "name": "browser-project",
                "runtime": "python",
                "entry": "scrapy_demo.py",
                "url": "https://example.com/browser",
                "output": "artifacts/exports/items.json",
            }
        ),
        encoding="utf-8",
    )
    (project_dir / "scrapy_demo.py").write_text(
        "from pyspider.spider.spider import Item, Spider\n\n"
        "class DemoSpider(Spider):\n"
        "    name = 'demo'\n"
        "    start_urls = ['https://example.com/browser']\n\n"
        "    def parse(self, page):\n"
        "        yield Item(title=page.response.selector.title(), url=page.response.url)\n",
        encoding="utf-8",
    )
    (project_dir / "spider-framework.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "project": {"name": "browser-project"},
                "runtime": "python",
                "crawl": {"urls": ["https://example.com/browser"]},
                "browser": {
                    "enabled": True,
                    "headless": True,
                    "timeout_seconds": 30,
                    "user_agent": "",
                    "screenshot_path": "artifacts/browser/page.png",
                    "html_path": "artifacts/browser/page.html",
                },
                "scrapy": {"runner": "browser"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    def fake_fetch(
        url,
        browser_cfg,
        *,
        request=None,
        browser=None,
        close_browser=True,
        wait_until="networkidle",
        wait_for_selector=None,
        wait_for_load_state=None,
        timeout_seconds=None,
        screenshot_path=None,
        html_path=None,
    ):
        from pyspider.core.models import Request, Response

        html = "<html><title>Browser Routed</title></html>"
        if html_path:
            Path(html_path).parent.mkdir(parents=True, exist_ok=True)
            Path(html_path).write_text(html, encoding="utf-8")
        return Response(
            url=url + "?browser=1",
            status_code=200,
            headers={"content-type": "text/html"},
            content=html.encode("utf-8"),
            text=html,
            request=request or Request(url=url),
        )

    buffer = StringIO()
    with patch.object(module, "_fetch_browser_response", side_effect=fake_fetch):
        with redirect_stdout(buffer):
            exit_code = module.main(["scrapy", "run", "--project", str(project_dir)])

    payload = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert payload["runner"] == "browser"
    output_path = Path(payload["output"])
    assert output_path.exists()
    assert "Browser Routed" in output_path.read_text(encoding="utf-8")
    assert (project_dir / "artifacts" / "browser" / "page.html").exists()


def test_cli_main_scrapy_run_allows_spider_level_runner_override(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    project_dir = tmp_path / "project"
    spiders_dir = project_dir / "spiders"
    spiders_dir.mkdir(parents=True)

    (project_dir / "scrapy-project.json").write_text(
        json.dumps(
            {
                "name": "browser-override-project",
                "runtime": "python",
                "entry": "scrapy_demo.py",
                "url": "https://example.com/default",
                "output": "artifacts/exports/items.json",
            }
        ),
        encoding="utf-8",
    )
    (project_dir / "scrapy_demo.py").write_text(
        "from pyspider.spider.spider import Item, Spider\n\n"
        "class DemoSpider(Spider):\n"
        "    name = 'demo'\n"
        "    start_urls = ['https://example.com/default']\n\n"
        "    def parse(self, page):\n"
        "        yield Item(title='demo')\n",
        encoding="utf-8",
    )
    (spiders_dir / "news.py").write_text(
        "from pyspider.spider.spider import Item, Spider\n\n"
        "class NewsSpider(Spider):\n"
        "    name = 'news'\n"
        "    start_urls = ['https://example.com/news']\n\n"
        "    def parse(self, page):\n"
        "        yield Item(title=page.response.selector.title(), url=page.response.url)\n",
        encoding="utf-8",
    )
    (project_dir / "spider-framework.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "project": {"name": "browser-override-project"},
                "runtime": "python",
                "crawl": {"urls": ["https://example.com/default"]},
                "browser": {
                    "enabled": True,
                    "headless": True,
                    "timeout_seconds": 30,
                    "user_agent": "",
                    "screenshot_path": "artifacts/browser/page.png",
                    "html_path": "artifacts/browser/page.html",
                },
                "scrapy": {
                    "runner": "http",
                    "spiders": {
                        "news": {"runner": "browser"},
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    def fake_fetch(
        url,
        browser_cfg,
        *,
        request=None,
        browser=None,
        close_browser=True,
        wait_until="networkidle",
        wait_for_selector=None,
        wait_for_load_state=None,
        timeout_seconds=None,
        screenshot_path=None,
        html_path=None,
    ):
        from pyspider.core.models import Request, Response

        html = "<html><title>Spider Override</title></html>"
        return Response(
            url=url,
            status_code=200,
            headers={"content-type": "text/html"},
            content=html.encode("utf-8"),
            text=html,
            request=request or Request(url=url),
        )

    buffer = StringIO()
    with patch.object(module, "_fetch_browser_response", side_effect=fake_fetch):
        with redirect_stdout(buffer):
            exit_code = module.main(
                ["scrapy", "run", "--project", str(project_dir), "--spider", "news"]
            )

    payload = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert payload["runner"] == "browser"
    assert payload["spider"] == "news"
    assert "Spider Override" in Path(payload["output"]).read_text(encoding="utf-8")


def test_cli_main_scrapy_run_supports_request_level_hybrid_routing(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    project_dir = tmp_path / "project"
    spiders_dir = project_dir / "spiders"
    spiders_dir.mkdir(parents=True)

    (project_dir / "scrapy-project.json").write_text(
        json.dumps(
            {
                "name": "hybrid-project",
                "runtime": "python",
                "entry": "scrapy_demo.py",
                "url": "https://example.com/start",
                "output": "artifacts/exports/items.json",
            }
        ),
        encoding="utf-8",
    )
    (project_dir / "scrapy_demo.py").write_text(
        "from pyspider.core.models import Request\n"
        "from pyspider.spider.spider import Item, Spider\n\n"
        "class DemoSpider(Spider):\n"
        "    name = 'demo'\n"
        "    start_urls = ['https://example.com/start']\n\n"
        "    def parse(self, page):\n"
        "        yield Request(url='https://example.com/http', callback=self.parse_http)\n"
        "        yield Request(\n"
        "            url='https://example.com/browser',\n"
        "            callback=self.parse_browser,\n"
        "            meta={'runner': 'browser', 'browser_html_path': 'artifacts/browser/request-browser.html'},\n"
        "        )\n\n"
        "    def parse_http(self, page):\n"
        "        yield Item(kind='http', title=page.response.selector.title(), url=page.response.url)\n\n"
        "    def parse_browser(self, page):\n"
        "        yield Item(kind='browser', title=page.response.selector.title(), url=page.response.url)\n",
        encoding="utf-8",
    )
    (project_dir / "spider-framework.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "project": {"name": "hybrid-project"},
                "runtime": "python",
                "crawl": {"urls": ["https://example.com/start"]},
                "browser": {
                    "enabled": True,
                    "headless": True,
                    "timeout_seconds": 30,
                    "user_agent": "",
                    "screenshot_path": "artifacts/browser/page.png",
                    "html_path": "artifacts/browser/page.html",
                },
                "scrapy": {"runner": "hybrid"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    def fake_http_download(self, request):
        from pyspider.core.models import Response

        html_by_url = {
            "https://example.com/start": "<html><title>Start</title></html>",
            "https://example.com/http": "<html><title>HTTP Routed</title></html>",
        }
        html = html_by_url[request.url]
        return Response(
            url=request.url,
            status_code=200,
            headers={"content-type": "text/html"},
            content=html.encode("utf-8"),
            text=html,
            request=request,
        )

    def fake_browser_fetch(
        url,
        browser_cfg,
        *,
        request=None,
        browser=None,
        close_browser=True,
        wait_until="networkidle",
        wait_for_selector=None,
        wait_for_load_state=None,
        timeout_seconds=None,
        screenshot_path=None,
        html_path=None,
    ):
        from pyspider.core.models import Request, Response

        html = "<html><title>Browser Routed</title></html>"
        if html_path:
            Path(html_path).parent.mkdir(parents=True, exist_ok=True)
            Path(html_path).write_text(html, encoding="utf-8")
        return Response(
            url=url,
            status_code=200,
            headers={"content-type": "text/html"},
            content=html.encode("utf-8"),
            text=html,
            request=request or Request(url=url),
        )

    buffer = StringIO()
    with patch(
        "pyspider.downloader.downloader.HTTPDownloader.download", new=fake_http_download
    ):
        with patch.object(
            module, "_fetch_browser_response", side_effect=fake_browser_fetch
        ):
            with redirect_stdout(buffer):
                exit_code = module.main(
                    ["scrapy", "run", "--project", str(project_dir)]
                )

    payload = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert payload["runner"] == "hybrid"
    output_text = Path(payload["output"]).read_text(encoding="utf-8")
    assert '"kind": "http"' in output_text
    assert '"title": "HTTP Routed"' in output_text
    assert '"kind": "browser"' in output_text
    assert '"title": "Browser Routed"' in output_text
    assert (project_dir / "artifacts" / "browser" / "request-browser.html").exists()


def test_cli_main_scrapy_run_includes_reverse_summary_when_node_reverse_is_configured(
    tmp_path,
):
    module = importlib.import_module("pyspider.cli.main")
    project_dir = tmp_path / "project"
    spiders_dir = project_dir / "spiders"
    spiders_dir.mkdir(parents=True)
    html_path = tmp_path / "page.html"
    html_path.write_text("<html><title>Reverse Demo</title></html>", encoding="utf-8")

    (project_dir / "scrapy-project.json").write_text(
        json.dumps(
            {
                "name": "reverse-project",
                "runtime": "python",
                "entry": "scrapy_demo.py",
                "url": "https://example.com",
                "output": "artifacts/exports/items.json",
            }
        ),
        encoding="utf-8",
    )
    (project_dir / "scrapy_demo.py").write_text(
        "from pyspider.spider.spider import Item, Spider\n\n"
        "class DemoSpider(Spider):\n"
        "    name = 'demo'\n"
        "    start_urls = ['https://example.com']\n\n"
        "    def parse(self, page):\n"
        "        yield Item(title=page.response.selector.title())\n",
        encoding="utf-8",
    )
    (project_dir / "spider-framework.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "project": {"name": "reverse-project"},
                "runtime": "python",
                "crawl": {"urls": ["https://example.com"]},
                "node_reverse": {"enabled": True, "base_url": "http://127.0.0.1:3000"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (spiders_dir / "news.py").write_text(
        "from pyspider.spider.spider import Item, Spider\n\n"
        "class NewsSpider(Spider):\n"
        "    name = 'news'\n"
        "    start_urls = ['https://example.com/news']\n\n"
        "    def parse(self, page):\n"
        "        yield Item(title=page.response.selector.title())\n",
        encoding="utf-8",
    )

    with patch.object(
        module,
        "_collect_reverse_summary",
        return_value={
            "detect": {"success": True},
            "profile": {"success": True, "level": "medium"},
            "fingerprint_spoof": {"success": True},
            "tls_fingerprint": {"success": True, "fingerprint": {"ja3": "mock-ja3"}},
        },
    ):
        run_buffer = StringIO()
        with redirect_stdout(run_buffer):
            exit_code = module.main(
                [
                    "scrapy",
                    "run",
                    "--project",
                    str(project_dir),
                    "--spider",
                    "news",
                    "--html-file",
                    str(html_path),
                ]
            )

    payload = json.loads(run_buffer.getvalue())
    assert exit_code == 0
    assert payload["reverse"]["profile"]["level"] == "medium"
    assert payload["reverse"]["tls_fingerprint"]["fingerprint"]["ja3"] == "mock-ja3"


def test_browser_downloader_reuses_session_and_closes_on_cleanup():
    module = importlib.import_module("pyspider.cli.main")
    from pyspider.core.models import Request, Response

    class FakeBrowser:
        def __init__(self):
            self.closed = 0

        def close(self):
            self.closed += 1

    calls = []

    def fake_browser_fetch(
        url,
        browser_cfg,
        *,
        request=None,
        browser=None,
        close_browser=True,
        wait_until="networkidle",
        wait_for_selector=None,
        wait_for_load_state=None,
        timeout_seconds=None,
        screenshot_path=None,
        html_path=None,
    ):
        calls.append(
            {
                "url": url,
                "browser": browser,
                "close_browser": close_browser,
                "wait_until": wait_until,
                "wait_for_selector": wait_for_selector,
                "timeout_seconds": timeout_seconds,
            }
        )
        request.meta["_browser_instance"] = browser or FakeBrowser()
        html = "<html><title>Session</title></html>"
        return Response(
            url=url,
            status_code=200,
            headers={"content-type": "text/html"},
            content=html.encode("utf-8"),
            text=html,
            request=request,
        )

    downloader = module.BrowserDownloader(
        {
            "headless": True,
            "timeout_seconds": 30,
            "user_agent": "",
            "screenshot_path": "",
            "html_path": "",
        },
    )

    req1 = Request(
        url="https://example.com/1",
        meta={"runner": "browser", "browser": {"session": "shared"}},
    )
    req2 = Request(
        url="https://example.com/2",
        meta={
            "runner": "browser",
            "browser": {
                "session": "shared",
                "wait_until": "domcontentloaded",
                "wait_for_selector": "h1",
                "timeout_seconds": 12,
            },
        },
    )

    with patch.object(
        module, "_fetch_browser_response", side_effect=fake_browser_fetch
    ):
        downloader.download(req1)
        downloader.download(req2)
        downloader.close()

    assert len(calls) == 2
    assert calls[0]["browser"] is None
    assert calls[1]["browser"] is not None
    assert calls[1]["wait_until"] == "domcontentloaded"
    assert calls[1]["wait_for_selector"] == "h1"
    assert calls[1]["timeout_seconds"] == 12
    assert calls[1]["close_browser"] is False
    assert calls[1]["browser"].closed == 1


def test_cli_main_scrapy_init_command_creates_project(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    project_dir = tmp_path / "init-project"

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(["scrapy", "init", "--path", str(project_dir)])

    payload = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert payload["command"] == "scrapy init"
    assert (project_dir / "scrapy-project.json").exists()
    assert (project_dir / "scrapy_demo.py").exists()
    assert (project_dir / "spider-framework.yaml").exists()


def test_cli_main_scrapy_list_validate_and_genspider_commands(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    project_dir = tmp_path / "init-project"
    module.main(["scrapy", "init", "--path", str(project_dir)])

    list_buffer = StringIO()
    with redirect_stdout(list_buffer):
        assert module.main(["scrapy", "list", "--project", str(project_dir)]) == 0
    list_payload = json.loads(list_buffer.getvalue())
    assert list_payload["command"] == "scrapy list"
    assert list_payload["spiders"]

    validate_buffer = StringIO()
    with redirect_stdout(validate_buffer):
        assert module.main(["scrapy", "validate", "--project", str(project_dir)]) == 0
    validate_payload = json.loads(validate_buffer.getvalue())
    assert validate_payload["summary"] == "passed"

    genspider_buffer = StringIO()
    with redirect_stdout(genspider_buffer):
        assert (
            module.main(
                [
                    "scrapy",
                    "genspider",
                    "news",
                    "example.com",
                    "--project",
                    str(project_dir),
                ]
            )
            == 0
        )
    genspider_payload = json.loads(genspider_buffer.getvalue())
    assert genspider_payload["command"] == "scrapy genspider"
    assert (project_dir / "spiders" / "news.py").exists()

    run_buffer = StringIO()
    html_path = tmp_path / "news.html"
    html_path.write_text("<html><title>News Demo</title></html>", encoding="utf-8")
    with redirect_stdout(run_buffer):
        assert (
            module.main(
                [
                    "scrapy",
                    "run",
                    "--project",
                    str(project_dir),
                    "--spider",
                    "news",
                    "--html-file",
                    str(html_path),
                ]
            )
            == 0
        )
    run_payload = json.loads(run_buffer.getvalue())
    assert run_payload["command"] == "scrapy run"
    assert run_payload["spider"] == "news"


def test_cli_main_scrapy_shell_command_reads_html_fixture(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    html_path = tmp_path / "page.html"
    html_path.write_text("<html><title>Shell Demo</title></html>", encoding="utf-8")

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(
            [
                "scrapy",
                "shell",
                "--html-file",
                str(html_path),
                "--type",
                "css",
                "--expr",
                "title",
            ]
        )

    payload = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert payload["command"] == "scrapy shell"
    assert payload["values"] == ["Shell Demo"]


def test_cli_main_scrapy_export_command_uses_project_output(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "scrapy-project.json").write_text(
        json.dumps(
            {
                "name": "demo-project",
                "runtime": "python",
                "entry": "scrapy_demo.py",
                "url": "https://example.com",
                "output": "artifacts/exports/items.json",
            }
        ),
        encoding="utf-8",
    )
    source = project_dir / "artifacts" / "exports" / "items.json"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        json.dumps([{"title": "Demo", "url": "https://example.com"}]), encoding="utf-8"
    )
    output = project_dir / "artifacts" / "exports" / "items.csv"

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(
            [
                "scrapy",
                "export",
                "--project",
                str(project_dir),
                "--format",
                "csv",
                "--output",
                str(output),
            ]
        )

    payload = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert payload["command"] == "scrapy export"
    assert output.exists()


def test_cli_main_scrapy_profile_command_uses_project_and_spider(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spider_dir = project_dir / "spiders"
    spider_dir.mkdir()
    (project_dir / "scrapy-project.json").write_text(
        json.dumps(
            {
                "name": "demo-project",
                "runtime": "python",
                "entry": "scrapy_demo.py",
                "url": "https://example.com",
                "output": "artifacts/exports/items.json",
            }
        ),
        encoding="utf-8",
    )
    (spider_dir / "news.py").write_text(
        "# scrapy: url=https://example.com/news\n", encoding="utf-8"
    )
    html_path = tmp_path / "page.html"
    html_path.write_text(
        "<html><title>Profile Demo</title><a href='/a'>A</a><img src='x.png'></html>",
        encoding="utf-8",
    )

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(
            [
                "scrapy",
                "profile",
                "--project",
                str(project_dir),
                "--spider",
                "news",
                "--html-file",
                str(html_path),
            ]
        )

    payload = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert payload["command"] == "scrapy profile"
    assert payload["spider"] == "news"
    assert payload["title"] == "Profile Demo"
    assert payload["link_count"] == 1
    assert payload["image_count"] == 1


def test_cli_main_scrapy_bench_command_uses_html_fixture(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    html_path = tmp_path / "page.html"
    html_path.write_text(
        "<html><title>Bench Demo</title><a href='/a'>A</a></html>", encoding="utf-8"
    )

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(["scrapy", "bench", "--html-file", str(html_path)])

    payload = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert payload["command"] == "scrapy bench"
    assert payload["title"] == "Bench Demo"
    assert payload["link_count"] == 1


def test_cli_main_scrapy_doctor_command_reports_project_health(tmp_path):
    module = importlib.import_module("pyspider.cli.main")
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    spiders_dir = project_dir / "spiders"
    spiders_dir.mkdir()
    (project_dir / "scrapy-project.json").write_text(
        json.dumps(
            {
                "name": "demo-project",
                "runtime": "python",
                "entry": "scrapy_demo.py",
                "url": "https://example.com",
                "output": "artifacts/exports/items.json",
            }
        ),
        encoding="utf-8",
    )
    (project_dir / "scrapy_demo.py").write_text(
        "from pyspider.spider.spider import Spider\n\nclass DemoSpider(Spider):\n    name='demo'\n    start_urls=['https://example.com']\n    def parse(self, page):\n        return []\n",
        encoding="utf-8",
    )

    buffer = StringIO()
    with redirect_stdout(buffer):
        exit_code = module.main(["scrapy", "doctor", "--project", str(project_dir)])

    payload = json.loads(buffer.getvalue())
    assert exit_code == 0
    assert payload["command"] == "scrapy doctor"
    assert payload["summary"] in {"passed", "warning"}
