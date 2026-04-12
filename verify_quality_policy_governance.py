from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonical_policy_digest(path: Path) -> str:
    obj = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def collect_quality_policy_governance_report(root: Path) -> dict:
    governance_path = root / "quality-policy-governance.json"
    policy_path = root / "quality-thresholds.json"
    checks: list[dict] = []

    if not governance_path.exists():
        return {
            "command": "verify-quality-policy-governance",
            "summary": "failed",
            "summary_text": "0 passed, 1 failed",
            "exit_code": 1,
            "checks": [{
                "name": "governance-file",
                "status": "failed",
                "details": "quality-policy-governance.json is missing",
            }],
        }

    governance = json.loads(governance_path.read_text(encoding="utf-8"))
    checks.append({
        "name": "governance-file",
        "status": "passed",
        "details": str(governance_path),
    })

    if not policy_path.exists():
        checks.append({
            "name": "policy-file",
            "status": "failed",
            "details": "quality-thresholds.json is missing",
        })
    else:
        checks.append({
            "name": "policy-file",
            "status": "passed",
            "details": str(policy_path),
        })

    expected_digest = canonical_policy_digest(policy_path) if policy_path.exists() else ""
    if governance.get("policy_digest") == expected_digest:
        checks.append({
            "name": "policy-digest",
            "status": "passed",
            "details": expected_digest,
        })
    else:
        checks.append({
            "name": "policy-digest",
            "status": "failed",
            "details": f"expected {expected_digest}, got {governance.get('policy_digest')!r}",
        })

    policy = json.loads(policy_path.read_text(encoding="utf-8")) if policy_path.exists() else {}
    profiles = set((policy.get("profiles") or {}).keys())
    if governance.get("default_profile") in profiles and governance.get("release_profile") in profiles:
        checks.append({
            "name": "profile-registry",
            "status": "passed",
            "details": f"default={governance.get('default_profile')} release={governance.get('release_profile')}",
        })
    else:
        checks.append({
            "name": "profile-registry",
            "status": "failed",
            "details": f"profile registry mismatch against available profiles {sorted(profiles)!r}",
        })

    for document in governance.get("required_documents", []):
        doc_path = root / document
        if not doc_path.exists():
            checks.append({
                "name": f"document:{document}",
                "status": "failed",
                "details": "required governance document is missing",
            })
            continue
        content = doc_path.read_text(encoding="utf-8")
        missing_sections = [
            section
            for section in governance.get("required_sections", [])
            if section not in content
        ]
        if missing_sections:
            checks.append({
                "name": f"document:{document}",
                "status": "failed",
                "details": f"missing sections: {missing_sections!r}",
            })
        else:
            checks.append({
                "name": f"document:{document}",
                "status": "passed",
                "details": str(doc_path),
            })

    passed = sum(1 for check in checks if check["status"] == "passed")
    failed = len(checks) - passed
    exit_code = 1 if failed else 0
    return {
        "command": "verify-quality-policy-governance",
        "summary": "failed" if exit_code else "passed",
        "summary_text": f"{passed} passed, {failed} failed",
        "exit_code": exit_code,
        "governance": {
            "version": governance.get("version", ""),
            "policy_path": governance.get("policy_path", ""),
            "policy_digest": governance.get("policy_digest", ""),
            "default_profile": governance.get("default_profile", ""),
            "release_profile": governance.get("release_profile", ""),
        },
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify that quality policy changes are governed by digest and documentation records")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument("--json", action="store_true", help="print governance report as JSON")
    args = parser.parse_args(argv)

    report = collect_quality_policy_governance_report(Path(args.root).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("verify-quality-policy-governance:", report["summary"])
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
