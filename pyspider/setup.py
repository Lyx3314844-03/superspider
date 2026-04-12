from pathlib import Path

try:
    from setuptools import setup
except (
    ModuleNotFoundError
):  # pragma: no cover - fallback for metadata-only test environments

    def setup(**kwargs):
        return kwargs


BASE_DIR = Path(__file__).resolve().parent


def load_long_description() -> str:
    for candidate in (BASE_DIR / "README.md", BASE_DIR.parent / "README.md"):
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    return "强大的 Python 爬虫框架"


long_description = load_long_description()


def discover_pyspider_packages():
    ignored_parts = {
        "build",
        "dist",
        "__pycache__",
        ".pytest_cache",
        "examples",
        "tests",
    }
    packages = set()
    package_dir = {}

    for package_path in sorted(path for path in BASE_DIR.rglob("*") if path.is_dir()):
        relative_dir = package_path.relative_to(BASE_DIR)
        if any(part in ignored_parts for part in relative_dir.parts):
            continue
        has_python_sources = any(
            child.is_file() and child.suffix == ".py"
            for child in package_path.iterdir()
        )
        if not has_python_sources:
            continue
        package_name = "pyspider"
        if relative_dir.parts:
            package_name = ".".join(("pyspider", *relative_dir.parts))
        packages.add(package_name)
        package_dir[package_name] = (
            "." if not relative_dir.parts else relative_dir.as_posix()
        )

    packages.add("pyspider")
    package_dir["pyspider"] = "."
    return sorted(packages), package_dir


packages, package_dir = discover_pyspider_packages()

setup(
    name="pyspider",
    version="1.0.0",
    author="Spider Framework Suite Maintainers",
    description="Python runtime for the Spider Framework Suite crawler platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=packages,
    package_dir=package_dir,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=5.1.0",
        "aiohttp>=3.9.0",
        "aiofiles>=23.2.0",
        "pydantic>=2.5.0",
        "pyyaml>=6.0",
        "redis>=5.0.0",
        "flask>=3.1.0",
        "flask-cors>=6.0.0",
        "psutil>=6.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.23.0",
            "black>=23.12.0",
            "mypy>=1.8.0",
            "flake8>=7.0.0",
        ],
        "browser": [
            "playwright>=1.40.0",
            "selenium>=4.16.0",
            "webdriver-manager>=4.0.2",
        ],
        "extract": [
            "jsonpath-ng>=1.7.0",
        ],
        "ai": [
            "openai>=1.6.0",
            "anthropic>=0.8.0",
        ],
        "media": [
            "ffmpeg-python>=0.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pyspider=pyspider.cli.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "pyspider": ["py.typed"],
    },
)
