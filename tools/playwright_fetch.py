#!/usr/bin/env python3
"""
Shared Playwright fetch helper for the spider framework suite.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import json
import re
import struct
from copy import deepcopy
from pathlib import Path
import os
import time

from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch a rendered page with Playwright")
    parser.add_argument("--tooling-command", choices=["fetch", "trace", "mock", "codegen"], default="fetch")
    parser.add_argument("--url", help="Target URL")
    parser.add_argument("--screenshot", help="Optional screenshot output path")
    parser.add_argument("--html", help="Optional HTML output path")
    parser.add_argument("--trace-path", help="Optional Playwright trace output path")
    parser.add_argument("--har-path", help="Optional HAR output path")
    parser.add_argument("--har-replay", help="Optional HAR file to replay with route_from_har")
    parser.add_argument("--route-manifest", help="Optional JSON route mocking manifest")
    parser.add_argument("--codegen-out", help="Optional generated script output path")
    parser.add_argument("--codegen-language", choices=["python", "javascript"], default="python")
    parser.add_argument("--timeout-seconds", type=int, default=30, help="Navigation timeout in seconds")
    parser.add_argument("--user-agent", default="", help="Override user agent")
    parser.add_argument("--storage-state", default="", help="Optional Playwright storage state JSON path")
    parser.add_argument("--cookies-file", default="", help="Optional cookies JSON path")
    parser.add_argument("--save-storage-state", default="", help="Optional output path to save Playwright storage state")
    parser.add_argument("--save-cookies-file", default="", help="Optional output path to save cookies JSON")
    parser.add_argument("--auth-file", default="", help="Optional ai-auth.json path that can provide auth actions and session assets")
    parser.add_argument("--headless", action="store_true", default=True, help="Run headless")
    parser.add_argument("--job-file", help="Optional normalized browser JobSpec JSON file")
    return parser.parse_args()


def ensure_parent(path: str | None) -> None:
    if not path:
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def load_job_file(path: str | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_route_manifest(path: str | None) -> list[dict]:
    if not path:
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("routes") or []
    return [item for item in payload if isinstance(item, dict)]


def load_cookies_file(path: str | None) -> list[dict]:
    if not path:
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("cookies") or payload.get("items") or list(payload.values())
    return [item for item in payload if isinstance(item, dict)]


def load_auth_file(path: str | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def common_browser_paths() -> list[Path]:
    return [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    ]


def launch_browser(playwright, *, headless: bool):
    launch_attempts = [
        {"channel": "chrome", "headless": headless},
        {"channel": "msedge", "headless": headless},
    ]
    for candidate in common_browser_paths():
        if candidate.exists():
            launch_attempts.append({"executable_path": str(candidate), "headless": headless})
    launch_attempts.append({"headless": headless})

    last_error: Exception | None = None
    for options in launch_attempts:
        try:
            return playwright.chromium.launch(**options)
        except Exception as exc:  # pragma: no cover - depends on local browser availability
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError("no browser launch strategy succeeded")


def default_screenshot_path(job_spec: dict) -> str:
    output = job_spec.get("output") or {}
    prefix = output.get("artifact_prefix") or job_spec.get("name") or "playwright-job"
    directory = output.get("directory") or "artifacts/browser"
    return str(Path(directory) / f"{prefix}-capture.png")


def default_html_path(job_spec: dict) -> str:
    output = job_spec.get("output") or {}
    prefix = output.get("artifact_prefix") or job_spec.get("name") or "playwright-job"
    directory = output.get("directory") or "artifacts/browser"
    return str(Path(directory) / f"{prefix}-page.html")


def is_screenshot_path(path: str | None) -> bool:
    if not path:
        return False
    return Path(path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}


def is_html_path(path: str | None) -> bool:
    if not path:
        return False
    return Path(path).suffix.lower() in {".html", ".htm"}


def script_to_expression(script: str) -> str:
    normalized = script.strip()
    if normalized.startswith("return "):
        normalized = normalized[len("return ") :]
    if normalized.endswith(";"):
        normalized = normalized[:-1]
    return normalized or "null"


def generate_totp(secret: str, digits: int = 6, period: int = 30, now: float | None = None) -> str:
    normalized = "".join(secret.strip().split()).upper()
    if not normalized:
        return ""
    padding = "=" * ((8 - len(normalized) % 8) % 8)
    try:
        key = base64.b32decode(normalized + padding, casefold=True)
    except binascii.Error:
        return ""
    counter = int((now if now is not None else time.time()) // max(period, 1))
    payload = struct.pack(">Q", counter)
    digest = hmac.new(key, payload, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10 ** max(digits, 1))).zfill(max(digits, 1))


def resolve_otp_value(action: dict) -> str:
    value = str(action.get("value") or "").strip()
    if value:
        return value
    env_name = str(action.get("otp_env") or "").strip()
    if env_name:
        env_value = os.getenv(env_name, "").strip()
        if env_value:
            return env_value
    secret = str(action.get("totp_secret") or "").strip()
    if not secret:
        secret_env = str(action.get("totp_env") or "SPIDER_AUTH_TOTP_SECRET").strip()
        secret = os.getenv(secret_env, "").strip()
    if not secret:
        return ""
    digits = int(action.get("digits") or 6)
    period = int(action.get("period") or 30)
    return generate_totp(secret, digits=digits, period=period)


def resolve_site_challenge_fields(page, action: dict) -> tuple[str, str, str, str]:
    selector = str(action.get("selector") or "").strip()
    site_key = str(action.get("site_key") or "").strip()
    action_name = str(action.get("captcha_action") or action.get("action") or "").strip()
    c_data = str(action.get("c_data") or "").strip()
    page_data = str(action.get("page_data") or "").strip()
    if not selector:
        return site_key, action_name, c_data, page_data

    locator = page.locator(selector).first
    if not site_key:
        site_key = (
            locator.get_attribute("data-sitekey")
            or locator.get_attribute("sitekey")
            or locator.get_attribute("data-site-key")
            or ""
        )
    if not action_name:
        action_name = locator.get_attribute("data-action") or locator.get_attribute("action") or ""
    if not c_data:
        c_data = locator.get_attribute("data-cdata") or locator.get_attribute("cdata") or ""
    if not page_data:
        page_data = (
            locator.get_attribute("data-pagedata")
            or locator.get_attribute("pagedata")
            or locator.get_attribute("data-page-data")
            or ""
        )
    return site_key, action_name, c_data, page_data


def extract_script_sample(html: str, limit: int = 32000) -> str:
    snippets = re.findall(r"<script[^>]*>(.*?)</script>", html or "", re.IGNORECASE | re.DOTALL)
    joined = "\n".join(snippet.strip() for snippet in snippets if snippet.strip())
    if joined:
        return joined[:limit]
    return (html or "")[:limit]


def summarize_request(request) -> dict:
    return {
        "name": request.url,
        "type": request.resource_type,
        "method": request.method,
    }


def build_codegen_script(url: str, language: str, selectors: list[str]) -> str:
    selectors = selectors or ["body"]
    if language == "javascript":
        locator_lines = "\n".join(
            f"  await page.locator({json.dumps(selector)}).first().waitFor();"
            for selector in selectors
        )
        return (
            "const { chromium } = require('playwright');\n\n"
            "(async () => {\n"
            "  const browser = await chromium.launch({ headless: true });\n"
            "  const context = await browser.newContext();\n"
            f"  const page = await context.newPage();\n  await page.goto({json.dumps(url)}, {{ waitUntil: 'networkidle' }});\n"
            f"{locator_lines}\n"
            "  await context.close();\n  await browser.close();\n})();\n"
        )
    locator_lines = "\n".join(
        f"    page.locator({selector!r}).first.wait_for()\n"
        for selector in selectors
    ).rstrip()
    fallback_locator = "    page.locator('body').first.wait_for()"
    return (
        "from playwright.sync_api import sync_playwright\n\n"
        "with sync_playwright() as playwright:\n"
        "    browser = playwright.chromium.launch(headless=True)\n"
        "    context = browser.new_context()\n"
        "    page = context.new_page()\n"
        f"    page.goto({url!r}, wait_until='networkidle')\n"
        f"{locator_lines or fallback_locator}\n"
        "    context.close()\n"
        "    browser.close()\n"
    )


def suggest_locators(page) -> list[str]:
    suggestions = page.evaluate(
        """() => {
            const selectors = [];
            for (const element of Array.from(document.querySelectorAll('[data-testid], [id], [name], button, a, input, textarea, select')).slice(0, 12)) {
                if (element.getAttribute('data-testid')) {
                    selectors.push(`[data-testid="${element.getAttribute('data-testid')}"]`);
                    continue;
                }
                if (element.id) {
                    selectors.push(`#${element.id}`);
                    continue;
                }
                if (element.getAttribute('name')) {
                    selectors.push(`[name="${element.getAttribute('name')}"]`);
                    continue;
                }
                selectors.push(element.tagName.toLowerCase());
            }
            return selectors;
        }"""
    )
    return [selector for selector in suggestions if isinstance(selector, str)]


def apply_route_manifest(context, routes: list[dict]) -> list[dict]:
    applied = []
    for route in routes:
        pattern = str(route.get("pattern") or "**/*")
        action = str(route.get("action") or "continue")
        if action == "abort":
            context.route(pattern, lambda route, _action=action: route.abort())
        elif action == "fulfill":
            status = int(route.get("status") or 200)
            body = str(route.get("body") or "")
            headers = route.get("headers") or {"content-type": route.get("content_type") or "application/json"}
            context.route(
                pattern,
                lambda route, _status=status, _body=body, _headers=headers: route.fulfill(status=_status, body=_body, headers=_headers),
            )
        else:
            context.route(pattern, lambda route: route.continue_())
        applied.append({"pattern": pattern, "action": action})
    return applied


def run_browser_actions(
    page,
    actions: list[dict],
    network_requests: list[dict],
    extracted: dict,
    warnings: list[str],
    auth_spec: dict | None = None,
) -> list[str]:
    auth_spec = auth_spec or {}
    def condition_matches(condition: dict | None) -> bool:
        if not isinstance(condition, dict) or not condition:
            return True
        if condition.get("all"):
            return all(condition_matches(item) for item in condition.get("all") or [])
        if condition.get("any"):
            return any(condition_matches(item) for item in condition.get("any") or [])
        if condition.get("not"):
            return not condition_matches(condition.get("not"))
        if condition.get("selector_exists"):
            if page.locator(str(condition["selector_exists"])).count() == 0:
                return False
        if condition.get("selector_missing"):
            if page.locator(str(condition["selector_missing"])).count() > 0:
                return False
        if condition.get("url_contains") is not None:
            if str(condition["url_contains"]) not in page.url:
                return False
        if condition.get("title_contains") is not None:
            if str(condition["title_contains"]) not in page.title():
                return False
        capture_name = str(condition.get("capture") or "").strip()
        if capture_name:
            captured = extracted.get(capture_name)
            if condition.get("equals") is not None and str(captured) != str(condition.get("equals")):
                return False
            if condition.get("contains") is not None and str(condition.get("contains")) not in str(captured):
                return False
        return True

    def execute_single(action: dict, index: int) -> list[str]:
        local_artifacts: list[str] = []
        action_type = str(action.get("type") or "").strip()
        selector = str(action.get("selector") or "").strip()
        value = str(action.get("value") or "")
        save_as = str(action.get("save_as") or "").strip()
        timeout_ms = int(action.get("timeout_ms") or 30_000)

        if not condition_matches(action.get("when")):
            return local_artifacts

        if action_type == "if":
            branch = action.get("then") if condition_matches(action.get("when")) else action.get("else")
            if isinstance(branch, list):
                local_artifacts.extend(
                    run_browser_actions(
                        page,
                        branch,
                        network_requests,
                        extracted,
                        warnings,
                        auth_spec,
                    )
                )
            return local_artifacts

        if action_type == "goto":
            page.goto(str(action.get("url") or page.url), wait_until="networkidle", timeout=timeout_ms)
        elif action_type == "wait":
            if selector:
                page.wait_for_selector(selector, timeout=timeout_ms)
            else:
                page.wait_for_timeout(timeout_ms)
        elif action_type == "click":
            page.click(selector, timeout=timeout_ms)
        elif action_type == "type":
            page.fill(selector, value, timeout=timeout_ms)
        elif action_type == "select":
            page.select_option(selector, value=value, timeout=timeout_ms)
        elif action_type == "submit":
            if selector:
                page.locator(selector).press("Enter", timeout=timeout_ms)
            else:
                page.keyboard.press("Enter")
        elif action_type == "otp":
            otp_value = resolve_otp_value(action)
            if not otp_value:
                raise AssertionError("otp action requires value, otp_env, totp_secret, or totp_env")
            page.fill(selector, otp_value, timeout=timeout_ms)
        elif action_type == "mfa_totp":
            totp_value = resolve_otp_value(action)
            if not totp_value:
                raise AssertionError("mfa_totp action requires totp_secret or totp_env")
            page.fill(selector, totp_value, timeout=timeout_ms)
        elif action_type == "captcha_solve":
            from pyspider.captcha.solver import CaptchaSolver

            provider = str(action.get("provider") or auth_spec.get("captcha_provider") or "2captcha")
            api_key = str(
                action.get("api_key")
                or os.getenv(str(action.get("api_key_env") or auth_spec.get("captcha_api_key_env") or "CAPTCHA_API_KEY"), "")
                or auth_spec.get("captcha_api_key")
                or ""
            )
            solver = CaptchaSolver(api_key=api_key, service=provider)
            challenge = str(action.get("challenge") or "image").strip().lower()
            token = ""
            if challenge in {"recaptcha", "hcaptcha", "turnstile"}:
                site_key, challenge_action, c_data, page_data = resolve_site_challenge_fields(page, action)
                if challenge == "recaptcha":
                    result = solver.solve_recaptcha(site_key, page.url)
                elif challenge == "turnstile":
                    result = solver.solve_turnstile(
                        site_key,
                        page.url,
                        action=challenge_action,
                        c_data=c_data,
                        page_data=page_data,
                    )
                else:
                    result = solver.solve_hcaptcha(site_key, page.url)
                token = result.text if result.success else ""
                if not result.success:
                    raise AssertionError(result.error or "captcha solve failed")
            elif challenge == "image":
                image_bytes = b""
                if selector:
                    image_bytes = page.locator(selector).first.screenshot()
                elif action.get("image_base64"):
                    image_bytes = base64.b64decode(str(action.get("image_base64")))
                elif action.get("image_file"):
                    image_bytes = Path(str(action.get("image_file"))).read_bytes()
                result = solver.solve_image(image_bytes)
                token = result.text if result.success else ""
                if not result.success:
                    raise AssertionError(result.error or "image captcha solve failed")
            else:
                raise AssertionError("captcha_solve currently supports image/recaptcha/hcaptcha/turnstile challenges")
            if save_as:
                extracted[save_as] = token
            if action.get("target_selector"):
                page.fill(str(action.get("target_selector")), token, timeout=timeout_ms)
        elif action_type == "captcha_wait":
            captcha_selector = selector or str(action.get("captcha_selector") or "iframe[title*='captcha'], [class*='captcha'], [id*='captcha']")
            page.locator(captcha_selector).first.wait_for(state="hidden", timeout=timeout_ms)
        elif action_type == "hover":
            page.hover(selector, timeout=timeout_ms)
        elif action_type == "scroll":
            if selector:
                page.locator(selector).scroll_into_view_if_needed(timeout=timeout_ms)
            elif value.strip().lower() == "top":
                page.evaluate("window.scrollTo(0, 0)")
            else:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        elif action_type == "eval":
            result = page.evaluate(script_to_expression(value))
            if save_as:
                extracted[save_as] = result
        elif action_type == "wait_network_idle":
            page.wait_for_load_state("networkidle", timeout=timeout_ms)
        elif action_type == "assert":
            if selector:
                locator = page.locator(selector).first
                attr = str(action.get("attr") or "").strip()
                if attr:
                    observed = locator.get_attribute(attr) or ""
                else:
                    observed = locator.text_content() or ""
                if action.get("equals") is not None and observed != str(action.get("equals")):
                    raise AssertionError(f"assert equals failed for {selector}: {observed!r}")
                if action.get("contains") is not None and str(action.get("contains")) not in observed:
                    raise AssertionError(f"assert contains failed for {selector}: {observed!r}")
                if action.get("exists") is True and not observed:
                    raise AssertionError(f"assert exists failed for {selector}")
            elif action.get("url_contains") is not None:
                if str(action.get("url_contains")) not in page.url:
                    raise AssertionError(f"url assert failed: {page.url!r}")
            elif action.get("title_contains") is not None:
                title = page.title()
                if str(action.get("title_contains")) not in title:
                    raise AssertionError(f"title assert failed: {title!r}")
        elif action_type == "save_as":
            field_name = save_as or str(action.get("field") or action.get("name") or f"value_{index}")
            attr = str(action.get("attr") or "").strip()
            capture_kind = str(action.get("value") or "").strip().lower()
            if selector:
                locator = page.locator(selector).first
                extracted[field_name] = (
                    locator.get_attribute(attr) if attr else locator.text_content()
                ) or ""
            elif capture_kind == "url":
                extracted[field_name] = page.url
            elif capture_kind == "title":
                extracted[field_name] = page.title()
            elif capture_kind in {"html", "dom"}:
                extracted[field_name] = page.content()
            else:
                warnings.append(f"unsupported save_as capture kind: {capture_kind or 'selector-required'}")
        elif action_type == "listen_network":
            page.wait_for_load_state("networkidle", timeout=timeout_ms)
            extracted[save_as or "network_requests"] = deepcopy(network_requests)
        elif action_type == "reverse_profile":
            from pyspider.node_reverse.client import NodeReverseClient

            base_url = str(action.get("base_url") or auth_spec.get("node_reverse_base_url") or "http://localhost:3000")
            client = NodeReverseClient(base_url)
            script_sample = extract_script_sample(page.content())
            payload = {
                "detect": client.detect_anti_bot(html=page.content(), url=page.url),
                "profile": client.profile_anti_bot(html=page.content(), url=page.url),
                "fingerprint_spoof": client.spoof_fingerprint("chrome", "windows"),
                "tls_fingerprint": client.generate_tls_fingerprint("chrome", "120"),
            }
            if script_sample.strip():
                payload["crypto_analysis"] = client.analyze_crypto(script_sample)
            extracted[save_as or "reverse_runtime"] = payload
        elif action_type == "reverse_analyze_crypto":
            from pyspider.node_reverse.client import NodeReverseClient

            base_url = str(action.get("base_url") or auth_spec.get("node_reverse_base_url") or "http://localhost:3000")
            client = NodeReverseClient(base_url)
            code = value
            if selector:
                code = page.locator(selector).first.text_content() or ""
            extracted[save_as or "reverse_crypto"] = client.analyze_crypto(code)
        elif action_type == "screenshot":
            path = value or f"artifacts/browser/action-{index}.png"
            ensure_parent(path)
            page.screenshot(path=path, full_page=True)
            local_artifacts.append(path)
        else:
            warnings.append(f"unsupported playwright helper action: {action_type}")
        return local_artifacts

    artifacts: list[str] = []
    for index, action in enumerate(actions):
        attempts = max(1, int(action.get("retry") or 0) + 1)
        retry_delay_ms = int(action.get("retry_delay_ms") or 0)
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                artifacts.extend(execute_single(action, index))
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if attempt + 1 < attempts and retry_delay_ms > 0:
                    time.sleep(retry_delay_ms / 1000)
        if last_error is not None:
            warnings.append(f"auth action failed ({action.get('type')}): {last_error}")
    return artifacts


def run_extract_specs(page, html: str, current_url: str, title: str, extract_specs: list[dict], extracted: dict, warnings: list[str]) -> None:
    for spec in extract_specs:
        field = str(spec.get("field") or "").strip()
        extract_type = str(spec.get("type") or "").strip()
        expr = spec.get("expr")
        attr = spec.get("attr")
        if not field:
            continue

        if field == "url":
            extracted[field] = current_url
            continue
        if field in {"html", "dom"}:
            extracted[field] = html
            continue
        if field == "title" and extract_type == "ai":
            extracted[field] = title
            continue

        try:
            if extract_type == "css":
                if expr == "title":
                    extracted[field] = title
                elif expr:
                    extracted[field] = page.locator(str(expr)).first.text_content() or ""
            elif extract_type == "css_attr" and expr and attr:
                extracted[field] = page.locator(str(expr)).first.get_attribute(str(attr)) or ""
            elif extract_type == "regex" and expr:
                match = re.search(str(expr), html, re.MULTILINE | re.DOTALL)
                if match:
                    extracted[field] = match.group(1) if match.groups() else match.group(0)
            else:
                warnings.append(f"unsupported playwright helper extract type: {extract_type}")
        except Exception as exc:
            warnings.append(f"extract failed for {field}: {exc}")


def main() -> int:
    args = parse_args()
    job_spec = load_job_file(args.job_file)

    browser_spec = job_spec.get("browser") or {}
    target_spec = job_spec.get("target") or {}
    output_spec = job_spec.get("output") or {}
    resource_spec = job_spec.get("resources") or {}
    auth_spec = load_auth_file(args.auth_file)

    url = args.url or target_spec.get("url")
    if not url:
        raise SystemExit("--url or --job-file target.url is required")

    configured_output_path = output_spec.get("path")
    screenshot_path = args.screenshot
    if not screenshot_path and is_screenshot_path(configured_output_path):
        screenshot_path = configured_output_path
    if not screenshot_path and args.job_file:
        screenshot_path = default_screenshot_path(job_spec)

    html_path = args.html
    if not html_path and is_html_path(configured_output_path):
        html_path = configured_output_path
    if not html_path and args.job_file:
        html_path = default_html_path(job_spec)
    timeout_seconds = args.timeout_seconds
    if resource_spec.get("timeout_ms"):
        timeout_seconds = max(1, int(resource_spec["timeout_ms"]) // 1000)
    user_agent = args.user_agent or target_spec.get("headers", {}).get("User-Agent", "")
    headless = browser_spec.get("headless", True) if args.job_file else args.headless
    trace_path = args.trace_path or output_spec.get("trace_path")
    har_path = args.har_path or output_spec.get("har_path")
    har_replay = args.har_replay or output_spec.get("har_replay")
    route_manifest = args.route_manifest or output_spec.get("route_manifest")
    codegen_out = args.codegen_out or output_spec.get("codegen_out")
    codegen_language = args.codegen_language
    storage_state = args.storage_state or auth_spec.get("storage_state_file") or browser_spec.get("storage_state_file") or ""
    cookies_file = args.cookies_file or auth_spec.get("cookies_file") or browser_spec.get("cookies_file") or ""
    save_storage_state = args.save_storage_state or output_spec.get("save_storage_state") or ""
    save_cookies_file = args.save_cookies_file or output_spec.get("save_cookies_file") or ""
    route_rules = load_route_manifest(route_manifest)

    ensure_parent(screenshot_path)
    ensure_parent(html_path)
    ensure_parent(trace_path)
    ensure_parent(har_path)
    ensure_parent(codegen_out)
    ensure_parent(save_storage_state)
    ensure_parent(save_cookies_file)

    with sync_playwright() as playwright:
        browser = launch_browser(playwright, headless=headless)
        context_kwargs = {}
        if user_agent:
            context_kwargs["user_agent"] = user_agent
        if har_path:
            context_kwargs["record_har_path"] = har_path
        if storage_state:
            context_kwargs["storage_state"] = storage_state
        context = browser.new_context(**context_kwargs)
        if cookies_file:
            cookies = load_cookies_file(cookies_file)
            if cookies:
                context.add_cookies(cookies)
        if har_replay:
            context.route_from_har(har_replay, not_found="fallback")
        applied_routes = apply_route_manifest(context, route_rules)
        if trace_path:
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        network_requests: list[dict] = []
        console_messages: list[dict] = []
        page.on("request", lambda request: network_requests.append(summarize_request(request)))
        page.on(
            "console",
            lambda message: console_messages.append(
                {
                    "type": message.type,
                    "text": message.text,
                }
            ),
        )
        page.goto(url, wait_until="networkidle", timeout=timeout_seconds * 1000)

        for name, value in (target_spec.get("cookies") or {}).items():
            context.add_cookies([{"name": name, "value": value, "url": url}])
        if target_spec.get("cookies"):
            page.reload(wait_until="networkidle", timeout=timeout_seconds * 1000)

        extracted: dict = {}
        warnings: list[str] = []
        artifacts: list[str] = []

        auth_actions = auth_spec.get("actions") or []
        if isinstance(auth_actions, list) and auth_actions:
            artifacts.extend(
                run_browser_actions(
                    page,
                    auth_actions,
                    network_requests,
                    extracted,
                    warnings,
                    auth_spec,
                )
            )

        artifacts.extend(run_browser_actions(
            page,
            browser_spec.get("actions") or [],
            network_requests,
            extracted,
            warnings,
            auth_spec,
        ))

        title = page.title()
        current_url = page.url
        html = page.content()

        run_extract_specs(
            page,
            html,
            current_url,
            title,
            job_spec.get("extract") or [],
            extracted,
            warnings,
        )

        for capture in browser_spec.get("capture") or []:
            if capture in {"html", "dom"}:
                extracted[capture] = html
            elif capture == "screenshot" and screenshot_path:
                page.screenshot(path=screenshot_path, full_page=True)
                artifacts.append(screenshot_path)
            elif capture == "listen_network":
                extracted["network_requests"] = deepcopy(network_requests)
            elif capture == "console":
                extracted["console_messages"] = deepcopy(console_messages)
            elif capture == "har":
                if not har_path:
                    warnings.append("har capture requested but no har path was configured")

        if screenshot_path and screenshot_path not in artifacts:
            page.screenshot(path=screenshot_path, full_page=True)
        if html_path:
            Path(html_path).write_text(html, encoding="utf-8")
        if save_storage_state:
            context.storage_state(path=save_storage_state)
        if save_cookies_file:
            Path(save_cookies_file).write_text(
                json.dumps(context.cookies(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        locator_suggestions = suggest_locators(page)
        generated_script = ""
        if args.tooling_command == "codegen" or codegen_out:
            generated_script = build_codegen_script(current_url, codegen_language, locator_suggestions)
            if codegen_out:
                Path(codegen_out).write_text(generated_script, encoding="utf-8")
        if trace_path:
            context.tracing.stop(path=trace_path)

        payload = {
            "command": args.tooling_command,
            "title": title,
            "url": current_url,
            "html_path": html_path,
            "screenshot_path": screenshot_path,
            "storage_state_path": save_storage_state,
            "cookies_file_path": save_cookies_file,
            "trace_path": trace_path,
            "har_path": har_path,
            "har_replay": har_replay,
            "applied_routes": applied_routes,
            "codegen_out": codegen_out,
            "generated_script": generated_script,
            "locator_suggestions": locator_suggestions,
            "extract": extracted,
            "network_requests": network_requests,
            "console_messages": console_messages,
            "artifacts": artifacts,
            "warnings": warnings,
            "body": html,
        }
        print(json.dumps(payload, ensure_ascii=False))

        context.close()
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
