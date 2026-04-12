from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_shared_playwright_helper_exists():
    helper = ROOT / "tools" / "playwright_fetch.py"
    assert helper.exists()
    content = helper.read_text(encoding="utf-8")
    assert "sync_playwright" in content
    assert "--url" in content
    assert "--tooling-command" in content
    assert "--route-manifest" in content
    assert "--codegen-out" in content


def test_gospider_browser_fetch_uses_shared_helper():
    main_file = (ROOT / "gospider" / "cmd" / "gospider" / "main.go").read_text(encoding="utf-8")

    assert "browser fetch" in main_file
    assert "browser trace" in main_file
    assert "browser mock" in main_file
    assert "browser codegen" in main_file
    assert "playwright_fetch.py" in main_file
    assert "browserFetchRunnerFactory" in main_file


def test_rustspider_browser_fetch_uses_shared_helper():
    main_file = (ROOT / "rustspider" / "src" / "main.rs").read_text(encoding="utf-8")

    assert "browser fetch" in main_file
    assert "browser trace" in main_file
    assert "browser mock" in main_file
    assert "browser codegen" in main_file
    assert "playwright_fetch.py" in main_file
    assert "run_playwright_fetch" in main_file


def test_javaspider_browser_fetch_uses_shared_helper():
    main_file = (ROOT / "javaspider" / "src" / "main" / "java" / "com" / "javaspider" / "EnhancedSpider.java").read_text(encoding="utf-8")

    assert "browser fetch" in main_file
    assert "browser trace" in main_file
    assert "browser mock" in main_file
    assert "browser codegen" in main_file
    assert "playwright_fetch.py" in main_file
    assert "BrowserFetchRunner" in main_file


def test_python_playwright_tests_exist():
    assert (ROOT / "pyspider" / "tests" / "test_playwright_simple.py").exists()
    assert (ROOT / "pyspider" / "tests" / "test_playwright_features.py").exists()
