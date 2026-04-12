import importlib.util
from pathlib import Path
from types import SimpleNamespace
import runpy
import sys
import types

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pyspider.cli import dependencies
from pyspider.media.ffmpeg_tools import FFmpegNotFoundError


def test_dependency_report_to_dict_normalizes_levels():
    report = SimpleNamespace(
        exit_code=1,
        summary="1 passed, 1 warning, 1 failed, 1 skipped",
        statuses=[
            SimpleNamespace(level="ok", name="Python", message="3.13.12"),
            SimpleNamespace(level="warn", name="Config file", message="defaults"),
            SimpleNamespace(level="fail", name="FFmpeg", message="missing"),
            SimpleNamespace(
                level="skip", name="Redis connection", message="not checked"
            ),
        ],
    )

    payload = dependencies.dependency_report_to_dict(report)

    assert payload["summary"] == "failed"
    assert payload["summary_text"] == "1 passed, 1 warning, 1 failed, 1 skipped"
    assert [check["status"] for check in payload["checks"]] == [
        "passed",
        "warning",
        "failed",
        "skipped",
    ]


def test_check_module_marks_missing_optional_dependency_as_warning(monkeypatch):
    monkeypatch.setattr(dependencies.importlib.util, "find_spec", lambda _: None)

    status = dependencies._check_module("Playwright", "playwright", optional=True)

    assert status.level == "warn"
    assert "optional feature unavailable" in status.message


def test_check_ffmpeg_reports_missing_binary_and_skips_ffprobe(monkeypatch):
    class MissingExecutor:
        def __init__(self, *args, **kwargs):
            raise FFmpegNotFoundError("ffmpeg missing for test")

    monkeypatch.setattr(dependencies, "FFmpegExecutor", MissingExecutor)

    statuses = dependencies._check_ffmpeg("C:/missing/ffmpeg.exe")

    assert [status.level for status in statuses] == ["fail", "warn"]
    assert "Configured path: C:/missing/ffmpeg.exe" in statuses[0].message
    assert statuses[1].name == "ffprobe"


def test_check_browser_binary_accepts_absolute_existing_path(monkeypatch):
    monkeypatch.setattr(
        dependencies, "_browser_candidates", lambda: ("C:/Chrome/chrome.exe",)
    )
    monkeypatch.setattr(dependencies.os.path, "isabs", lambda candidate: True)
    monkeypatch.setattr(
        dependencies.os.path,
        "exists",
        lambda candidate: candidate == "C:/Chrome/chrome.exe",
    )

    status = dependencies._check_browser_binary()

    assert status.level == "ok"
    assert status.message == "C:/Chrome/chrome.exe"


def test_run_dependency_doctor_builds_summary_and_exit_code(monkeypatch):
    monkeypatch.setattr(
        dependencies,
        "_check_python",
        lambda: dependencies.DependencyStatus("ok", "Python", "3.13.12"),
    )
    monkeypatch.setattr(
        dependencies,
        "_load_config_statuses",
        lambda config_path: (
            SimpleNamespace(media=SimpleNamespace(output_dir="downloads")),
            [dependencies.DependencyStatus("warn", "Config file", "defaults")],
        ),
    )
    monkeypatch.setattr(
        dependencies,
        "_check_output_dir",
        lambda output_dir: dependencies.DependencyStatus("ok", "Output", output_dir),
    )
    monkeypatch.setattr(
        dependencies,
        "resolve_ffmpeg_path",
        lambda config_path=None: "C:/ffmpeg/ffmpeg.exe",
    )
    monkeypatch.setattr(
        dependencies,
        "_check_ffmpeg",
        lambda ffmpeg_path: [
            dependencies.DependencyStatus("ok", "FFmpeg", ffmpeg_path)
        ],
    )
    monkeypatch.setattr(
        dependencies,
        "_check_module",
        lambda name, module_name, optional: dependencies.DependencyStatus(
            "ok", name, "installed"
        ),
    )
    monkeypatch.setattr(
        dependencies,
        "_check_redis_connection",
        lambda redis_url: dependencies.DependencyStatus(
            "skip", "Redis connection", "not checked"
        ),
    )
    monkeypatch.setattr(
        dependencies,
        "_check_browser_binary",
        lambda: dependencies.DependencyStatus(
            "fail", "Browser binary", "missing browser"
        ),
    )

    report = dependencies.run_dependency_doctor()

    assert report.exit_code == 1
    assert report.summary == "6 passed, 1 warnings, 1 failed, 1 skipped"
    assert report.statuses[-1].name == "Browser binary"


def test_pyspider_setup_can_load_without_local_readme(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    pyspider_root = root / "pyspider"
    captured = {}

    def fake_setup(**kwargs):
        captured.update(kwargs)

    monkeypatch.chdir(pyspider_root)
    fake_setuptools = types.ModuleType("setuptools")
    fake_setuptools.setup = fake_setup
    fake_setuptools.find_packages = lambda where=".": []
    monkeypatch.setitem(sys.modules, "setuptools", fake_setuptools)

    runpy.run_path(str(pyspider_root / "setup.py"), run_name="__main__")

    assert captured["name"] == "pyspider"
    assert captured["long_description"]
    assert "pyspider.encrypted" in captured["packages"]
    assert "pyspider.bridge" in captured["packages"]
    assert "flask>=3.1.0" in captured["install_requires"]
    assert "flask-cors>=6.0.0" in captured["install_requires"]
    assert "psutil>=6.1.0" in captured["install_requires"]
    assert "webdriver-manager>=4.0.2" in captured["extras_require"]["browser"]
    assert "jsonpath-ng>=1.7.0" in captured["extras_require"]["extract"]


def test_legacy_enhanced_script_imports_without_missing_pyspider_modules(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    module_path = root / "pyspider" / "enhanced.py"

    monkeypatch.syspath_prepend(str(root))

    spec = importlib.util.spec_from_file_location("legacy_enhanced_script", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    assert hasattr(module, "SitemapGenerator")
    assert hasattr(module, "APIScanner")
