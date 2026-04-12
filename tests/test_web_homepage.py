from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_root_web_homepage_exists_and_links_core_surfaces():
    html = (ROOT / "web-ui" / "index.html").read_text(encoding="utf-8")
    assert "Spider Framework Suite" in html
    assert "One operator model across Java, Go, Python, and Rust." in html
    assert "public-benchmarks/" in html
    assert "docs/" in html
    assert "../docs/STARTERS.md" in html
    assert "../docs/COMPARE.md" in html


def test_platform_demo_files_exist():
    demo = ROOT / "examples" / "external" / "platform-demo"
    assert (demo / "README.md").exists()
    assert (demo / "docker-compose.yml").exists()
    assert (demo / "nginx.conf").exists()
    compose = (demo / "docker-compose.yml").read_text(encoding="utf-8")
    assert "gospider-api:" in compose
    assert "pyspider-web:" in compose
    assert "javaspider-web:" in compose
    assert "rustspider-web:" in compose


def test_docs_portal_exists():
    html = (ROOT / "web-ui" / "docs" / "index.html").read_text(encoding="utf-8")
    assert "Spider Framework Suite Docs" in html
    assert "../../docs/POSITIONING.md" in html
    assert "../public-benchmarks/" in html
