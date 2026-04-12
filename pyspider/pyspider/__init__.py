"""
Compatibility surface for `python -m pyspider` execution from the repository root.

The repository historically exposes the top-level package from the project root
while some workflows resolve this nested package first. Keep lightweight
metadata here so repo-root module execution can bootstrap the real CLI.
"""

__version__ = "1.0.0"
