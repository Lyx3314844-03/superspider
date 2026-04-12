from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import validate_contract_configs


def test_collect_contract_config_report_passes_for_valid_configs(tmp_path):
    configs = {
        "java": tmp_path / "java.yaml",
        "go": tmp_path / "go.yaml",
        "rust": tmp_path / "rust.yaml",
        "python": tmp_path / "py.yaml",
    }

    for runtime, path in configs.items():
        path.write_text(
            f"""
version: 1
project:
  name: {runtime}-project
runtime: {runtime}
crawl:
  urls:
    - https://example.com
  concurrency: 2
  max_requests: 10
  max_depth: 1
  timeout_seconds: 30
browser:
  enabled: true
  headless: true
  timeout_seconds: 30
  user_agent: ""
  screenshot_path: artifacts/browser/page.png
  html_path: artifacts/browser/page.html
storage:
  checkpoint_dir: artifacts/checkpoints
  dataset_dir: artifacts/datasets
  export_dir: artifacts/exports
export:
  format: json
  output_path: artifacts/exports/results.json
doctor:
  network_targets:
    - https://example.com
""".strip(),
            encoding="utf-8",
        )

    report = validate_contract_configs.collect_contract_config_report(tmp_path, configs)

    assert report["command"] == "validate-contract-configs"
    assert report["summary"] == "passed"
    assert report["summary_text"] == "4 passed, 0 failed"
    assert report["exit_code"] == 0


def test_collect_contract_config_report_rejects_runtime_mismatch(tmp_path):
    config_path = tmp_path / "java.yaml"
    config_path.write_text(
        """
version: 1
project:
  name: wrong-runtime
runtime: python
crawl:
  urls:
    - https://example.com
  concurrency: 1
  max_requests: 1
  max_depth: 0
  timeout_seconds: 30
browser:
  enabled: true
  headless: true
  timeout_seconds: 30
  user_agent: ""
  screenshot_path: artifacts/browser/page.png
  html_path: artifacts/browser/page.html
storage:
  checkpoint_dir: artifacts/checkpoints
  dataset_dir: artifacts/datasets
  export_dir: artifacts/exports
export:
  format: json
  output_path: artifacts/exports/results.json
""".strip(),
        encoding="utf-8",
    )

    report = validate_contract_configs.collect_contract_config_report(tmp_path, {"java": config_path})

    assert report["summary"] == "failed"
    assert any("runtime mismatch" in check["details"] for check in report["checks"] if check["name"] == "java")


def test_main_prints_json_report_for_explicit_configs(tmp_path, capsys):
    config_path = tmp_path / "python.yaml"
    config_path.write_text(
        """
version: 1
project:
  name: py-project
runtime: python
crawl:
  urls:
    - https://example.com
  concurrency: 1
  max_requests: 1
  max_depth: 0
  timeout_seconds: 30
browser:
  enabled: true
  headless: true
  timeout_seconds: 30
  user_agent: ""
  screenshot_path: artifacts/browser/page.png
  html_path: artifacts/browser/page.html
storage:
  checkpoint_dir: artifacts/checkpoints
  dataset_dir: artifacts/datasets
  export_dir: artifacts/exports
export:
  format: json
  output_path: artifacts/exports/results.json
""".strip(),
        encoding="utf-8",
    )

    exit_code = validate_contract_configs.main(
        ["--root", str(tmp_path), "--config", f"python={config_path}", "--json"]
    )
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert report["command"] == "validate-contract-configs"
    assert report["summary_text"] == "1 passed, 3 failed"
