from __future__ import annotations

import argparse
import json
from pathlib import Path

import generate_framework_scorecard


README_TOKENS = ("Quick Start", "API", "Deploy")

FRAMEWORKS = {
    "javaspider": {
        "runtime": "java",
        "source_glob": "src/main/java/**/*.java",
        "test_glob": "src/test/java/**/*Test.java",
        "compile_mode": "maven",
        "compile_paths": ("pom.xml", "build.sh", "run-framework.sh"),
    },
    "pyspider": {
        "runtime": "python",
        "source_roots": ("",),
        "source_suffix": ".py",
        "source_excludes": {"tests", "__pycache__", ".pytest_cache", "downloads", "artifacts", "pyspider.egg-info"},
        "test_glob": "tests/test_*.py",
        "compile_mode": "import",
        "compile_paths": ("__init__.py", "__main__.py", "pyproject.toml"),
    },
    "gospider": {
        "runtime": "go",
        "source_glob": "**/*.go",
        "source_excludes_suffixes": ("_test.go",),
        "test_glob": "**/*_test.go",
        "compile_mode": "exe",
        "compile_paths": ("go.mod", "cmd/gospider/main.go"),
    },
    "rustspider": {
        "runtime": "rust",
        "source_glob": "src/**/*.rs",
        "test_glob": "tests/*.rs",
        "compile_mode": "exe",
        "compile_paths": ("Cargo.toml", "src/main.rs"),
    },
}


def _count_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def _python_source_files(base: Path) -> list[Path]:
    files: list[Path] = []
    excludes = FRAMEWORKS["pyspider"]["source_excludes"]
    for path in base.rglob("*.py"):
        relative = path.relative_to(base)
        if any(part in excludes for part in relative.parts):
            continue
        files.append(path)
    return files


def _source_files(root: Path, framework: str) -> list[Path]:
    base = root / framework
    if framework == "pyspider":
        return _python_source_files(base)

    config = FRAMEWORKS[framework]
    files = list(base.glob(config["source_glob"]))
    suffixes = config.get("source_excludes_suffixes", ())
    if suffixes:
        files = [path for path in files if not any(str(path).endswith(suffix) for suffix in suffixes)]
    return [path for path in files if path.is_file()]


def _count_tests(root: Path, framework: str) -> int:
    return len(list((root / framework).glob(FRAMEWORKS[framework]["test_glob"])))


def _docs_verified(root: Path, framework: str) -> tuple[bool, str]:
    readme = root / framework / "README.md"
    if not readme.exists():
        return False, "README missing"
    content = readme.read_text(encoding="utf-8")
    missing = [token for token in README_TOKENS if token not in content]
    if missing:
        return False, f"README missing sections: {', '.join(missing)}"
    return True, "README covers Quick Start, API, Deploy"


def _compile_verified(root: Path, framework: str) -> tuple[bool, str]:
    paths = FRAMEWORKS[framework]["compile_paths"]
    missing = [path for path in paths if not (root / framework / path).exists()]
    if missing:
        return False, f"missing compile assets: {', '.join(missing)}"
    return True, FRAMEWORKS[framework]["compile_mode"]


def collect_framework_standards(root: Path, scorecard: dict | None = None) -> dict:
    scorecard = scorecard or generate_framework_scorecard.collect_framework_scorecard(root)
    frameworks: dict[str, dict] = {}
    overall_passed = True

    for framework, meta in FRAMEWORKS.items():
        line_count = sum(_count_lines(path) for path in _source_files(root, framework))
        test_count = _count_tests(root, framework)
        compile_ok, compile_detail = _compile_verified(root, framework)
        docs_ok, docs_detail = _docs_verified(root, framework)
        distributed = scorecard["frameworks"][framework]["evidence"]["distributed"]
        distributed_ok = distributed == "verified"

        standard_results = {
            "code_volume": {
                "summary": "passed" if line_count > 100 else "failed",
                "actual": line_count,
                "threshold": 100,
            },
            "tests": {
                "summary": "passed" if test_count > 20 else "failed",
                "actual": test_count,
                "threshold": 20,
            },
            "compile_validation": {
                "summary": "passed" if compile_ok else "failed",
                "mode": meta["compile_mode"],
                "detail": compile_detail,
            },
            "distributed": {
                "summary": "passed" if distributed_ok else "failed",
                "detail": distributed,
            },
            "documentation": {
                "summary": "passed" if docs_ok else "failed",
                "detail": docs_detail,
            },
            "stability": {
                "summary": "passed" if scorecard["frameworks"][framework]["evidence"]["stability_verified"] else "failed",
                "detail": "runtime stability gate",
            },
            "stability_trends": {
                "summary": "passed" if scorecard["frameworks"][framework]["evidence"]["stability_trends_verified"] else "failed",
                "detail": "runtime stability trends gate",
            },
            "governance": {
                "summary": "passed" if scorecard["frameworks"][framework]["evidence"]["maturity_governance_verified"] else "failed",
                "detail": "maturity governance gate",
            },
            "control_plane": {
                "summary": "passed" if scorecard["frameworks"][framework]["evidence"]["control_plane_verified"] else "failed",
                "detail": "shared superspider control-plane gate",
            },
            "legacy_isolation": {
                "summary": "passed" if scorecard["frameworks"][framework]["evidence"]["legacy_isolation_verified"] else "failed",
                "detail": "legacy surface isolation gate",
            },
        }

        framework_passed = all(item["summary"] == "passed" for item in standard_results.values())
        frameworks[framework] = {
            "runtime": meta["runtime"],
            "summary": "passed" if framework_passed else "failed",
            "standards": standard_results,
        }
        overall_passed = overall_passed and framework_passed

    return {
        "command": "verify-framework-standards",
        "summary": "passed" if overall_passed else "failed",
        "summary_text": "framework standards matrix computed from source, tests, build entrypoints, distributed evidence, and docs",
        "exit_code": 0 if overall_passed else 1,
        "frameworks": frameworks,
    }


def render_markdown(report: dict) -> str:
    def cell(summary: str, detail: str) -> str:
        icon = "✅" if summary == "passed" else "❌"
        return f"{icon} {detail}"

    lines = [
        "# Framework Standards",
        "",
        "| 标准 | JavaSpider | PySpider | GoSpider | RustSpider |",
        "| --- | --- | --- | --- | --- |",
    ]

    rows = [
        (
            "代码量>100",
            lambda item: str(item["standards"]["code_volume"]["actual"]),
            lambda item: item["standards"]["code_volume"]["summary"],
        ),
        (
            "测试>20",
            lambda item: str(item["standards"]["tests"]["actual"]),
            lambda item: item["standards"]["tests"]["summary"],
        ),
        (
            "编译验证",
            lambda item: item["standards"]["compile_validation"]["mode"],
            lambda item: item["standards"]["compile_validation"]["summary"],
        ),
        (
            "分布式",
            lambda item: item["standards"]["distributed"]["detail"],
            lambda item: item["standards"]["distributed"]["summary"],
        ),
        (
            "文档",
            lambda item: item["standards"]["documentation"]["detail"],
            lambda item: item["standards"]["documentation"]["summary"],
        ),
        (
            "稳定性",
            lambda item: item["standards"]["stability"]["detail"],
            lambda item: item["standards"]["stability"]["summary"],
        ),
        (
            "趋势",
            lambda item: item["standards"]["stability_trends"]["detail"],
            lambda item: item["standards"]["stability_trends"]["summary"],
        ),
        (
            "治理",
            lambda item: item["standards"]["governance"]["detail"],
            lambda item: item["standards"]["governance"]["summary"],
        ),
        (
            "统一控制面",
            lambda item: item["standards"]["control_plane"]["detail"],
            lambda item: item["standards"]["control_plane"]["summary"],
        ),
        (
            "Legacy隔离",
            lambda item: item["standards"]["legacy_isolation"]["detail"],
            lambda item: item["standards"]["legacy_isolation"]["summary"],
        ),
    ]

    for label, detail_fn, summary_fn in rows:
        values = []
        for framework in ("javaspider", "pyspider", "gospider", "rustspider"):
            info = report["frameworks"][framework]
            values.append(cell(summary_fn(info), detail_fn(info)))
        lines.append(f"| {label} | {' | '.join(values)} |")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify four-framework standards matrix")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_framework_standards(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-framework-standards:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
