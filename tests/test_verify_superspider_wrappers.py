from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_superspider_control_plane_benchmark
import verify_superspider_control_plane_install_smoke
import verify_superspider_control_plane_package
import verify_superspider_control_plane_postgres_backend
import verify_superspider_control_plane_release


ROOT = Path(__file__).resolve().parents[1]


def test_wrapper_reports_missing_superspider_script(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPERSPIDER_ROOT", str(tmp_path))

    report = verify_superspider_control_plane_release.collect_report(ROOT)

    assert report["summary"] == "failed"
    assert "missing script" in report["summary_text"]


def test_wrappers_use_superspider_root_override(monkeypatch, tmp_path):
    superspider_root = tmp_path / "superspider"
    superspider_root.mkdir()
    (superspider_root / "verify_control_plane_release.py").write_text("pass", encoding="utf-8")
    (superspider_root / "verify_control_plane_benchmark.py").write_text("pass", encoding="utf-8")
    (superspider_root / "verify_control_plane_install_smoke.py").write_text("pass", encoding="utf-8")
    (superspider_root / "verify_control_plane_package.py").write_text("pass", encoding="utf-8")
    (superspider_root / "verify_control_plane_postgres_backend.py").write_text("pass", encoding="utf-8")

    def fake_run(command, cwd, capture_output, text, check, timeout=None):
        payload = {
            "command": "foreign",
            "summary": "passed",
            "summary_text": "ok",
            "exit_code": 0,
            "checks": [],
        }

        class Result:
            returncode = 0
            stdout = json.dumps(payload)
            stderr = ""

        assert cwd == superspider_root
        return Result()

    monkeypatch.setenv("SUPERSPIDER_ROOT", str(superspider_root))
    monkeypatch.setattr(verify_superspider_control_plane_release.subprocess, "run", fake_run)
    monkeypatch.setattr(verify_superspider_control_plane_benchmark.subprocess, "run", fake_run)
    monkeypatch.setattr(verify_superspider_control_plane_install_smoke.subprocess, "run", fake_run)
    monkeypatch.setattr(verify_superspider_control_plane_package.subprocess, "run", fake_run)
    monkeypatch.setattr(verify_superspider_control_plane_postgres_backend.subprocess, "run", fake_run)

    release = verify_superspider_control_plane_release.collect_report(ROOT)
    benchmark = verify_superspider_control_plane_benchmark.collect_report(ROOT)
    install_smoke = verify_superspider_control_plane_install_smoke.collect_report(ROOT)
    package = verify_superspider_control_plane_package.collect_report(ROOT)
    postgres = verify_superspider_control_plane_postgres_backend.collect_report(ROOT)

    assert release["summary"] == "passed"
    assert benchmark["summary"] == "passed"
    assert install_smoke["summary"] == "passed"
    assert package["summary"] == "passed"
    assert postgres["summary"] == "passed"
