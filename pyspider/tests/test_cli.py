from pathlib import Path
import sys
import importlib

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def test_cli_entrypoint_module_exposes_main():
    module = importlib.import_module("pyspider.cli.main")

    assert callable(module.main)
