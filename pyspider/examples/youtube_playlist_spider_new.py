"""
Legacy wrapper.

Actual example implementation moved to `examples/legacy/youtube_playlist_spider_new.py`.
"""

from pathlib import Path
import runpy
import sys

if any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
    print("Legacy example moved to examples/legacy/youtube_playlist_spider_new.py")
    raise SystemExit(0)

runpy.run_path(
    str(Path(__file__).with_name("legacy").joinpath("youtube_playlist_spider_new.py")),
    run_name="__main__",
)
