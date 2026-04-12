from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


DELETED_WRAPPERS = [
    "gospider/browser.go",
    "pyspider/browser.py",
    "rustspider/src/playwright.rs",
    "javaspider/src/main/java/com/javaspider/examples/SimpleYouTubeSpider.java",
]

DEPRECATED_JAVA_EXAMPLES = [
    "javaspider/examples/legacy/QQVideoSpiderHttpClient.java",
    "javaspider/examples/legacy/TencentVideoSpider.java",
    "javaspider/examples/legacy/TencentVideoSpiderEnhanced.java",
    "javaspider/examples/legacy/UniversalMediaSpider.java",
    "javaspider/examples/legacy/YoukuMediaSpider.java",
    "javaspider/examples/legacy/YoukuVideoSpider.java",
    "javaspider/examples/legacy/YoukuVideoSpiderEnhanced.java",
    "javaspider/examples/legacy/YouTubePlaylistSpider.java",
    "javaspider/examples/legacy/YouTubeVideoSpider.java",
]


def collect_legacy_surfaces_report(root: Path) -> dict:
    checks: list[dict] = []

    for relative in DELETED_WRAPPERS:
        path = root / relative
        checks.append(
            {
                "name": f"removed:{relative}",
                "status": "passed" if not path.exists() else "failed",
                "details": "wrapper removed" if not path.exists() else "legacy wrapper still exists",
            }
        )

    legacy_doc = root / "docs" / "legacy-surfaces.md"
    content = legacy_doc.read_text(encoding="utf-8")
    checks.append(
        {
            "name": "legacy-doc",
            "status": "passed" if "compatibility-only" in content and "Delete a legacy surface only after" in content else "failed",
            "details": str(legacy_doc),
        }
    )

    examples_readme = root / "javaspider" / "src" / "main" / "java" / "com" / "javaspider" / "examples" / "README.md"
    readme_content = examples_readme.read_text(encoding="utf-8")
    checks.append(
        {
            "name": "java-examples-readme",
            "status": "passed" if "legacy" in readme_content.lower() and "canonical public surface" in readme_content.lower() else "failed",
            "details": str(examples_readme),
        }
    )
    legacy_readme = root / "javaspider" / "examples" / "legacy" / "README.md"
    checks.append(
        {
            "name": "java-legacy-readme",
            "status": "passed" if legacy_readme.exists() else "failed",
            "details": str(legacy_readme),
        }
    )

    for relative in DEPRECATED_JAVA_EXAMPLES:
        path = root / relative
        if not path.exists():
            checks.append(
                {
                    "name": f"deprecated:{relative}",
                    "status": "failed",
                    "details": "expected legacy source file to exist for reference-only isolation",
                }
            )
            continue
        source = path.read_text(encoding="utf-8")
        checks.append(
            {
                "name": f"deprecated:{relative}",
                "status": "passed" if "@Deprecated" in source else "failed",
                "details": "marked deprecated" if "@Deprecated" in source else "missing @Deprecated marker",
            }
        )

    pom_path = root / "javaspider" / "pom.xml"
    pom = pom_path.read_text(encoding="utf-8")
    checks.append(
        {
            "name": "java-build-excludes-legacy-examples",
            "status": "passed" if "com/javaspider/examples/**" in pom else "failed",
            "details": "legacy Java examples excluded from production compile" if "com/javaspider/examples/**" in pom else "missing maven compiler exclude",
        }
    )

    jar_path = root / "javaspider" / "target" / "javaspider-1.0.0.jar"
    if jar_path.exists() and jar_path.stat().st_mtime >= pom_path.stat().st_mtime:
        with zipfile.ZipFile(jar_path) as jar:
            legacy_prefixes = [
                f"com/javaspider/examples/{Path(relative).stem}"
                for relative in DEPRECATED_JAVA_EXAMPLES
            ]
            legacy_entries = [
                name for name in jar.namelist()
                if any(name.startswith(prefix) and name.endswith(".class") for prefix in legacy_prefixes)
            ]
        stale_class_dirs = [root / "javaspider" / "target" / "classes" / prefix for prefix in legacy_prefixes]
        stale_build = any(path.exists() for path in stale_class_dirs)
        checks.append(
            {
                "name": "java-release-jar-excludes-legacy-examples",
                "status": "passed" if not legacy_entries else ("skipped" if stale_build else "failed"),
                "details": (
                    "legacy Java examples absent from release jar"
                    if not legacy_entries
                    else ("release jar appears stale; rerun a clean package to verify artifact isolation" if stale_build else f"jar still contains {legacy_entries[:3]!r}")
                ),
            }
        )
    else:
        checks.append(
            {
                "name": "java-release-jar-excludes-legacy-examples",
                "status": "skipped",
                "details": "release jar missing or stale relative to pom; build artifact check skipped",
            }
        )

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = sum(1 for check in checks if check["status"] == "failed")
    return {
        "command": "verify-legacy-surfaces",
        "summary": "passed" if failed == 0 else "failed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": 0 if failed == 0 else 1,
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify that legacy compatibility surfaces are removed or isolated correctly")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print report as JSON")
    args = parser.parse_args(argv)

    report = collect_legacy_surfaces_report(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-legacy-surfaces:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
