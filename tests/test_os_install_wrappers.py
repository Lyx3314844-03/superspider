from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cross_platform_install_and_verify_wrappers_exist():
    expected = [
        ROOT / "scripts" / "windows" / "install.bat",
        ROOT / "scripts" / "windows" / "verify.bat",
        ROOT / "scripts" / "linux" / "install.sh",
        ROOT / "scripts" / "linux" / "verify.sh",
        ROOT / "scripts" / "macos" / "install.sh",
        ROOT / "scripts" / "macos" / "verify.sh",
    ]

    for path in expected:
        assert path.exists(), f"missing installer wrapper: {path}"


def test_readme_and_install_doc_reference_cross_platform_wrappers():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install = (ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")

    for token in (
        "scripts/windows/install.bat",
        "scripts/linux/install.sh",
        "scripts/macos/install.sh",
        "scripts/windows/verify.bat",
        "scripts/linux/verify.sh",
        "scripts/macos/verify.sh",
    ):
        assert token in readme
        assert token in install
