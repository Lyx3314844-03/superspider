from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_scrapy_style_starter_files_exist():
    expected = [
        ROOT / "examples" / "starters" / "pyspider-starter" / "scrapy_demo.py",
        ROOT / "examples" / "starters" / "pyspider-starter" / "scrapy-project.json",
        ROOT / "examples" / "starters" / "gospider-starter" / "main.go",
        ROOT / "examples" / "starters" / "gospider-starter" / "scrapy-project.json",
        ROOT / "examples" / "starters" / "rustspider-starter" / "src" / "main.rs",
        ROOT / "examples" / "starters" / "rustspider-starter" / "scrapy-project.json",
        ROOT / "examples" / "starters" / "javaspider-starter" / "src" / "main" / "java" / "starter" / "ScrapyStyleStarter.java",
        ROOT / "examples" / "starters" / "javaspider-starter" / "scrapy-project.json",
        ROOT / "examples" / "starters" / "csharpspider-starter" / "src" / "project" / "Program.cs",
        ROOT / "examples" / "starters" / "csharpspider-starter" / "scrapy-project.json",
    ]

    missing = [str(path) for path in expected if not path.exists()]
    assert not missing, f"missing scrapy-style starter files: {missing}"


def test_starter_index_mentions_scrapy_style_entrypoints():
    content = (ROOT / "examples" / "starters" / "README.md").read_text(encoding="utf-8")
    assert "scrapy-style" in content.lower()
    assert "ScrapyStyleStarter.java" in content
    assert "scrapy validate --project <path>" in content
    assert "csharpspider-starter" in content


def test_authoring_doc_mentions_starter_kits():
    content = (ROOT / "docs" / "scrapy-style-authoring.md").read_text(encoding="utf-8")
    assert "Starter Kits" in content
    assert "run-scrapy.sh" in content
    assert "scrapy run --project <path>" in content
    assert "scrapy validate --project <path>" in content
    assert "scrapy doctor --project <path>" in content
    assert "scrapy genspider" in content
    assert "scrapy shell" in content
    assert "scrapy export" in content
    assert "scrapy profile" in content
    assert "ScrapyPlugin" in content
    assert "CSharpSpider.Scrapy" in content
