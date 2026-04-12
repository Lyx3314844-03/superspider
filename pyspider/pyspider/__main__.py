from __future__ import annotations

import importlib
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    # When `python -m pyspider` is executed from the repository root, Python can
    # resolve this nested compatibility package first. Re-route imports to the
    # real top-level package at the repository root.
    repo_parent = Path(__file__).resolve().parents[2]
    repo_parent_str = str(repo_parent)
    if repo_parent_str not in sys.path:
        sys.path.insert(0, repo_parent_str)

    current = sys.modules.get("pyspider")
    if (
        current is not None
        and Path(getattr(current, "__file__", __file__)).resolve().parent
        == Path(__file__).resolve().parent
    ):
        sys.modules.pop("pyspider", None)

    runtime_main = importlib.import_module("pyspider.__main__")
    return int(runtime_main.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
