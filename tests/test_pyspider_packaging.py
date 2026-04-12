from pathlib import Path
import runpy
import sys
import types


ROOT = Path(__file__).resolve().parents[1]
PYSPIDER_ROOT = ROOT / "pyspider"


def test_pyspider_setup_can_load_without_local_readme(monkeypatch):
    captured = {}

    def fake_setup(**kwargs):
        captured.update(kwargs)

    monkeypatch.chdir(PYSPIDER_ROOT)
    fake_setuptools = types.ModuleType("setuptools")
    fake_setuptools.setup = fake_setup
    fake_setuptools.find_packages = lambda where=".": []
    monkeypatch.setitem(sys.modules, "setuptools", fake_setuptools)

    runpy.run_path(str(PYSPIDER_ROOT / "setup.py"), run_name="__main__")

    assert captured["name"] == "pyspider"
    assert captured["long_description"]
    assert "pyspider.advanced" in captured["packages"]
    assert "pyspider.node_reverse" in captured["packages"]
