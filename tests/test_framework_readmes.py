from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_framework_readmes_exist_and_cover_usage_and_deploy():
    expected = {
        "javaspider": ["Quick Start", "API", "Deploy"],
        "pyspider": ["Quick Start", "API", "Deploy"],
        "gospider": ["Quick Start", "API", "Deploy"],
        "rustspider": ["Quick Start", "API", "Deploy"],
    }

    for framework, tokens in expected.items():
        readme = ROOT / framework / "README.md"
        assert readme.exists(), framework
        content = readme.read_text(encoding="utf-8")
        for token in tokens:
            assert token in content, f"{framework}: missing {token}"


def test_framework_readmes_document_advanced_entrypoints():
    expected = {
        "javaspider": ["ultimate"],
        "pyspider": ["ultimate", "node-reverse"],
        "gospider": ["ultimate"],
        "rustspider": ["ultimate"],
    }

    for framework, tokens in expected.items():
        readme = ROOT / framework / "README.md"
        content = readme.read_text(encoding="utf-8").lower()
        for token in tokens:
            assert token in content, f"{framework}: missing {token}"
