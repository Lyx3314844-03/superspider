from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_publish_scripts_run_aggregate_verify_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_env.py --json" in powershell_script
    assert "verify_env.py --json" in bash_script

    assert powershell_script.index("verify_env.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_env.py --json") < bash_script.index("git add .")


def test_publish_scripts_do_not_overwrite_existing_repo_files():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "if (-not (Test-Path \".gitignore\"))" in powershell_script
    assert "if (-not (Test-Path \"LICENSE\"))" in powershell_script
    assert "if [ ! -f \".gitignore\" ]" in bash_script
    assert "if [ ! -f \"LICENSE\" ]" in bash_script
    assert "if [ ! -f \"CONTRIBUTING.md\" ]" in bash_script


def test_publish_scripts_skip_commit_when_nothing_is_staged():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "git diff --cached --quiet" in powershell_script
    assert "git diff --cached --quiet" in bash_script


def test_powershell_publish_script_checks_remote_add_exit_code():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")

    remote_section = powershell_script.split("Write-Host \"📤 推送到 GitHub...\" -ForegroundColor Yellow", 1)[1]

    assert "git remote add origin $REPO_URL 2>$null" in remote_section
    assert "try {" not in remote_section
    assert "if ($LASTEXITCODE -eq 0)" in remote_section
    assert "git remote set-url origin $REPO_URL" in remote_section


def test_publish_scripts_support_non_interactive_publish_configuration():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "PUBLISH_MODE" in powershell_script
    assert "GITHUB_USERNAME" in powershell_script
    assert "PUBLISH_MODE" in bash_script
    assert "GITHUB_USERNAME" in bash_script


def test_publish_scripts_run_smoke_test_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "smoke_test.py --json" in powershell_script
    assert "smoke_test.py --json" in bash_script
    assert powershell_script.index("smoke_test.py --json") < powershell_script.index("git add .")
    assert bash_script.index("smoke_test.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_version_check_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_version.py --json" in powershell_script
    assert "verify_version.py --json" in bash_script
    assert powershell_script.index("verify_version.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_version.py --json") < bash_script.index("git add .")


def test_four_framework_workflow_has_aggregate_verify_job():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "verify-env:" in workflow
    assert "name: Verify Aggregate Environment" in workflow
    assert "python verify_env.py --json" in workflow
    assert "ffmpeg" in workflow.lower()


def test_four_framework_workflow_installs_browser_runtime_for_aggregate_verify():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "browser-actions/setup-chrome@v2" in workflow
    assert "install-dependencies: true" in workflow


def test_four_framework_workflow_runs_root_release_guard_tests():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python -m pytest tests -p no:cacheprovider" in workflow


def test_four_framework_workflow_runs_root_smoke_test():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python smoke_test.py --json" in workflow


def test_four_framework_workflow_runs_root_version_check():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_version.py --json" in workflow


def test_four_framework_workflow_always_uploads_aggregate_artifacts():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "name: Upload aggregate verify artifacts" in workflow
    assert "if: always()" in workflow
    assert "artifacts/verify-env.json" in workflow
    assert "artifacts/smoke-test.json" in workflow
    assert "artifacts/root-tests.log" in workflow


def test_four_framework_workflow_enforces_rust_fmt_check():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "cargo fmt --check" in workflow


def test_four_framework_workflow_runs_javaspider_verify_not_only_test():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "mvn verify" in workflow


def test_four_framework_workflow_installs_pyspider_dev_dependencies_and_collects_coverage():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert 'pip install -e ".[dev]"' in workflow
    assert "--cov=pyspider" in workflow
    assert "coverage.xml" in workflow


def test_release_workflow_exists_and_runs_root_release_gates():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "push:" in workflow
    assert "tags: [ 'v*' ]" in workflow or "tags:\n      - 'v*'" in workflow
    assert "python -m pytest tests -p no:cacheprovider" in workflow
    assert "python verify_version.py --json" in workflow
    assert "python verify_env.py --json" in workflow
    assert "python smoke_test.py --json" in workflow


def test_release_workflow_only_creates_release_for_tags():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "if: startsWith(github.ref, 'refs/tags/v')" in workflow
    assert "gh release create" in workflow
    assert "contents: write" in workflow


def test_release_workflow_enforces_rust_quality_gates():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "cargo clippy --all-targets -- -D warnings" in workflow
    assert "cargo fmt --check" in workflow


def test_release_workflow_runs_javaspider_verify_not_only_test():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "mvn -q verify" in workflow or "mvn verify" in workflow


def test_release_workflow_installs_pyspider_dev_dependencies_and_collects_coverage():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert 'pip install -e "./pyspider[dev]"' in workflow or 'pip install -e ".[dev]"' in workflow
    assert "--cov=pyspider" in workflow
    assert "coverage.xml" in workflow


def test_rust_quality_workflow_exists_and_runs_fmt_clippy_and_tests():
    workflow = (ROOT / ".github" / "workflows" / "rustspider-quality.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "push:" in workflow
    assert "pull_request:" in workflow
    assert "dtolnay/rust-toolchain@stable" in workflow
    assert "cargo test" in workflow
    assert "cargo fmt --check" in workflow
    assert "cargo clippy --all-targets -- -D warnings" in workflow
