from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gospider_browser_module_path_is_current():
    browser_module = ROOT / "gospider" / "browser" / "browser.go"
    assert browser_module.exists()
    assert not (ROOT / "gospider" / "browser.go").exists()


def test_rustspider_browser_module_path_is_current():
    browser_module = ROOT / "rustspider" / "src" / "browser" / "mod.rs"
    assert browser_module.exists()
    assert not (ROOT / "rustspider" / "src" / "playwright.rs").exists()


def test_gospider_examples_are_partitioned():
    examples_dir = ROOT / "gospider" / "examples"
    assert (examples_dir / "README.md").exists()
    assert (examples_dir / "legacy").exists()


def test_rustspider_examples_are_partitioned():
    examples_dir = ROOT / "rustspider" / "examples"
    assert (examples_dir / "README.md").exists()
    assert (examples_dir / "legacy").exists()


def test_pyspider_examples_are_partitioned():
    examples_dir = ROOT / "pyspider" / "examples"
    assert (examples_dir / "README.md").exists()
    assert (examples_dir / "legacy").exists()


def test_javaspider_media_examples_are_explicitly_legacy():
    readme = (ROOT / "javaspider" / "src" / "main" / "java" / "com" / "javaspider" / "examples" / "README.md").read_text(encoding="utf-8")
    legacy_dir = ROOT / "javaspider" / "examples" / "legacy"
    media = (legacy_dir / "UniversalMediaSpider.java").read_text(encoding="utf-8")

    assert not (ROOT / "javaspider" / "src" / "main" / "java" / "com" / "javaspider" / "examples" / "SimpleYouTubeSpider.java").exists()
    assert legacy_dir.exists()
    assert "@Deprecated" in media
    assert "EnhancedSpider" in readme
    assert "legacy" in readme.lower()


def test_pyspider_legacy_browser_wrapper_is_removed():
    assert not (ROOT / "pyspider" / "browser.py").exists()


def test_parallel_rust_spider_tree_is_removed():
    assert not (ROOT / "rust-spider").exists()


def test_unused_production_config_shadows_are_removed():
    assert not (ROOT / "gospider" / "core" / "production_config.go").exists()
    assert not (ROOT / "gospider" / "core" / "spider_v3.go").exists()
    assert not (ROOT / "rustspider" / "src" / "production_config.rs").exists()
    assert not (ROOT / "rustspider" / "src" / "config.rs").exists()


def test_pyspider_unused_parallel_engines_are_removed():
    assert not (ROOT / "pyspider" / "core" / "async_spider.py").exists()
    assert not (ROOT / "pyspider" / "core" / "advanced_crawler.py").exists()
    assert not (ROOT / "pyspider" / "core" / "spider_async_v3.py").exists()
