import io
import json
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pyspider_capabilities_reports_shared_contract_fields():
    from pyspider import __main__ as runtime_cli

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = runtime_cli._print_capabilities()

    assert exit_code == 0
    payload = json.loads(buffer.getvalue())
    assert payload["command"] == "capabilities"
    assert payload["runtime"] == "python"
    assert "shared_contracts" in payload
    assert "kernel_contracts" in payload
    assert "operator_products" in payload
    assert "observability" in payload
    assert "jobdir" in payload["entrypoints"]
    assert "http-cache" in payload["entrypoints"]
    assert "console" in payload["entrypoints"]
    assert sorted(payload["kernel_contracts"].keys()) == [
        "artifact_store",
        "cache",
        "fingerprint",
        "frontier",
        "middleware",
        "observability",
        "proxy_policy",
        "request",
        "scheduler",
        "session_pool",
    ]
    assert sorted(payload["operator_products"].keys()) == [
        "autoscaling_pools",
        "browser_tooling",
        "debug_console",
        "http_cache",
        "jobdir",
    ]


def test_ecosystem_manifest_reflects_extended_runtime_entrypoints():
    manifest = json.loads((ROOT / "contracts" / "ecosystem-manifest.json").read_text(encoding="utf-8"))
    runtimes = {runtime["name"]: runtime for runtime in manifest["runtimes"]}

    assert "workflow" in runtimes["javaspider"]["entrypoints"]
    assert "media" in runtimes["javaspider"]["entrypoints"]
    assert "jobdir" in runtimes["javaspider"]["entrypoints"]
    assert "http-cache" in runtimes["javaspider"]["entrypoints"]
    assert "console" in runtimes["javaspider"]["entrypoints"]
    assert "media" in runtimes["gospider"]["entrypoints"]
    assert "jobdir" in runtimes["gospider"]["entrypoints"]
    assert "http-cache" in runtimes["gospider"]["entrypoints"]
    assert "console" in runtimes["gospider"]["entrypoints"]
    assert "async-job" in runtimes["pyspider"]["entrypoints"]
    assert "media" in runtimes["pyspider"]["entrypoints"]
    assert "jobdir" in runtimes["pyspider"]["entrypoints"]
    assert "http-cache" in runtimes["pyspider"]["entrypoints"]
    assert "console" in runtimes["pyspider"]["entrypoints"]
    assert "media" in runtimes["rustspider"]["entrypoints"]
    assert "jobdir" in runtimes["rustspider"]["entrypoints"]
    assert "http-cache" in runtimes["rustspider"]["entrypoints"]
    assert "console" in runtimes["rustspider"]["entrypoints"]
    expected_kernel = {
        "request",
        "fingerprint",
        "frontier",
        "scheduler",
        "middleware",
        "artifact_store",
        "session_pool",
        "proxy_policy",
        "observability",
        "cache",
    }
    expected_operator_products = {
        "jobdir",
        "http_cache",
        "browser_tooling",
        "autoscaling_pools",
        "debug_console",
    }

    for runtime in runtimes.values():
        assert "control-plane-jsonl" in runtime["operator_surfaces"]
        assert set(runtime["kernel_contracts"]) == expected_kernel
        assert set(runtime["operator_products"]) == expected_operator_products


def test_static_runtime_capability_sources_advertise_extended_entrypoints():
    sources = {
        "python": ROOT / "pyspider" / "__main__.py",
        "java": ROOT / "javaspider" / "src" / "main" / "java" / "com" / "javaspider" / "cli" / "SuperSpiderCLI.java",
        "go": ROOT / "gospider" / "cmd" / "gospider" / "main.go",
        "rust": ROOT / "rustspider" / "src" / "main.rs",
    }

    python = sources["python"].read_text(encoding="utf-8")
    java = sources["java"].read_text(encoding="utf-8")
    go = sources["go"].read_text(encoding="utf-8")
    rust = sources["rust"].read_text(encoding="utf-8")

    assert '"jobdir"' in python
    assert '"http-cache"' in python
    assert '"console"' in python
    assert '"workflow"' in java
    assert '"media"' in java
    assert '"jobdir"' in java
    assert '"http-cache"' in java
    assert '"console"' in java
    assert '"media"' in go
    assert '"jobdir"' in go
    assert '"http-cache"' in go
    assert '"console"' in go
    assert '"media"' in rust
    assert '"jobdir"' in rust
    assert '"http-cache"' in rust
    assert '"console"' in rust
    assert '"kernel_contracts"' in java
    assert '"kernel_contracts"' in go
    assert '"kernel_contracts"' in rust
    assert '"operator_products"' in python
    assert '"operator_products"' in java
    assert '"operator_products"' in go
    assert '"operator_products"' in rust
    assert '"prometheus"' in java
    assert '"prometheus"' in go
    assert '"prometheus"' in rust
