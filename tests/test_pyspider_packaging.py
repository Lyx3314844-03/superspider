from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]
PYSPIDER_ROOT = ROOT / "pyspider"


def test_pyspider_setup_can_load_without_local_readme(monkeypatch):
    captured = {}

    def fake_setup(**kwargs):
        captured.update(kwargs)

    monkeypatch.chdir(PYSPIDER_ROOT)
    monkeypatch.setattr("setuptools.setup", fake_setup)

    runpy.run_path(str(PYSPIDER_ROOT / "setup.py"), run_name="__main__")

    assert captured["name"] == "pyspider"
    assert captured["long_description"]
