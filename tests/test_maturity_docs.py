from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_maturity_docs_exist_and_reference_new_governance_surfaces():
    docs = {
        "STABILITY_EVIDENCE.md": ["verify_runtime_stability.py", "frontier-stress"],
        "API_COMPATIBILITY.md": ["kernel contract", "verify_runtime_core_capabilities.py"],
        "COOKBOOK.md": ["verify_runtime_stability.py", "verify_public_install_chain.py"],
        "PLUGIN_GOVERNANCE.md": ["plugin", "manifest"],
        "DEPRECATION_POLICY.md": ["legacy", "migration"],
    }

    for name, tokens in docs.items():
        path = ROOT / "docs" / name
        content = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token.lower() in content.lower(), f"{name}: missing {token}"
