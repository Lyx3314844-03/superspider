from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generate_framework_deep_surfaces_report


ROOT = Path(__file__).resolve().parents[1]


def _payload(framework: str, runtime: str):
    return {
        "command": "capabilities",
        "framework": framework,
        "runtime": runtime,
        "entrypoints": [
            "config",
            "crawl",
            "browser",
            "ai",
            "doctor",
            "export",
            "scrapy",
            "ultimate",
            "anti-bot",
            "node-reverse",
            "jobdir",
            "http-cache",
            "console",
            "profile-site",
            "selector-studio",
            "plugins",
            "capabilities",
            "version",
        ],
        "modules": ["runtime.dispatch", "site_profiler", "selector_studio"],
        "operator_products": {
            "jobdir": {},
            "http_cache": {},
            "browser_tooling": {},
            "autoscaling_pools": {},
            "debug_console": {},
        },
        "control_plane": {
            "task_api": True,
            "result_envelope": True,
            "artifact_refs": True,
            "graph_artifact": True,
            "graph_extract": True,
        },
        "observability": ["doctor", "profile-site", "selector-studio"],
        "runtimes": ["http", "browser", "media", "ai"],
        "shared_contracts": ["runtime-core", "web-control-plane"],
        "kernel_contracts": {
            "request": ["core.Request"],
            "fingerprint": ["core.Fingerprint"],
            "frontier": ["core.Frontier"],
        },
    }


def test_collect_report_aggregates_capability_payloads(monkeypatch):
    monkeypatch.setattr(
        generate_framework_deep_surfaces_report.verify_runtime_core_capabilities,
        "_prepare_java",
        lambda root: {"status": "passed"},
    )
    monkeypatch.setattr(
        generate_framework_deep_surfaces_report.verify_runtime_core_capabilities,
        "_capability_command",
        lambda root, framework: (["echo", framework], root),
    )
    monkeypatch.setattr(
        generate_framework_deep_surfaces_report.verify_runtime_core_capabilities,
        "_run",
        lambda command, cwd: {
            "status": "passed",
            "stdout": json.dumps(
                _payload(
                    framework=command[-1],
                    runtime={
                        "javaspider": "java",
                        "gospider": "go",
                        "pyspider": "python",
                        "rustspider": "rust",
                    }[command[-1]],
                )
            ),
        },
    )
    monkeypatch.setattr(
        generate_framework_deep_surfaces_report.verify_captcha_live_readiness,
        "collect_captcha_live_readiness_report",
        lambda root: {
            "frameworks": {
                "javaspider": {"summary": "skipped", "summary_text": "java live skipped"},
                "gospider": {"summary": "skipped", "summary_text": "go live skipped"},
                "pyspider": {"summary": "passed", "summary_text": "python live passed"},
                "rustspider": {"summary": "passed", "summary_text": "rust live passed"},
            }
        },
    )
    monkeypatch.setattr(
        generate_framework_deep_surfaces_report.verify_javaspider_ai_live,
        "run_javaspider_ai_live",
        lambda root: {"summary": "skipped", "summary_text": "java ai live skipped"},
    )

    report = generate_framework_deep_surfaces_report.collect_report(ROOT)

    assert report["command"] == "generate-framework-deep-surfaces-report"
    assert report["frameworks"]["gospider"]["runtime"] == "go"
    assert "profile-site" in report["frameworks"]["gospider"]["extended_entrypoints"]
    assert "debug_console" in report["frameworks"]["gospider"]["operator_products"]
    assert report["frameworks"]["pyspider"]["live_surfaces"][0]["summary"] == "passed"
    assert report["frameworks"]["javaspider"]["live_surfaces"][1]["name"] == "ai-live-readiness"


def test_render_markdown_includes_extended_surfaces():
    markdown = generate_framework_deep_surfaces_report.render_markdown(
        {
            "summary_text": "deep surfaces collected",
            "frameworks": {
                "gospider": {
                    "runtime": "go",
                    "runtimes": ["http", "browser"],
                    "entrypoints": ["config", "crawl", "profile-site"],
                    "extended_entrypoints": ["profile-site"],
                    "modules": ["runtime.dispatch", "site_profiler"],
                    "operator_products": ["debug_console", "jobdir"],
                    "control_plane_keys": ["task_api", "result_envelope"],
                    "shared_contracts": ["runtime-core"],
                    "kernel_contracts": ["request", "frontier"],
                    "observability": ["doctor", "profile-site"],
                    "live_surfaces": [
                        {
                            "name": "captcha-live-readiness",
                            "summary": "skipped",
                            "details": "go live skipped",
                        }
                    ],
                }
            },
        }
    )

    assert "## gospider" in markdown
    assert "extended entrypoints: `profile-site`" in markdown
    assert "modules: `runtime.dispatch, site_profiler`" in markdown
    assert "`captcha-live-readiness`: `skipped` | go live skipped" in markdown


def test_schema_exists():
    schema = json.loads(
        (
            ROOT / "schemas" / "spider-framework-deep-surfaces-report.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert schema["properties"]["command"]["const"] == "generate-framework-deep-surfaces-report"
