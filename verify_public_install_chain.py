from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _resolve_command(command: list[str]) -> list[str]:
    if not command:
        return command
    executable = (
        shutil.which(command[0])
        or shutil.which(f"{command[0]}.cmd")
        or shutil.which(f"{command[0]}.exe")
    )
    if executable:
        return [executable, *command[1:]]
    return command


def _run(command: list[str], cwd: Path, timeout: int = 600) -> dict:
    resolved = _resolve_command(command)
    completed = subprocess.run(
        resolved,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    details = "\n".join(
        part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
    ).strip()
    return {
        "command": resolved,
        "exit_code": completed.returncode,
        "status": "passed" if completed.returncode == 0 else "failed",
        "details": details or "command completed",
    }


def _doc_check(root: Path) -> dict:
    readme = (root / "README.md").read_text(encoding="utf-8")
    framework_readmes = [
        (root / "gospider" / "README.md").read_text(encoding="utf-8"),
        (root / "rustspider" / "README.md").read_text(encoding="utf-8"),
        (root / "javaspider" / "README.md").read_text(encoding="utf-8"),
        (root / "pyspider" / "README.md").read_text(encoding="utf-8"),
    ]
    install = (root / "docs" / "INSTALL.md").read_text(encoding="utf-8")
    release = (root / "docs" / "RELEASE.md").read_text(encoding="utf-8")
    doc_bodies = [readme, install, release, *framework_readmes]
    lowered_bodies = [body.lower() for body in doc_bodies]

    expected_tokens = [
        "built-in metadata runner",
        "project runner artifact",
        "go build -o dist/gospider ./cmd/gospider",
        "mvn -q -dmaven.test.skip=true package",
        "cargo build --release --bin rustspider",
        "python -m pip install -e .",
        "verify_public_install_chain.py",
    ]
    missing = [
        token for token in expected_tokens
        if all(token not in body for body in lowered_bodies)
    ]
    legacy_tokens = [
        "metadata-fallback",
        "metadata fallback",
        "artifact runner",
        "built runner artifact",
        "built project artifact",
    ]
    legacy_hits = sorted({
        token
        for body in lowered_bodies
        for token in legacy_tokens
        if token in body
    })
    if legacy_hits:
        missing.append("public docs still contain legacy runner phrasing: " + ", ".join(legacy_hits))
    return {
        "name": "public-docs",
        "status": "passed" if not missing else "failed",
        "details": "public install docs aligned" if not missing else "; ".join(missing),
    }


def collect_report(root: Path) -> dict:
    checks: list[dict] = [_doc_check(root)]

    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        go_binary = tmpdir / ("gospider.exe" if platform.system() == "Windows" else "gospider")
        go_check = _run(
            ["go", "build", "-o", str(go_binary), "./cmd/gospider"],
            root / "gospider",
            timeout=300,
        )
        go_check["name"] = "gospider-public-build"
        if go_check["status"] == "passed" and not go_binary.exists():
            go_check["status"] = "failed"
            go_check["details"] = "go build succeeded but binary was not created"
        checks.append(go_check)
        if go_check["status"] == "passed":
            go_smoke = _run([str(go_binary), "version"], root, timeout=60)
            go_smoke["name"] = "gospider-public-smoke"
            checks.append(go_smoke)

    rust_binary = root / "rustspider" / "target" / "release" / ("rustspider.exe" if platform.system() == "Windows" else "rustspider")
    rust_check = _run(
        ["cargo", "build", "--release", "--bin", "rustspider"],
        root / "rustspider",
        timeout=900,
    )
    rust_check["name"] = "rustspider-public-build"
    if rust_check["status"] == "passed" and not rust_binary.exists():
        rust_check["status"] = "failed"
        rust_check["details"] = "cargo build succeeded but release binary was not created"
    checks.append(rust_check)
    if rust_check["status"] == "passed":
        rust_smoke = _run([str(rust_binary), "version"], root / "rustspider", timeout=60)
        rust_smoke["name"] = "rustspider-public-smoke"
        checks.append(rust_smoke)

    java_jar = root / "javaspider" / "target" / "javaspider-1.0.0.jar"
    java_check = _run(
        ["mvn", "-q", "-Dmaven.javadoc.skip=true", "-Dmaven.test.skip=true", "clean", "package", "dependency:copy-dependencies"],
        root / "javaspider",
        timeout=900,
    )
    java_check["name"] = "javaspider-public-package"
    if java_check["status"] == "passed" and not java_jar.exists():
        java_check["status"] = "failed"
        java_check["details"] = "maven package succeeded but target javaspider jar was not created"
    checks.append(java_check)
    if java_check["status"] == "passed":
        java_smoke = _run(
            [
                "java",
                "-cp",
                f"{java_jar}{os.pathsep}{root / 'javaspider' / 'target' / 'dependency' / '*'}",
                "com.javaspider.EnhancedSpider",
                "version",
            ],
            root / "javaspider",
            timeout=60,
        )
        java_smoke["name"] = "javaspider-public-smoke"
        checks.append(java_smoke)

    with tempfile.TemporaryDirectory() as py_tmpdir_str:
        py_tmpdir = Path(py_tmpdir_str)
        py_site = py_tmpdir / "site"
        py_check = _run(
            [sys.executable, "-m", "pip", "install", ".", "--no-deps", "--target", str(py_site)],
            root / "pyspider",
            timeout=900,
        )
        py_check["name"] = "pyspider-public-package"
        checks.append(py_check)
        if py_check["status"] == "passed":
            py_smoke = _run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import sys; "
                        f"sys.path.insert(0, r'{py_site}'); "
                        "from pyspider import __main__ as runtime; "
                        "raise SystemExit(runtime._print_capabilities())"
                    ),
                ],
                root,
                timeout=60,
            )
            py_smoke["name"] = "pyspider-public-smoke"
            checks.append(py_smoke)

    failed = sum(1 for check in checks if check["status"] != "passed")
    passed = len(checks) - failed
    return {
        "command": "verify-public-install-chain",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 0 if failed == 0 else 1,
        "checks": checks,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Public Install Chain Report",
        "",
        f"Summary: {report['summary_text']}",
        "",
        "| Check | Status |",
        "| --- | --- |",
    ]
    for check in report["checks"]:
        lines.append(f"| {check['name']} | {check['status']} |")
    lines.append("")
    for check in report["checks"]:
        lines.append(f"## {check['name']}")
        lines.append("")
        lines.append(f"- Status: {check['status']}")
        if "command" in check:
            lines.append(f"- Command: `{' '.join(check['command'])}`")
        lines.append(f"- Details: {check['details']}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify public install/build chain for Go, Rust, and Java runtimes")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown-out", default="", help="optional markdown output path")
    args = parser.parse_args(argv)

    report = collect_report(Path(args.root).resolve())
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-public-install-chain:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
