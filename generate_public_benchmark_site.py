from __future__ import annotations

import argparse
import json
from pathlib import Path

import generate_framework_deep_surfaces_report
import generate_framework_scorecard
import verify_benchmark_sla
import verify_benchmark_trends
import verify_blackbox_e2e
import verify_cache_incremental_evidence
import verify_captcha_live_readiness
import verify_ecosystem_readiness
import verify_ecosystem_marketplace
import verify_industry_proof_surface
import verify_kernel_homogeneity
import verify_observability_evidence
import verify_operator_products
import verify_result_contracts
import verify_runtime_stability
import verify_runtime_readiness
import verify_superspider_control_plane
import verify_superspider_control_plane_benchmark
import verify_superspider_control_plane_package
import verify_superspider_control_plane_release


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _runtime_readiness_needs_refresh(payload: dict) -> bool:
    frameworks = payload.get("frameworks")
    if not isinstance(frameworks, list):
        return True
    for item in frameworks:
        metrics = item.get("metrics") if isinstance(item, dict) else None
        if not isinstance(metrics, dict) or "control_plane_rate" not in metrics:
            return True
    return False


def collect_site_data(root: Path, *, refresh: bool = False) -> dict:
    artifacts = root / "artifacts"
    runtime_readiness_path = artifacts / "runtime-readiness.json"
    framework_scorecard_path = artifacts / "framework-scorecard.json"
    framework_deep_surfaces_path = artifacts / "framework-deep-surfaces.json"
    benchmark_sla_path = artifacts / "benchmark-sla.json"
    blackbox_e2e_path = artifacts / "blackbox-e2e.json"
    benchmark_trends_path = artifacts / "benchmark-trends.json"
    runtime_stability_path = artifacts / "runtime-stability.json"
    result_contracts_path = artifacts / "result-contracts.json"
    superspider_control_plane_benchmark_path = artifacts / "superspider-control-plane-benchmark.json"
    superspider_control_plane_path = artifacts / "superspider-control-plane.json"
    superspider_control_plane_package_path = artifacts / "superspider-control-plane-package.json"
    superspider_control_plane_release_path = artifacts / "superspider-control-plane-release.json"
    operator_products_path = artifacts / "operator-products.json"
    kernel_homogeneity_path = artifacts / "kernel-homogeneity.json"
    observability_evidence_path = artifacts / "observability-evidence.json"
    cache_incremental_evidence_path = artifacts / "cache-incremental-evidence.json"
    ecosystem_marketplace_path = artifacts / "ecosystem-marketplace.json"
    ecosystem_readiness_path = artifacts / "ecosystem-readiness.json"
    captcha_live_readiness_path = artifacts / "captcha-live-readiness.json"
    industry_proof_surface_path = artifacts / "industry-proof-surface.json"

    if refresh or (not runtime_readiness_path.exists()) or _runtime_readiness_needs_refresh(_read_json(runtime_readiness_path)):
        runtime_readiness_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_readiness_path.write_text(
            json.dumps(
                verify_runtime_readiness.collect_runtime_readiness_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not framework_scorecard_path.exists():
        framework_scorecard_path.parent.mkdir(parents=True, exist_ok=True)
        framework_scorecard_path.write_text(
            json.dumps(
                generate_framework_scorecard.collect_framework_scorecard(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not framework_deep_surfaces_path.exists():
        framework_deep_surfaces_path.parent.mkdir(parents=True, exist_ok=True)
        framework_deep_surfaces_path.write_text(
            json.dumps(
                generate_framework_deep_surfaces_report.collect_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not benchmark_sla_path.exists():
        benchmark_sla_path.parent.mkdir(parents=True, exist_ok=True)
        benchmark_sla_path.write_text(
            json.dumps(
                verify_benchmark_sla.collect_benchmark_sla_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not blackbox_e2e_path.exists():
        blackbox_e2e_path.parent.mkdir(parents=True, exist_ok=True)
        blackbox_e2e_path.write_text(
            json.dumps(
                verify_blackbox_e2e.collect_blackbox_e2e_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not benchmark_trends_path.exists():
        benchmark_trends_path.parent.mkdir(parents=True, exist_ok=True)
        benchmark_trends_path.write_text(
            json.dumps(
                verify_benchmark_trends.collect_benchmark_trend_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not runtime_stability_path.exists():
        runtime_stability_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_stability_path.write_text(
            json.dumps(
                verify_runtime_stability.collect_runtime_stability_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not result_contracts_path.exists():
        result_contracts_path.parent.mkdir(parents=True, exist_ok=True)
        result_contracts_path.write_text(
            json.dumps(
                verify_result_contracts.collect_result_contracts_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not superspider_control_plane_benchmark_path.exists():
        superspider_control_plane_benchmark_path.parent.mkdir(parents=True, exist_ok=True)
        superspider_control_plane_benchmark_path.write_text(
            json.dumps(
                verify_superspider_control_plane_benchmark.collect_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not superspider_control_plane_path.exists():
        superspider_control_plane_path.parent.mkdir(parents=True, exist_ok=True)
        superspider_control_plane_path.write_text(
            json.dumps(
                verify_superspider_control_plane.collect_superspider_control_plane_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not superspider_control_plane_package_path.exists():
        superspider_control_plane_package_path.parent.mkdir(parents=True, exist_ok=True)
        superspider_control_plane_package_path.write_text(
            json.dumps(
                verify_superspider_control_plane_package.collect_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not superspider_control_plane_release_path.exists():
        superspider_control_plane_release_path.parent.mkdir(parents=True, exist_ok=True)
        superspider_control_plane_release_path.write_text(
            json.dumps(
                verify_superspider_control_plane_release.collect_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not operator_products_path.exists():
        operator_products_path.parent.mkdir(parents=True, exist_ok=True)
        operator_products_path.write_text(
            json.dumps(
                verify_operator_products.collect_operator_products_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not kernel_homogeneity_path.exists():
        kernel_homogeneity_path.parent.mkdir(parents=True, exist_ok=True)
        kernel_homogeneity_path.write_text(
            json.dumps(
                verify_kernel_homogeneity.collect_kernel_homogeneity_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not observability_evidence_path.exists():
        observability_evidence_path.parent.mkdir(parents=True, exist_ok=True)
        observability_evidence_path.write_text(
            json.dumps(
                verify_observability_evidence.collect_observability_evidence_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not cache_incremental_evidence_path.exists():
        cache_incremental_evidence_path.parent.mkdir(parents=True, exist_ok=True)
        cache_incremental_evidence_path.write_text(
            json.dumps(
                verify_cache_incremental_evidence.collect_cache_incremental_evidence_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not ecosystem_marketplace_path.exists():
        ecosystem_marketplace_path.parent.mkdir(parents=True, exist_ok=True)
        ecosystem_marketplace_path.write_text(
            json.dumps(
                verify_ecosystem_marketplace.collect_ecosystem_marketplace_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not ecosystem_readiness_path.exists():
        ecosystem_readiness_path.parent.mkdir(parents=True, exist_ok=True)
        ecosystem_readiness_path.write_text(
            json.dumps(
                verify_ecosystem_readiness.collect_ecosystem_readiness_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not industry_proof_surface_path.exists():
        industry_proof_surface_path.parent.mkdir(parents=True, exist_ok=True)
        industry_proof_surface_path.write_text(
            json.dumps(
                verify_industry_proof_surface.collect_industry_proof_surface_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if refresh or not captcha_live_readiness_path.exists():
        captcha_live_readiness_path.parent.mkdir(parents=True, exist_ok=True)
        captcha_live_readiness_path.write_text(
            json.dumps(
                verify_captcha_live_readiness.collect_captcha_live_readiness_report(root),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    return {
        "runtime_readiness": _read_json(runtime_readiness_path),
        "framework_scorecard": _read_json(framework_scorecard_path),
        "framework_deep_surfaces": _read_json(framework_deep_surfaces_path),
        "benchmark_sla": _read_json(benchmark_sla_path),
        "blackbox_e2e": _read_json(blackbox_e2e_path),
        "benchmark_trends": _read_json(benchmark_trends_path),
        "runtime_stability": _read_json(runtime_stability_path),
        "result_contracts": _read_json(result_contracts_path),
        "superspider_control_plane_benchmark": _read_json(superspider_control_plane_benchmark_path),
        "superspider_control_plane": _read_json(superspider_control_plane_path),
        "superspider_control_plane_package": _read_json(superspider_control_plane_package_path),
        "superspider_control_plane_release": _read_json(superspider_control_plane_release_path),
        "operator_products": _read_json(operator_products_path),
        "kernel_homogeneity": _read_json(kernel_homogeneity_path),
        "observability_evidence": _read_json(observability_evidence_path),
        "cache_incremental_evidence": _read_json(cache_incremental_evidence_path),
        "ecosystem_marketplace": _read_json(ecosystem_marketplace_path),
        "ecosystem_readiness": _read_json(ecosystem_readiness_path),
        "captcha_live_readiness": _read_json(captcha_live_readiness_path),
        "industry_proof_surface": _read_json(industry_proof_surface_path),
    }


def _escape(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def render_site(payload: dict) -> str:
    readiness_rows = []
    for item in payload["runtime_readiness"]["frameworks"]:
        metrics = item["metrics"]
        control_plane_rate = float(metrics.get("control_plane_rate", 0.0))
        workflow_replay_rate = float(metrics.get("workflow_replay_rate", 0.0))
        success_rate = float(metrics.get("success_rate", 0.0))
        readiness_rows.append(
            f"<tr><td>{_escape(item['name'])}</td><td>{_escape(item['runtime'])}</td>"
            f"<td>{_escape(item['summary'])}</td><td>{success_rate:.2f}</td>"
            f"<td>{workflow_replay_rate:.2f}</td><td>{control_plane_rate:.2f}</td></tr>"
        )

    benchmark_rows = []
    for item in payload["benchmark_sla"]["frameworks"]:
        sla = item["sla"]["success_job_ms"]
        benchmark_rows.append(
            f"<tr><td>{_escape(item['name'])}</td><td>{_escape(item['runtime'])}</td>"
            f"<td>{_escape(item['summary'])}</td><td>{sla['measured']}ms</td>"
            f"<td>{sla['threshold']}ms</td><td>{'pass' if sla['passed'] else 'fail'}</td></tr>"
        )

    blackbox_rows = []
    for item in payload["blackbox_e2e"]["frameworks"]:
        blackbox_rows.append(
            f"<tr><td>{_escape(item['name'])}</td><td>{_escape(item['runtime'])}</td><td>{_escape(item['summary'])}</td></tr>"
        )

    stability_rows = []
    for item in payload["runtime_stability"]["frameworks"]:
        metrics = item["metrics"]
        distributed = metrics.get("distributed_longevity_rate")
        distributed_text = "n/a" if distributed is None else f"{float(distributed):.2f}"
        stability_rows.append(
            f"<tr><td>{_escape(item['name'])}</td><td>{_escape(item['runtime'])}</td>"
            f"<td>{_escape(item['summary'])}</td><td>{float(metrics.get('frontier_stress_rate', 0.0)):.2f}</td>"
            f"<td>{float(metrics.get('recovery_rate', 0.0)):.2f}</td><td>{distributed_text}</td>"
            f"<td>{'yes' if metrics.get('soak_ready') else 'no'}</td></tr>"
        )

    ecosystem_rows = []
    for item in payload["ecosystem_readiness"]["checks"]:
        ecosystem_rows.append(
            f"<tr><td>{_escape(item['name'])}</td><td>{_escape(item['status'])}</td><td>{_escape(item['details'])}</td></tr>"
        )

    deep_surface_rows = []
    for name, item in payload["framework_deep_surfaces"]["frameworks"].items():
        live = item.get("live_surfaces", [])
        live_text = ", ".join(
            f"{entry.get('name')}={entry.get('summary')}"
            for entry in live
        ) or "none"
        modules = item.get("modules", [])
        entrypoints = item.get("extended_entrypoints", [])
        deep_surface_rows.append(
            f"<tr><td>{_escape(name)}</td><td>{_escape(item.get('runtime'))}</td>"
            f"<td>{_escape(item.get('capability_status', 'unknown'))}</td>"
            f"<td>{_escape(', '.join(entrypoints[:6]))}</td>"
            f"<td>{_escape(', '.join(modules[:6]))}</td>"
            f"<td>{_escape(live_text)}</td></tr>"
        )

    kernel_rows = []
    for item in payload["kernel_homogeneity"]["checks"]:
        kernel_rows.append(
            f"<tr><td>{_escape(item['name'])}</td><td>{_escape(item['status'])}</td><td>{_escape(item['details'])}</td></tr>"
        )

    observability_rows = []
    for item in payload["observability_evidence"]["checks"]:
        observability_rows.append(
            f"<tr><td>{_escape(item['name'])}</td><td>{_escape(item['status'])}</td><td>{_escape(item['details'])}</td></tr>"
        )

    cache_rows = []
    for item in payload["cache_incremental_evidence"]["checks"]:
        cache_rows.append(
            f"<tr><td>{_escape(item['name'])}</td><td>{_escape(item['status'])}</td><td>{_escape(item['details'])}</td></tr>"
        )

    marketplace_rows = []
    for item in payload["ecosystem_marketplace"]["checks"]:
        marketplace_rows.append(
            f"<tr><td>{_escape(item['name'])}</td><td>{_escape(item['status'])}</td><td>{_escape(item['details'])}</td></tr>"
        )

    industry_proof_rows = []
    for item in payload["industry_proof_surface"]["checks"]:
        industry_proof_rows.append(
            f"<tr><td>{_escape(item['name'])}</td><td>{_escape(item['status'])}</td><td>{_escape(item['details'])}</td></tr>"
        )

    captcha_live_rows = []
    for name, item in payload["captcha_live_readiness"]["frameworks"].items():
        captcha_live_rows.append(
            f"<tr><td>{_escape(name)}</td><td>{_escape(item['runtime'])}</td><td>{_escape(item['summary'])}</td><td>{_escape(item['summary_text'])}</td></tr>"
        )

    result_contract_rows = []
    for item in payload["result_contracts"]["checks"]:
        result_contract_rows.append(
            f"<tr><td>{_escape(item['name'])}</td><td>{_escape(item['status'])}</td><td>{_escape(item['details'])}</td></tr>"
        )

    superspider_benchmark_rows = []
    for item in payload["superspider_control_plane_benchmark"]["checks"]:
        superspider_benchmark_rows.append(
            f"<tr><td>{_escape(item['name'])}</td><td>{_escape(item['status'])}</td><td>{_escape(item['details'])}</td></tr>"
        )

    superspider_release_rows = []
    for section_name in ("superspider_control_plane", "superspider_control_plane_package", "superspider_control_plane_release"):
        section = payload[section_name]
        label = section_name.replace("_", "-")
        superspider_release_rows.append(
            f"<tr><td>{_escape(label)}</td><td>{_escape(section['summary'])}</td><td>{_escape(section['summary_text'])}</td></tr>"
        )

    operator_rows = []
    for item in payload["operator_products"]["checks"]:
        operator_rows.append(
            f"<tr><td>{_escape(item['name'])}</td><td>{_escape(item['status'])}</td><td>{_escape(item['details'])}</td></tr>"
        )

    trend_rows = []
    for name, item in payload["benchmark_trends"]["benchmark_trends"].items():
        current = item["current"]
        trend_rows.append(
            f"<tr><td>{_escape(name)}</td><td>{_escape(item['runtime'])}</td>"
            f"<td>{current['measured']}ms / {current['threshold']}ms</td>"
            f"<td>{_escape(item['delta_ms'])}</td><td>{_escape(item['summary_changed'])}</td></tr>"
        )

    readiness_trend_rows = []
    for name, item in payload["benchmark_trends"].get("readiness_trends", {}).items():
        current = item["current"]
        previous = item["previous"]
        readiness_trend_rows.append(
            f"<tr><td>{_escape(name)}</td><td>{_escape(item['runtime'])}</td>"
            f"<td>{_escape(current.get('summary'))}</td><td>{_escape(previous.get('summary'))}</td>"
            f"<td>{_escape(current.get('control_plane_rate'))}</td><td>{_escape(item['delta'].get('control_plane_rate'))}</td>"
            f"<td>{_escape(item.get('summary_changed'))}</td></tr>"
        )
    alert_rows = []
    for alert in payload["benchmark_trends"].get("alerts", []):
        severity = str(alert.get("severity", "warning"))
        tag_class = "fail" if severity == "failed" else "warn"
        alert_rows.append(
            f"<tr><td>{_escape(alert.get('framework'))}</td><td>{_escape(alert.get('source'))}</td>"
            f"<td><span class=\"tag {tag_class}\">{_escape(severity)}</span></td><td>{_escape(alert.get('details'))}</td></tr>"
        )
    if not alert_rows:
        alert_rows.append("<tr><td colspan=\"4\">No active benchmark or readiness regressions.</td></tr>")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Spider Public Benchmarks</title>
  <style>
    :root {{
      --bg: #07111f;
      --panel: rgba(15, 23, 42, 0.86);
      --line: rgba(148, 163, 184, 0.22);
      --text: #e5eef7;
      --muted: #9fb2c8;
      --good: #34d399;
      --bad: #fb7185;
      --accent: #7dd3fc;
      --accent-strong: #22d3ee;
    }}
    body {{ margin: 0; font-family: "Segoe UI Variable", "Segoe UI", sans-serif; background:
      radial-gradient(circle at top, rgba(34, 211, 238, 0.14), transparent 28%),
      linear-gradient(180deg, #020617, #0f172a 56%, #111827); color: var(--text); }}
    .wrap {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px 64px; }}
    h1 {{ margin: 0 0 8px; font-size: 40px; letter-spacing: -0.03em; }}
    h2 {{ letter-spacing: -0.02em; }}
    p {{ color: var(--muted); }}
    .hero {{ display: grid; gap: 16px; align-items: end; }}
    .eyebrow {{ color: var(--accent); text-transform: uppercase; letter-spacing: .16em; font-size: 12px; font-weight: 700; }}
    .lede {{ max-width: 760px; font-size: 17px; line-height: 1.6; }}
    .signal {{ display: inline-flex; align-items: center; gap: 8px; border: 1px solid var(--line); border-radius: 999px; padding: 8px 12px; background: rgba(15, 23, 42, 0.72); color: var(--muted); font-size: 14px; }}
    .signal strong {{ color: var(--text); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 28px 0; }}
    .card {{ background: var(--panel); backdrop-filter: blur(8px); border: 1px solid var(--line); border-radius: 18px; padding: 18px; box-shadow: 0 18px 40px rgba(2, 6, 23, .18); }}
    .card h2 {{ margin: 0 0 8px; font-size: 14px; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }}
    .big {{ font-size: 34px; font-weight: 700; color: var(--accent-strong); }}
    section {{ margin-top: 28px; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--line); border-radius: 18px; overflow: hidden; }}
    th, td {{ padding: 12px 14px; border-bottom: 1px solid var(--line); text-align: left; }}
    th {{ color: var(--muted); font-weight: 600; }}
    tr:last-child td {{ border-bottom: none; }}
    .note {{ margin-top: 12px; color: var(--muted); font-size: 14px; }}
    .tag {{ display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 9px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }}
    .tag.warn {{ background: rgba(245, 158, 11, 0.16); color: #fbbf24; }}
    .tag.fail {{ background: rgba(244, 63, 94, 0.18); color: #fda4af; }}
    .footer {{ margin-top: 28px; color: var(--muted); font-size: 14px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div>
        <div class="eyebrow">Public Evidence Surface</div>
        <h1>Spider Public Benchmarks</h1>
        <p class="lede">Repository-generated evidence for runtime readiness, runtime stability, result contracts, operator products, kernel homogeneity, observability, cache/incremental maturity, ecosystem marketplace, industry proof surface, and trend history across the Java, Python, Go, and Rust runtimes.</p>
      </div>
      <div class="signal"><strong>Operator parity:</strong> shared control-plane lifecycle probes are now tracked as a first-class readiness metric.</div>
    </div>

    <div class="grid">
      <div class="card"><h2>Benchmark SLA</h2><div class="big">{_escape(payload['benchmark_sla']['summary'])}</div></div>
      <div class="card"><h2>Blackbox E2E</h2><div class="big">{_escape(payload['blackbox_e2e']['summary'])}</div></div>
      <div class="card"><h2>Runtime Readiness</h2><div class="big">{_escape(payload['runtime_readiness']['summary'])}</div></div>
      <div class="card"><h2>Deep Surfaces</h2><div class="big">{_escape(payload['framework_deep_surfaces']['summary'])}</div></div>
      <div class="card"><h2>Runtime Stability</h2><div class="big">{_escape(payload['runtime_stability']['summary'])}</div></div>
      <div class="card"><h2>Result Contracts</h2><div class="big">{_escape(payload['result_contracts']['summary'])}</div></div>
      <div class="card"><h2>SuperSpider CP Benchmark</h2><div class="big">{_escape(payload['superspider_control_plane_benchmark']['summary'])}</div></div>
      <div class="card"><h2>SuperSpider CP Release</h2><div class="big">{_escape(payload['superspider_control_plane_release']['summary'])}</div></div>
      <div class="card"><h2>Operator Products</h2><div class="big">{_escape(payload['operator_products']['summary'])}</div></div>
      <div class="card"><h2>Kernel</h2><div class="big">{_escape(payload['kernel_homogeneity']['summary'])}</div></div>
      <div class="card"><h2>Observability</h2><div class="big">{_escape(payload['observability_evidence']['summary'])}</div></div>
      <div class="card"><h2>Cache / Incremental</h2><div class="big">{_escape(payload['cache_incremental_evidence']['summary'])}</div></div>
      <div class="card"><h2>Marketplace</h2><div class="big">{_escape(payload['ecosystem_marketplace']['summary'])}</div></div>
      <div class="card"><h2>Ecosystem</h2><div class="big">{_escape(payload['ecosystem_readiness']['summary'])}</div></div>
      <div class="card"><h2>Captcha Live</h2><div class="big">{_escape(payload['captcha_live_readiness']['summary'])}</div></div>
      <div class="card"><h2>Industry Proof</h2><div class="big">{_escape(payload['industry_proof_surface']['summary'])}</div></div>
      <div class="card"><h2>Trend Report</h2><div class="big">{_escape(payload['benchmark_trends']['summary'])}</div></div>
      <div class="card"><h2>History Depth</h2><div class="big">{_escape(payload['benchmark_trends']['history_depth'])}</div></div>
      <div class="card"><h2>Active Alerts</h2><div class="big">{len(payload['benchmark_trends'].get('alerts', []))}</div></div>
    </div>

    <section>
      <h2>Runtime Readiness</h2>
      <p class="note">Success rate, workflow replay rate, and control-plane parity are shown together so release evidence reflects both runtime contracts and operator-facing task lifecycle behavior.</p>
      <table>
        <thead><tr><th>Framework</th><th>Runtime</th><th>Summary</th><th>Success Rate</th><th>Replay Rate</th><th>Control Plane</th></tr></thead>
        <tbody>{''.join(readiness_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Framework Deep Surfaces</h2>
      <p class="note">This section exposes the under-documented operator and module surfaces that are discovered from each runtime&apos;s machine-readable <code>capabilities</code> payload instead of relying on short README highlights alone.</p>
      <table>
        <thead><tr><th>Framework</th><th>Runtime</th><th>Capability Status</th><th>Extended Entrypoints</th><th>Representative Modules</th><th>Live Surfaces</th></tr></thead>
        <tbody>{''.join(deep_surface_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Benchmark SLA</h2>
      <table>
        <thead><tr><th>Framework</th><th>Runtime</th><th>Summary</th><th>Measured</th><th>Threshold</th><th>Gate</th></tr></thead>
        <tbody>{''.join(benchmark_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Blackbox E2E</h2>
      <table>
        <thead><tr><th>Framework</th><th>Runtime</th><th>Summary</th></tr></thead>
        <tbody>{''.join(blackbox_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Runtime Stability</h2>
      <p class="note">Long-running maturity evidence tracks frontier stress, recovery, distributed longevity, and soak-readiness so the public benchmark story is not limited to one-shot command success.</p>
      <table>
        <thead><tr><th>Framework</th><th>Runtime</th><th>Summary</th><th>Frontier Stress</th><th>Recovery</th><th>Distributed Longevity</th><th>Soak Ready</th></tr></thead>
        <tbody>{''.join(stability_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Result Contracts</h2>
      <p class="note">This surface proves that task results and graph artifacts are not only implemented ad hoc, but checked against shared graph/result/artifact contracts and runtime-local result behavior.</p>
      <table>
        <thead><tr><th>Check</th><th>Status</th><th>Details</th></tr></thead>
        <tbody>{''.join(result_contract_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>SuperSpider Control Plane Benchmark</h2>
      <p class="note">This surface tracks lightweight control-plane execution, latency, and dashboard proof so the suite-level control plane is measured alongside the runtime frameworks.</p>
      <table>
        <thead><tr><th>Check</th><th>Status</th><th>Details</th></tr></thead>
        <tbody>{''.join(superspider_benchmark_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>SuperSpider Control Plane Release</h2>
      <p class="note">This surface tracks compiler/router parity, package publication, and release/runtime exposure for the standalone control-plane product shell.</p>
      <table>
        <thead><tr><th>Check</th><th>Status</th><th>Details</th></tr></thead>
        <tbody>{''.join(superspider_release_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Operator Products</h2>
      <p class="note">This surface tracks whether the suite-level operator products are formally shipped and validated: JOBDIR, HTTP cache management, Playwright trace/HAR/mock/codegen tooling, autoscaling pool surfaces, and runtime console inspection.</p>
      <table>
        <thead><tr><th>Check</th><th>Status</th><th>Details</th></tr></thead>
        <tbody>{''.join(operator_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Kernel Homogeneity</h2>
      <p class="note">This surface verifies that all runtimes still advertise the same shared kernel vocabulary even while native implementations continue to evolve independently.</p>
      <table>
        <thead><tr><th>Check</th><th>Status</th><th>Details</th></tr></thead>
        <tbody>{''.join(kernel_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Observability Evidence</h2>
      <p class="note">This surface keeps metrics, trace, failure-classification, and monitoring surfaces visible as a release-grade requirement instead of an informal implementation detail.</p>
      <table>
        <thead><tr><th>Check</th><th>Status</th><th>Details</th></tr></thead>
        <tbody>{''.join(observability_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Cache And Incremental Evidence</h2>
      <p class="note">This surface tracks whether conditional requests, delta fetch, retention, and freshness are formalized beyond one-off cache tooling.</p>
      <table>
        <thead><tr><th>Check</th><th>Status</th><th>Details</th></tr></thead>
        <tbody>{''.join(cache_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Benchmark Trends</h2>
      <table>
        <thead><tr><th>Framework</th><th>Runtime</th><th>Current SLA</th><th>Delta (ms)</th><th>Summary Changed</th></tr></thead>
        <tbody>{''.join(trend_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Runtime Readiness Trends</h2>
      <p class="note">The readiness trend view highlights whether task lifecycle parity stays stable across historical snapshots, with a dedicated delta for <code>control_plane_rate</code>.</p>
      <table>
        <thead><tr><th>Framework</th><th>Runtime</th><th>Current Summary</th><th>Previous Summary</th><th>Control Plane</th><th>Delta</th><th>Summary Changed</th></tr></thead>
        <tbody>{''.join(readiness_trend_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Current Alerts</h2>
      <p class="note">Warnings and failed regressions from the current trend report are surfaced here so public readers can spot SLA or control-plane drift without opening the raw JSON artifacts.</p>
      <table>
        <thead><tr><th>Framework</th><th>Source</th><th>Severity</th><th>Details</th></tr></thead>
        <tbody>{''.join(alert_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Ecosystem Readiness</h2>
      <p class="note">These checks capture the non-runtime maturity layer: docs, starters, external examples, and integration catalog discipline.</p>
      <table>
        <thead><tr><th>Check</th><th>Status</th><th>Details</th></tr></thead>
        <tbody>{''.join(ecosystem_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Ecosystem Marketplace</h2>
      <p class="note">This surface tracks plugin catalog, marketplace/support entrypoints, and starter/governance discipline as the foundation for a real public extension ecosystem.</p>
      <table>
        <thead><tr><th>Check</th><th>Status</th><th>Details</th></tr></thead>
        <tbody>{''.join(marketplace_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Captcha Live Readiness</h2>
      <p class="note">Optional provider-backed captcha smoke coverage is aggregated here so operators can tell whether live challenge routes are configured, unsupported, skipped, or genuinely passing.</p>
      <table>
        <thead><tr><th>Framework</th><th>Runtime</th><th>Summary</th><th>Details</th></tr></thead>
        <tbody>{''.join(captcha_live_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Industry Proof Surface</h2>
      <p class="note">This surface distinguishes repository-owned proof from external proof claims by checking benchmark history depth, published artifacts, and validation story visibility.</p>
      <table>
        <thead><tr><th>Check</th><th>Status</th><th>Details</th></tr></thead>
        <tbody>{''.join(industry_proof_rows)}</tbody>
      </table>
    </section>

    <div class="footer">Generated from repository artifacts under <code>artifacts/</code>.</div>
  </div>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a static public benchmark page from repository artifacts")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="repository root path")
    parser.add_argument(
        "--output",
        default="web-ui/public-benchmarks/index.html",
        help="output HTML path relative to the current working directory",
    )
    parser.add_argument("--refresh", action="store_true", help="refresh repository artifacts before rendering the page")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_site(collect_site_data(root, refresh=args.refresh)), encoding="utf-8")
    print(output.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
