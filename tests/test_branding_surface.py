from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_superspider_icon_and_capabilities_doc_exist():
    assert (ROOT / "docs" / "assets" / "superspider-icon.svg").exists()
    assert (ROOT / "docs" / "FRAMEWORK_CAPABILITIES.md").exists()


def test_readme_references_icon_and_capabilities_doc():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/assets/superspider-icon.svg" in readme
    assert "docs/FRAMEWORK_CAPABILITIES.md" in readme
    assert "### PySpider" in readme
    assert "### GoSpider" in readme
    assert "### RustSpider" in readme
    assert "### JavaSpider" in readme
