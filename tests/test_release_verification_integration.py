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


def test_publish_scripts_show_current_origin_before_push():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "git remote get-url origin" in powershell_script
    assert "git remote get-url origin" in bash_script
    assert "当前 origin" in powershell_script
    assert "当前 origin" in bash_script


def test_publish_scripts_prepare_artifact_directories_before_verifiers():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "发布产物目录已准备" in powershell_script
    assert "发布产物目录已准备" in bash_script
    assert "artifacts\\quality-events-history" in powershell_script
    assert "artifacts/quality-events-history" in bash_script
    assert powershell_script.index("发布产物目录已准备") < powershell_script.index("verify_runtime_stability.py --json")
    assert bash_script.index("发布产物目录已准备") < bash_script.index("verify_runtime_stability.py --json")


def test_publish_scripts_require_superspider_root_before_release_gate():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "SUPERSPIDER_ROOT" in powershell_script
    assert "SUPERSPIDER_ROOT" in bash_script
    assert "未找到 superspider 仓库" in powershell_script
    assert "未找到 superspider 仓库" in bash_script


def test_publish_scripts_support_non_interactive_publish_configuration():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "PUBLISH_MODE" in powershell_script
    assert "GITHUB_USERNAME" in powershell_script
    assert "PUBLISH_MODE" in bash_script
    assert "GITHUB_USERNAME" in bash_script


def test_publish_scripts_default_to_spider_repo_name():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert '$REPO_NAME = "spider"' in powershell_script
    assert 'REPO_NAME="spider"' in bash_script


def test_publish_scripts_skip_hints_target_spider_repo():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "https://github.com/YOUR_USERNAME/spider.git" in powershell_script
    assert "https://github.com/YOUR_USERNAME/spider.git" in bash_script
    assert "superspider.git" not in powershell_script
    assert "superspider.git" not in bash_script


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


def test_publish_scripts_run_runtime_readiness_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_runtime_readiness.py --json" in powershell_script
    assert "verify_runtime_readiness.py --json" in bash_script
    assert powershell_script.index("verify_runtime_readiness.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_runtime_readiness.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_public_install_chain_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_public_install_chain.py --json" in powershell_script
    assert "verify_public_install_chain.py --json" in bash_script
    assert powershell_script.index("verify_public_install_chain.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_public_install_chain.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_runtime_core_capabilities_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_runtime_core_capabilities.py --json" in powershell_script
    assert "verify_runtime_core_capabilities.py --json" in bash_script
    assert powershell_script.index("verify_runtime_core_capabilities.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_runtime_core_capabilities.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_operator_products_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_operator_products.py --json" in powershell_script
    assert "verify_operator_products.py --json" in bash_script
    assert powershell_script.index("verify_operator_products.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_operator_products.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_operating_system_support_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_operating_system_support.py --json" in powershell_script
    assert "verify_operating_system_support.py --json" in bash_script
    assert powershell_script.index("verify_operating_system_support.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_operating_system_support.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_kernel_homogeneity_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_kernel_homogeneity.py --json" in powershell_script
    assert "verify_kernel_homogeneity.py --json" in bash_script
    assert powershell_script.index("verify_kernel_homogeneity.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_kernel_homogeneity.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_observability_evidence_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_observability_evidence.py --json" in powershell_script
    assert "verify_observability_evidence.py --json" in bash_script
    assert powershell_script.index("verify_observability_evidence.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_observability_evidence.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_cache_incremental_evidence_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_cache_incremental_evidence.py --json" in powershell_script
    assert "verify_cache_incremental_evidence.py --json" in bash_script
    assert powershell_script.index("verify_cache_incremental_evidence.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_cache_incremental_evidence.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_ecosystem_marketplace_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_ecosystem_marketplace.py --json" in powershell_script
    assert "verify_ecosystem_marketplace.py --json" in bash_script
    assert powershell_script.index("verify_ecosystem_marketplace.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_ecosystem_marketplace.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_industry_proof_surface_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_industry_proof_surface.py --json" in powershell_script
    assert "verify_industry_proof_surface.py --json" in bash_script
    assert powershell_script.index("verify_industry_proof_surface.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_industry_proof_surface.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_runtime_stability_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_runtime_stability.py --json" in powershell_script
    assert "verify_runtime_stability.py --json" in bash_script
    assert powershell_script.index("verify_runtime_stability.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_runtime_stability.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_result_contracts_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_result_contracts.py --json" in powershell_script
    assert "verify_result_contracts.py --json" in bash_script
    assert powershell_script.index("verify_result_contracts.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_result_contracts.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_ecosystem_readiness_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_ecosystem_readiness.py --json" in powershell_script
    assert "verify_ecosystem_readiness.py --json" in bash_script
    assert powershell_script.index("verify_ecosystem_readiness.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_ecosystem_readiness.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_antibot_replay_validation_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "validate_antibot_replays.py --json" in powershell_script
    assert "validate_antibot_replays.py --json" in bash_script
    assert powershell_script.index("validate_antibot_replays.py --json") < powershell_script.index("git add .")
    assert bash_script.index("validate_antibot_replays.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_workflow_replay_validation_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "validate_workflow_replays.py --json" in powershell_script
    assert "validate_workflow_replays.py --json" in bash_script
    assert powershell_script.index("validate_workflow_replays.py --json") < powershell_script.index("git add .")
    assert bash_script.index("validate_workflow_replays.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_javaspider_captcha_summary_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_javaspider_captcha_summary.py --json" in powershell_script
    assert "verify_javaspider_captcha_summary.py --json" in bash_script
    assert powershell_script.index("verify_javaspider_captcha_summary.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_javaspider_captcha_summary.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_pyspider_concurrency_summary_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_pyspider_concurrency_summary.py --json" in powershell_script
    assert "verify_pyspider_concurrency_summary.py --json" in bash_script
    assert powershell_script.index("verify_pyspider_concurrency_summary.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_pyspider_concurrency_summary.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_rust_browser_summary_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_rust_browser_summary.py --json" in powershell_script
    assert "verify_rust_browser_summary.py --json" in bash_script
    assert powershell_script.index("verify_rust_browser_summary.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_rust_browser_summary.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_replay_dashboard_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_replay_dashboard.py --json" in powershell_script
    assert "verify_replay_dashboard.py --json" in bash_script
    assert powershell_script.index("verify_replay_dashboard.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_replay_dashboard.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_replay_trends_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_replay_trends.py --json" in powershell_script
    assert "verify_replay_trends.py --json" in bash_script
    assert powershell_script.index("verify_replay_trends.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_replay_trends.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_gospider_distributed_summary_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_gospider_distributed_summary.py --json" in powershell_script
    assert "verify_gospider_distributed_summary.py --json" in bash_script
    assert powershell_script.index("verify_gospider_distributed_summary.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_gospider_distributed_summary.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_rust_preflight_summary_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_rust_preflight_summary.py --json" in powershell_script
    assert "verify_rust_preflight_summary.py --json" in bash_script
    assert powershell_script.index("verify_rust_preflight_summary.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_rust_preflight_summary.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_rust_distributed_summary_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_rust_distributed_summary.py --json" in powershell_script
    assert "verify_rust_distributed_summary.py --json" in bash_script
    assert powershell_script.index("verify_rust_distributed_summary.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_rust_distributed_summary.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_framework_scorecard_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "generate_framework_scorecard.py --json" in powershell_script
    assert "generate_framework_scorecard.py --json" in bash_script
    assert powershell_script.index("generate_framework_scorecard.py --json") < powershell_script.index("git add .")
    assert bash_script.index("generate_framework_scorecard.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_quality_policy_governance_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_quality_policy_governance.py --json" in powershell_script
    assert "verify_quality_policy_governance.py --json" in bash_script
    assert powershell_script.index("verify_quality_policy_governance.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_quality_policy_governance.py --json") < bash_script.index("git add .")


def test_publish_scripts_run_framework_standards_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_framework_standards.py --json" in powershell_script
    assert "verify_framework_standards.py --json" in bash_script
    assert powershell_script.index("verify_framework_standards.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_framework_standards.py --json") < bash_script.index("git add .")
    assert "framework-standards.md" in powershell_script
    assert "framework-standards.md" in bash_script


def test_publish_scripts_run_quality_thresholds_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_quality_thresholds.py --json" in powershell_script
    assert "verify_quality_thresholds.py --json" in bash_script
    assert "--profile strict" in powershell_script
    assert "--profile strict" in bash_script
    assert powershell_script.index("verify_quality_thresholds.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_quality_thresholds.py --json") < bash_script.index("git add .")
    assert "quality-thresholds.md" in powershell_script
    assert "quality-thresholds.md" in bash_script


def test_publish_scripts_run_quality_events_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "verify_quality_events.py --json" in powershell_script
    assert "verify_quality_events.py --json" in bash_script
    assert powershell_script.index("verify_quality_events.py --json") < powershell_script.index("git add .")
    assert bash_script.index("verify_quality_events.py --json") < bash_script.index("git add .")
    assert "quality-events.ndjson" in powershell_script
    assert "quality-events.compact.json" in bash_script


def test_publish_scripts_run_baseline_bundle_before_git_add():
    powershell_script = (ROOT / "publish-to-github.ps1").read_text(encoding="utf-8")
    bash_script = (ROOT / "publish-to-github.sh").read_text(encoding="utf-8")

    assert "generate_baseline_bundle.py --json" in powershell_script
    assert "generate_baseline_bundle.py --json" in bash_script
    assert powershell_script.index("generate_baseline_bundle.py --json") < powershell_script.index("git add .")
    assert bash_script.index("generate_baseline_bundle.py --json") < bash_script.index("git add .")
    assert "baseline-bundle.md" in powershell_script
    assert "baseline-bundle.md" in bash_script


def test_four_framework_workflow_has_aggregate_verify_job():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "verify-env:" in workflow
    assert "name: Verify Aggregate Environment" in workflow
    assert "python verify_env.py --json" in workflow
    assert "python verify_ultimate_contract.py --json" in workflow
    assert "python verify_ultimate_trends.py --json" in workflow
    assert "python verify_ultimate_events.py --json" in workflow
    assert "ffmpeg" in workflow.lower()


def test_framework_contract_workflow_exists():
    workflow = (ROOT / ".github" / "workflows" / "framework-contract.yml").read_text(encoding="utf-8")

    assert "Verify Shared CLI Contract" in workflow
    assert "gospider config init" in workflow
    assert "python validate_contract_configs.py --json" in workflow
    assert "python verify_ultimate_contract.py --json" in workflow
    assert "gospider doctor" in workflow
    assert "run-framework.sh config init" in workflow
    assert "cargo run -- config init" in workflow
    assert "pyspider config init" in workflow


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


def test_four_framework_workflow_runs_runtime_readiness_verify():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_runtime_readiness.py --json" in workflow


def test_four_framework_workflow_runs_runtime_core_capabilities_verify():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_runtime_core_capabilities.py --json" in workflow


def test_four_framework_workflow_runs_operator_products_verify():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_operator_products.py --json" in workflow


def test_four_framework_workflow_runs_runtime_stability_verify():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_runtime_stability.py --json" in workflow


def test_four_framework_workflow_runs_result_contracts_verify():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_result_contracts.py --json" in workflow


def test_four_framework_workflow_runs_ecosystem_readiness_verify():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_ecosystem_readiness.py --json" in workflow


def test_four_framework_workflow_runs_antibot_replay_validation():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python validate_antibot_replays.py --json" in workflow


def test_four_framework_workflow_runs_workflow_replay_validation():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python validate_workflow_replays.py --json" in workflow


def test_four_framework_workflow_runs_javaspider_captcha_summary():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_javaspider_captcha_summary.py --json" in workflow


def test_four_framework_workflow_runs_captcha_live_readiness_summary():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_captcha_live_readiness.py --json" in workflow


def test_four_framework_workflow_runs_pyspider_concurrency_summary():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_pyspider_concurrency_summary.py --json" in workflow


def test_four_framework_workflow_runs_rust_browser_summary():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_rust_browser_summary.py --json" in workflow


def test_four_framework_workflow_runs_replay_dashboard():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_replay_dashboard.py --json" in workflow


def test_four_framework_workflow_runs_replay_trends():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_replay_trends.py --json" in workflow


def test_four_framework_workflow_runs_gospider_distributed_summary():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_gospider_distributed_summary.py --json" in workflow


def test_four_framework_workflow_runs_rust_preflight_summary():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_rust_preflight_summary.py --json" in workflow


def test_four_framework_workflow_runs_rust_distributed_summary():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_rust_distributed_summary.py --json" in workflow


def test_four_framework_workflow_runs_framework_scorecard():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python generate_framework_scorecard.py --json" in workflow


def test_four_framework_workflow_runs_framework_deep_surfaces_report():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python generate_framework_deep_surfaces_report.py --json" in workflow


def test_four_framework_workflow_runs_framework_standards():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_framework_standards.py --json" in workflow
    assert "framework-standards.md" in workflow


def test_four_framework_workflow_runs_quality_policy_governance():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_quality_policy_governance.py --json" in workflow


def test_four_framework_workflow_runs_quality_thresholds():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_quality_thresholds.py --json" in workflow
    assert "--profile default" in workflow
    assert "quality-thresholds.md" in workflow


def test_four_framework_workflow_runs_quality_events():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_quality_events.py --json" in workflow
    assert "quality-events.ndjson" in workflow
    assert "quality-events.compact.json" in workflow


def test_four_framework_workflow_runs_baseline_bundle():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python generate_baseline_bundle.py --json" in workflow
    assert "baseline-bundle.md" in workflow


def test_four_framework_workflow_runs_root_version_check():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python verify_version.py --json" in workflow


def test_four_framework_workflow_runs_contract_config_validation():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "python validate_contract_configs.py --json" in workflow
    assert "contract-config-validation.json" in workflow


def test_four_framework_workflow_always_uploads_aggregate_artifacts():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "name: Upload aggregate verify artifacts" in workflow
    assert "if: always()" in workflow
    assert "artifacts/verify-env.json" in workflow
    assert "artifacts/smoke-test.json" in workflow
    assert "artifacts/runtime-readiness.json" in workflow
    assert "artifacts/runtime-stability.json" in workflow
    assert "artifacts/runtime-stability.md" in workflow
    assert "artifacts/result-contracts.json" in workflow
    assert "artifacts/result-contracts.md" in workflow
    assert "artifacts/runtime-core-capabilities.json" in workflow
    assert "artifacts/operator-products.json" in workflow
    assert "artifacts/operator-products.md" in workflow
    assert "artifacts/ecosystem-readiness.json" in workflow
    assert "artifacts/ecosystem-readiness.md" in workflow
    assert "artifacts/captcha-live-readiness.json" in workflow
    assert "artifacts/captcha-live-readiness.md" in workflow
    assert "artifacts/antibot-replays.json" in workflow
    assert "artifacts/workflow-replays.json" in workflow
    assert "artifacts/replay-dashboard.json" in workflow
    assert "artifacts/replay-trends.json" in workflow
    assert "artifacts/rust-distributed-summary.json" in workflow
    assert "artifacts/rust-preflight-summary.json" in workflow
    assert "artifacts/framework-scorecard.json" in workflow
    assert "artifacts/framework-scorecard.md" in workflow
    assert "artifacts/framework-deep-surfaces.json" in workflow
    assert "artifacts/framework-deep-surfaces.md" in workflow
    assert "artifacts/quality-thresholds.json" in workflow
    assert "artifacts/quality-thresholds.md" in workflow
    assert "artifacts/quality-events.json" in workflow
    assert "artifacts/quality-events.ndjson" in workflow
    assert "artifacts/quality-events.compact.json" in workflow
    assert "artifacts/quality-policy-governance.json" in workflow
    assert "artifacts/root-tests.log" in workflow


def test_four_framework_workflow_enforces_rust_fmt_check():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "cargo fmt --check" in workflow


def test_four_framework_workflow_runs_rust_distributed_feature_gate():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert "cargo test --features distributed --test distributed_scorecard" in workflow
    assert "cargo test --test distributed_behavior_scorecard" in workflow


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
    assert "os-support:" in workflow
    assert "needs:" in workflow
    assert "- os-support" in workflow
    assert "vars.SUPERSPIDER_REPOSITORY" in workflow
    assert "format('{0}/superspider', github.repository_owner)" in workflow
    assert "pattern: os-support-*" in workflow
    assert "artifacts/operating-system-support-${{ matrix.os }}.json" in workflow
    assert "python -m pytest tests -p no:cacheprovider" in workflow
    assert "python validate_contract_configs.py --json" in workflow
    assert "python verify_version.py --json" in workflow
    assert "python verify_env.py --json" in workflow
    assert "python smoke_test.py --json" in workflow
    assert "python verify_runtime_readiness.py --json" in workflow
    assert "python verify_runtime_stability.py --json" in workflow
    assert "python verify_result_contracts.py --json" in workflow
    assert "python verify_runtime_core_capabilities.py --json" in workflow
    assert "python verify_superspider_control_plane_benchmark.py --json" in workflow
    assert "python verify_superspider_control_plane_install_smoke.py --json" in workflow
    assert "python verify_superspider_control_plane_package.py --json" in workflow
    assert "python verify_superspider_control_plane_postgres_backend.py --json" in workflow
    assert "python verify_superspider_control_plane_release.py --json" in workflow
    assert "python verify_operator_products.py --json" in workflow
    assert "python verify_operating_system_support.py --json" in workflow
    assert "python verify_ecosystem_readiness.py --json" in workflow
    assert "python verify_captcha_live_readiness.py --json" in workflow
    assert "python validate_antibot_replays.py --json" in workflow
    assert "python validate_workflow_replays.py --json" in workflow
    assert "python verify_replay_dashboard.py --json" in workflow
    assert "python verify_replay_trends.py --json" in workflow
    assert "python verify_rust_distributed_summary.py --json" in workflow
    assert "python verify_rust_preflight_summary.py --json" in workflow
    assert "python generate_framework_scorecard.py --json" in workflow
    assert "python generate_framework_deep_surfaces_report.py --json" in workflow
    assert "python verify_quality_thresholds.py --json" in workflow
    assert "python verify_quality_events.py --json" in workflow
    assert "quality-events.ndjson" in workflow
    assert "quality-events.compact.json" in workflow
    assert "python verify_quality_policy_governance.py --json" in workflow
    assert "--profile strict" in workflow
    assert workflow.count("python verify_superspider_control_plane_postgres_backend.py --json") == 1


def test_release_workflow_stages_and_uploads_superspider_dist_artifacts():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "name: Stage superspider control-plane dist artifacts" in workflow
    assert "SUPERSPIDER_ROOT: ${{ github.workspace }}/superspider" in workflow
    assert 'cp -R "${SUPERSPIDER_ROOT}/dist/." artifacts/superspider-control-plane-dist/' in workflow
    assert "artifacts/superspider-control-plane-dist.index.txt" in workflow
    assert "artifacts/superspider-control-plane-dist/SHA256SUMS.txt" in workflow
    assert "artifacts/superspider-control-plane-dist/dist-manifest.json" in workflow
    assert "name: Upload superspider control-plane dist" in workflow
    assert "name: superspider-control-plane-dist" in workflow


def test_release_workflow_installs_pyspider_before_shared_cli_contract():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert workflow.index("name: Install PySpider dependencies") < workflow.index("name: Verify shared CLI contract")


def test_four_framework_verify_installs_pyspider_before_shared_cli_contract():
    workflow = (ROOT / ".github" / "workflows" / "four-framework-verify.yml").read_text(encoding="utf-8")

    assert workflow.index("name: Install PySpider dependencies") < workflow.index("name: Verify shared CLI contract")


def test_framework_os_matrix_prepares_artifacts_and_installs_editable_pyspider():
    workflow = (ROOT / ".github" / "workflows" / "framework-os-matrix.yml").read_text(encoding="utf-8")

    assert 'pip install -e "./pyspider[dev]"' in workflow
    assert "name: Prepare artifact directory" in workflow
    assert "mkdir -p artifacts" in workflow
    assert "artifacts/operating-system-support-${{ matrix.os }}.json" in workflow


def test_release_workflow_only_creates_release_for_tags():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "if: startsWith(github.ref, 'refs/tags/v')" in workflow
    assert "gh release create" in workflow
    assert "contents: write" in workflow


def test_release_workflow_enforces_rust_quality_gates():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "cargo clippy --all-targets -- -D warnings" in workflow
    assert "cargo fmt --check" in workflow
    assert "cargo test --features distributed --test distributed_scorecard" in workflow
    assert "cargo test --test distributed_behavior_scorecard" in workflow


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
