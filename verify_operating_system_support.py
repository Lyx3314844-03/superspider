from __future__ import annotations

import argparse
import json
from pathlib import Path

import smoke_test
import verify_env


OPERATING_SYSTEM_MATRIX = {
    "windows": {
        "runner": "windows-latest",
        "frameworks": {
            "pyspider": ["pyspider/run-framework.bat"],
            "gospider": ["gospider/build.bat", "gospider/run-framework.bat"],
            "javaspider": ["javaspider/build.bat", "javaspider/run-framework.bat"],
            "rustspider": ["rustspider/build.bat", "rustspider/run-framework.bat"],
        },
    },
    "linux": {
        "runner": "ubuntu-latest",
        "frameworks": {
            "pyspider": ["pyspider/run-framework.sh"],
            "gospider": ["gospider/build.sh", "gospider/run-framework.sh"],
            "javaspider": ["javaspider/build.sh", "javaspider/run-framework.sh"],
            "rustspider": ["rustspider/build.sh", "rustspider/run-framework.sh"],
        },
    },
    "macos": {
        "runner": "macos-latest",
        "frameworks": {
            "pyspider": ["pyspider/run-framework.sh"],
            "gospider": ["gospider/build.sh", "gospider/run-framework.sh"],
            "javaspider": ["javaspider/build.sh", "javaspider/run-framework.sh"],
            "rustspider": ["rustspider/build.sh", "rustspider/run-framework.sh"],
        },
    },
}

WORKFLOW_PATH = Path(".github/workflows/framework-os-matrix.yml")
OS_ARTIFACT_DIR = Path("artifacts/os-support-artifacts")
OS_RUNNERS = ("ubuntu-latest", "windows-latest", "macos-latest")


def collect_operating_system_support_report(root: Path) -> dict:
    checks: list[dict] = []

    workflow = root / WORKFLOW_PATH
    workflow_text = workflow.read_text(encoding="utf-8") if workflow.exists() else ""
    workflow_tokens = (
        "ubuntu-latest",
        "windows-latest",
        "macos-latest",
        "python verify_operating_system_support.py --json",
        "python verify_env.py --json",
        "python smoke_test.py --json",
    )
    missing_tokens = [token for token in workflow_tokens if token not in workflow_text]
    checks.append(
        {
            "name": "framework-os-matrix-workflow",
            "status": "passed" if workflow.exists() and not missing_tokens else "failed",
            "details": "framework OS matrix workflow present"
            if workflow.exists() and not missing_tokens
            else f"missing workflow or tokens: {missing_tokens!r}",
        }
    )

    artifact_dir = root / OS_ARTIFACT_DIR
    if artifact_dir.exists():
        missing_os_artifacts: list[str] = []
        for runner in OS_RUNNERS:
            for prefix in ("verify-env", "smoke-test", "operating-system-support"):
                candidate = artifact_dir / f"{prefix}-{runner}.json"
                if not candidate.exists():
                    missing_os_artifacts.append(candidate.name)
        checks.append(
            {
                "name": "framework-os-matrix-artifacts",
                "status": "passed" if not missing_os_artifacts else "failed",
                "details": "actual windows/linux/macos artifact set present"
                if not missing_os_artifacts
                else f"missing OS artifacts: {missing_os_artifacts!r}",
            }
        )

    platforms: dict[str, dict] = {}
    for os_name, spec in OPERATING_SYSTEM_MATRIX.items():
        frameworks: dict[str, dict] = {}
        for framework, relative_paths in spec["frameworks"].items():
            missing_files = [path for path in relative_paths if not (root / path).exists()]
            checks.append(
                {
                    "name": f"{framework}-{os_name}-launcher-surface",
                    "status": "passed" if not missing_files else "failed",
                    "details": "launcher/build surface present"
                    if not missing_files
                    else f"missing files: {missing_files!r}",
                }
            )
            frameworks[framework] = {
                "files": relative_paths,
                "status": "passed" if not missing_files else "failed",
            }
        platforms[os_name] = {
            "runner": spec["runner"],
            "frameworks": frameworks,
        }

    darwin_verify_env = verify_env.build_framework_commands("Darwin")
    darwin_smoke = smoke_test.build_smoke_commands("Darwin")

    checks.append(
        {
            "name": "darwin-verify-env-surface",
            "status": "passed"
            if darwin_verify_env["javaspider"]["command"][:2] == ["bash", "-lc"]
            and darwin_verify_env["pyspider"]["command"][-2:] == ["doctor", "--json"]
            else "failed",
            "details": "Darwin verify_env commands resolve to Unix launch surface",
        }
    )
    checks.append(
        {
            "name": "darwin-smoke-surface",
            "status": "passed"
            if darwin_smoke["javaspider"]["command"][:2] == ["bash", "-lc"]
            and darwin_smoke["pyspider"]["command"][-1] == "version"
            else "failed",
            "details": "Darwin smoke commands resolve to Unix launch surface",
        }
    )

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    return {
        "command": "verify-operating-system-support",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 0 if failed == 0 else 1,
        "checks": checks,
        "platforms": platforms,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Operating System Support",
        "",
        f"Summary: {report['summary_text']}",
        "",
        "## Matrix",
        "",
    ]
    for os_name, spec in report["platforms"].items():
        lines.append(f"- `{os_name}` via `{spec['runner']}`")
        for framework, framework_spec in spec["frameworks"].items():
            files = ", ".join(f"`{path}`" for path in framework_spec["files"])
            lines.append(f"  - `{framework}`: {framework_spec['status']} ({files})")

    if any(check["name"] == "framework-os-matrix-artifacts" for check in report["checks"]):
        lines.extend(
            [
                "",
                "## Runtime Artifacts",
                "",
                f"- actual matrix artifacts root: `{OS_ARTIFACT_DIR.as_posix()}`",
            ]
        )

    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| Check | Status | Details |",
            "| --- | --- | --- |",
        ]
    )
    for check in report["checks"]:
        lines.append(f"| {check['name']} | {check['status']} | {check['details']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Windows/Linux/macOS support surfaces for the four-runtime suite")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_operating_system_support_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-operating-system-support:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
