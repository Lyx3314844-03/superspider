package com.javaspider.antibot;

import java.util.ArrayList;
import java.time.Duration;
import java.time.Instant;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

public final class AccessFrictionAnalyzer {
    private AccessFrictionAnalyzer() {
    }

    public static AccessFrictionReport analyze(int statusCode, Map<String, String> headers, String html, String url) {
        Map<String, String> normalizedHeaders = normalizeHeaders(headers);
        StringBuilder headerText = new StringBuilder();
        normalizedHeaders.forEach((key, value) -> headerText.append(key).append(": ").append(value).append("\n"));
        String haystack = ((url == null ? "" : url) + "\n" + (html == null ? "" : html) + "\n" + headerText)
            .toLowerCase(Locale.ROOT);
        List<String> signals = new ArrayList<>();

        if (statusCode == 401 || statusCode == 403) {
            signals.add("auth-or-forbidden");
        }
        if (statusCode == 429) {
            signals.add("rate-limited");
        }
        if (statusCode == 503 || statusCode == 520 || statusCode == 521 || statusCode == 522) {
            signals.add("temporary-gateway-or-challenge");
        }

        Map<String, List<String>> groups = new LinkedHashMap<>();
        groups.put("captcha", List.of("captcha", "recaptcha", "hcaptcha", "turnstile", "验证码", "滑块"));
        groups.put("slider-captcha", List.of("geetest", "gt_captcha", "nc_token", "aliyuncaptcha", "tencentcaptcha", "滑块验证", "拖动滑块"));
        groups.put("managed-browser-challenge", List.of("cf-chl", "checking your browser", "browser verification", "challenge-platform", "please enable javascript"));
        groups.put("request-blocked", List.of("access denied", "request blocked", "request rejected", "被拒绝", "封禁", "访问过于频繁"));
        groups.put("auth-required", List.of("login", "sign in", "扫码", "登录", "安全验证"));
        groups.put("waf-vendor", List.of("cloudflare", "akamai", "imperva", "datadome", "perimeterx", "aliyun", "tencent", "bytedance", "dun.163"));
        groups.put("risk-control", List.of("risk control", "风险", "异常访问", "suspicious activity", "环境异常", "账号存在风险"));
        groups.put("js-signature", List.of("x-bogus", "a_bogus", "mstoken", "m_h5_tk", "h5st", "_signature", "cryptojs", "__webpack_require__", "webpackchunk"));
        groups.put("fingerprint-required", List.of("navigator.webdriver", "canvas fingerprint", "webgl", "deviceid", "fpcollect", "sec-ch-ua"));

        for (Map.Entry<String, List<String>> entry : groups.entrySet()) {
            for (String pattern : entry.getValue()) {
                if (haystack.contains(pattern.toLowerCase(Locale.ROOT))) {
                    signals.add(entry.getKey());
                    break;
                }
            }
        }

        if (normalizedHeaders.containsKey("retry-after")) {
            signals.add("retry-after");
        }
        if (normalizedHeaders.containsKey("cf-ray")
            || normalizedHeaders.containsKey("x-datadome")
            || normalizedHeaders.containsKey("x-akamai-transformed")) {
            signals.add("waf-vendor");
        }
        String htmlLower = html == null ? "" : html.toLowerCase(Locale.ROOT);
        if (statusCode == 200
            && html != null
            && !html.trim().isEmpty()
            && html.trim().length() < 300
            && (htmlLower.contains("<script") || htmlLower.contains("enable javascript") || htmlLower.contains("window.location"))) {
            signals.add("empty-or-script-shell");
        }

        signals = dedupe(signals);
        Integer retryAfter = parseRetryAfter(normalizedHeaders.get("retry-after"));
        String level = levelFor(statusCode, signals);
        List<String> actions = actionsFor(signals, retryAfter);
        boolean shouldUpgradeToBrowser = containsAny(
            signals,
            "managed-browser-challenge",
            "captcha",
            "slider-captcha",
            "auth-required",
            "waf-vendor",
            "js-signature",
            "fingerprint-required",
            "empty-or-script-shell"
        );
        boolean requiresHumanAccess = containsAny(signals, "captcha", "slider-captcha", "auth-required");

        return new AccessFrictionReport(
            level,
            signals,
            actions,
            retryAfter,
            shouldUpgradeToBrowser,
            requiresHumanAccess,
            challengeHandoff(signals),
            capabilityPlan(level, signals, retryAfter),
            "medium".equals(level) || "high".equals(level)
        );
    }

    private static Map<String, String> normalizeHeaders(Map<String, String> headers) {
        Map<String, String> out = new LinkedHashMap<>();
        if (headers == null) {
            return out;
        }
        headers.forEach((key, value) -> {
            if (key != null && value != null) {
                out.put(key.toLowerCase(Locale.ROOT), value);
            }
        });
        return out;
    }

    private static Integer parseRetryAfter(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Math.max(0, Integer.parseInt(value.trim()));
        } catch (NumberFormatException ignored) {
            try {
                ZonedDateTime target = ZonedDateTime.parse(value.trim(), DateTimeFormatter.RFC_1123_DATE_TIME);
                long seconds = Duration.between(Instant.now(), target.toInstant()).getSeconds();
                return (int) Math.max(0, seconds);
            } catch (Exception ignoredDate) {
                return null;
            }
        }
    }

    private static String levelFor(int statusCode, List<String> signals) {
        if (containsAny(signals, "captcha", "slider-captcha", "auth-required", "request-blocked")) {
            return "high";
        }
        if (statusCode == 401 || statusCode == 403 || statusCode == 429) {
            return "high";
        }
        if (containsAny(signals, "managed-browser-challenge", "waf-vendor", "risk-control", "js-signature", "fingerprint-required", "empty-or-script-shell")) {
            return "medium";
        }
        return signals.isEmpty() ? "none" : "low";
    }

    private static List<String> actionsFor(List<String> signals, Integer retryAfter) {
        List<String> actions = new ArrayList<>();
        if (retryAfter != null || containsAny(signals, "rate-limited")) {
            actions.addAll(List.of("honor-retry-after", "reduce-concurrency", "increase-crawl-delay"));
        }
        if (containsAny(signals, "managed-browser-challenge", "waf-vendor", "empty-or-script-shell")) {
            actions.addAll(List.of("render-with-browser", "persist-session-state", "capture-html-screenshot-har"));
        }
        if (containsAny(signals, "js-signature", "fingerprint-required")) {
            actions.addAll(List.of("capture-devtools-network", "run-nodejs-reverse-analysis", "replay-authorized-session-only"));
        }
        if (containsAny(signals, "captcha", "slider-captcha", "auth-required")) {
            actions.addAll(List.of("pause-for-human-access", "document-authorization-requirement"));
        }
        if (containsAny(signals, "request-blocked")) {
            actions.add("stop-or-seek-site-permission");
        }
        actions.add("respect-robots-and-terms");
        return dedupe(actions);
    }

    private static boolean containsAny(List<String> values, String... candidates) {
        for (String value : values) {
            for (String candidate : candidates) {
                if (value.equals(candidate)) {
                    return true;
                }
            }
        }
        return false;
    }

    private static List<String> dedupe(List<String> values) {
        Set<String> seen = new LinkedHashSet<>(values);
        return new ArrayList<>(seen);
    }

    private static Map<String, Object> challengeHandoff(List<String> signals) {
        Map<String, Object> handoff = new LinkedHashMap<>();
        if (!containsAny(signals, "captcha", "slider-captcha", "auth-required", "risk-control")) {
            handoff.put("required", false);
            handoff.put("method", "none");
            handoff.put("resume", "automatic");
            return handoff;
        }
        handoff.put("required", true);
        handoff.put("method", "human-authorized-browser-session");
        handoff.put("resume", "after-challenge-cleared-and-session-persisted");
        handoff.put("artifacts", List.of("screenshot", "html", "cookies-or-storage-state", "network-summary"));
        handoff.put("stop_conditions", List.of("explicit-access-denied", "robots-disallow", "missing-site-permission"));
        return handoff;
    }

    private static Map<String, Object> capabilityPlan(String level, List<String> signals, Integer retryAfter) {
        List<String> transportOrder = new ArrayList<>();
        transportOrder.add("http");
        if (containsAny(signals, "managed-browser-challenge", "waf-vendor", "captcha", "slider-captcha", "auth-required", "empty-or-script-shell")) {
            transportOrder.add("browser-render");
            transportOrder.add("authorized-session-replay");
        }
        if (containsAny(signals, "js-signature", "fingerprint-required")) {
            transportOrder.add("devtools-analysis");
            transportOrder.add("node-reverse-analysis");
        }
        if (containsAny(signals, "request-blocked")) {
            transportOrder.add("stop-until-permission");
        }

        int crawlDelaySeconds = retryAfter == null ? 1 : retryAfter;
        if ("medium".equals(level)) {
            crawlDelaySeconds = Math.max(crawlDelaySeconds, 5);
        }
        if ("high".equals(level)) {
            crawlDelaySeconds = Math.max(crawlDelaySeconds, 30);
        }
        int concurrency = ("medium".equals(level) || "high".equals(level)) ? 1 : 2;
        int retryBudget = containsAny(signals, "request-blocked") ? 0 : ("high".equals(level) ? 1 : 2);

        Map<String, Object> throttle = new LinkedHashMap<>();
        throttle.put("concurrency", concurrency);
        throttle.put("crawl_delay_seconds", crawlDelaySeconds);
        throttle.put("jitter_ratio", 0.35);
        throttle.put("honor_retry_after", true);

        Map<String, Object> session = new LinkedHashMap<>();
        session.put("persist_storage_state", true);
        session.put("reuse_only_after_authorized_access", containsAny(signals, "captcha", "slider-captcha", "auth-required", "risk-control"));
        session.put("isolate_by_site", true);

        Map<String, Object> plan = new LinkedHashMap<>();
        plan.put("mode", "maximum-compliant");
        plan.put("transport_order", dedupe(transportOrder));
        plan.put("throttle", throttle);
        plan.put("session", session);
        plan.put("artifacts", List.of("html", "screenshot", "cookies-or-storage-state", "network-summary", "friction-report"));
        plan.put("retry_budget", retryBudget);
        plan.put("stop_conditions", List.of("robots-disallow", "explicit-access-denied", "missing-site-permission"));
        return plan;
    }

    public record AccessFrictionReport(
        String level,
        List<String> signals,
        List<String> recommendedActions,
        Integer retryAfterSeconds,
        boolean shouldUpgradeToBrowser,
        boolean requiresHumanAccess,
        Map<String, Object> challengeHandoff,
        Map<String, Object> capabilityPlan,
        boolean blocked
    ) {
        public Map<String, Object> toMap() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("level", level);
            out.put("signals", signals);
            out.put("recommended_actions", recommendedActions);
            out.put("retry_after_seconds", retryAfterSeconds);
            out.put("should_upgrade_to_browser", shouldUpgradeToBrowser);
            out.put("requires_human_access", requiresHumanAccess);
            out.put("challenge_handoff", challengeHandoff);
            out.put("capability_plan", capabilityPlan);
            out.put("blocked", blocked);
            return out;
        }
    }
}
