from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_runtime_core_capabilities


ROOT = Path(__file__).resolve().parents[1]


def test_validate_payload_accepts_complete_kernel_contract_surface():
    payload = {
        "command": "capabilities",
        "runtime": "python",
        "shared_contracts": [
            "runtime-core",
            "autoscaled-frontier",
            "incremental-cache",
            "observability-envelope",
        ],
        "control_plane": {
            key: True for key in verify_runtime_core_capabilities.REQUIRED_CONTROL_PLANE_KEYS
        },
        "kernel_contracts": {
            key: [f"module.{key}"] for key in verify_runtime_core_capabilities.EXPECTED_KERNEL_KEYS
        },
    }

    errors = verify_runtime_core_capabilities._validate_payload(
        payload,
        framework="pyspider",
        runtime="python",
        manifest_kernel_contracts=set(verify_runtime_core_capabilities.EXPECTED_KERNEL_KEYS),
    )

    assert errors == []


def test_validate_payload_rejects_missing_kernel_contracts():
    payload = {
        "command": "capabilities",
        "runtime": "go",
        "shared_contracts": ["runtime-core"],
        "control_plane": {},
        "kernel_contracts": {"request": ["core.Request"]},
    }

    errors = verify_runtime_core_capabilities._validate_payload(
        payload,
        framework="gospider",
        runtime="go",
        manifest_kernel_contracts=set(verify_runtime_core_capabilities.EXPECTED_KERNEL_KEYS),
    )

    assert any("missing shared_contracts" in error for error in errors)
    assert any("missing control_plane keys" in error for error in errors)
    assert any("missing kernel_contracts keys" in error for error in errors)


def test_collect_runtime_core_capabilities_report_aggregates_framework_checks(monkeypatch):
    manifest = {
        "runtimes": [
            {"name": "javaspider", "kernel_contracts": list(verify_runtime_core_capabilities.EXPECTED_KERNEL_KEYS)},
            {"name": "gospider", "kernel_contracts": list(verify_runtime_core_capabilities.EXPECTED_KERNEL_KEYS)},
            {"name": "pyspider", "kernel_contracts": list(verify_runtime_core_capabilities.EXPECTED_KERNEL_KEYS)},
            {"name": "rustspider", "kernel_contracts": list(verify_runtime_core_capabilities.EXPECTED_KERNEL_KEYS)},
        ]
    }
    monkeypatch.setattr(
        verify_runtime_core_capabilities,
        "_manifest_kernel_contracts",
        lambda root: {item["name"]: set(item["kernel_contracts"]) for item in manifest["runtimes"]},
    )
    monkeypatch.setattr(
        verify_runtime_core_capabilities,
        "_prepare_java",
        lambda root: {"command": ["mvn"], "exit_code": 0, "status": "passed", "details": "prepared", "stdout": ""},
    )

    def fake_run(command, cwd, timeout=600):
        framework_name = {
            "javaspider": "javaspider",
            "gospider": "gospider",
            "rustspider": "rustspider",
            "spider": "pyspider",
        }[cwd.name]
        payload = {
            "command": "capabilities",
            "runtime": {
                "javaspider": "java",
                "gospider": "go",
                "pyspider": "python",
                "rustspider": "rust",
            }[framework_name],
            "shared_contracts": list(verify_runtime_core_capabilities.REQUIRED_SHARED_CONTRACTS),
            "control_plane": {
                key: True for key in verify_runtime_core_capabilities.REQUIRED_CONTROL_PLANE_KEYS
            },
            "kernel_contracts": {
                key: [f"module.{key}"] for key in verify_runtime_core_capabilities.EXPECTED_KERNEL_KEYS
            },
        }
        return {
            "command": command,
            "exit_code": 0,
            "status": "passed",
            "details": "ok",
            "stdout": json.dumps(payload),
            "name": framework_name,
        }

    monkeypatch.setattr(verify_runtime_core_capabilities, "_run", fake_run)

    report = verify_runtime_core_capabilities.collect_runtime_core_capabilities_report(ROOT)

    assert report["command"] == "verify-runtime-core-capabilities"
    assert report["summary"] == "passed"
    assert report["exit_code"] == 0


def test_runtime_core_capabilities_contract_is_documented_and_schema_exists():
    contract = (ROOT / "docs" / "framework-contract.md").read_text(encoding="utf-8")
    schema = json.loads((ROOT / "schemas" / "spider-runtime-core-capabilities-report.schema.json").read_text(encoding="utf-8"))

    assert "Kernel Capability Surface" in contract
    assert schema["properties"]["command"]["const"] == "verify-runtime-core-capabilities"
