package com.javaspider.selector;

import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public final class DevToolsAnalyzer {
    private static final List<String> IMPORTANT_ATTRS = List.of(
        "id", "class", "name", "type", "href", "src", "role", "aria-label",
        "data-testid", "data-test", "placeholder", "action", "method"
    );

    public DevToolsReport analyze(String html, List<DevToolsNetworkArtifact> network, List<Map<String, String>> consoleEvents) {
        Document document = Jsoup.parse(html == null ? "" : html);
        List<ElementSnapshot> elements = new ArrayList<>();
        for (Element element : document.getAllElements()) {
            if ("#root".equals(element.tagName())) {
                continue;
            }
            elements.add(snapshot(element));
        }
        List<String> sources = new ArrayList<>();
        List<String> inline = new ArrayList<>();
        for (Element script : document.select("script")) {
            String src = script.attr("src").trim();
            if (!src.isBlank()) {
                sources.add(src);
                continue;
            }
            String code = script.data().isBlank() ? script.html().trim() : script.data().trim();
            if (!code.isBlank()) {
                inline.add(code.length() > 2000 ? code.substring(0, 2000) : code);
            }
        }
        List<DevToolsNetworkArtifact> networkCandidates = networkCandidates(network == null ? List.of() : network);
        List<ReverseRecommendation> recommendations = recommendReverseRoutes(html == null ? "" : html, sources, inline, networkCandidates);
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("element_count", elements.size());
        summary.put("script_count", sources.size() + inline.size());
        summary.put("network_candidate_count", networkCandidates.size());
        summary.put("best_reverse_route", recommendations.isEmpty() ? "" : recommendations.get(0).kind());
        return new DevToolsReport(
            elements,
            sources,
            inline,
            networkCandidates,
            consoleEvents == null ? List.of() : consoleEvents,
            recommendations,
            summary
        );
    }

    private ElementSnapshot snapshot(Element element) {
        Map<String, String> attrs = new LinkedHashMap<>();
        for (String attr : IMPORTANT_ATTRS) {
            String value = element.attr(attr).trim();
            if (!value.isBlank()) {
                attrs.put(attr, value);
            }
        }
        String text = element.text().trim();
        if (text.length() > 120) {
            text = text.substring(0, 120);
        }
        return new ElementSnapshot(element.tagName(), element.cssSelector(), fullXPath(element), text, attrs);
    }

    private List<DevToolsNetworkArtifact> networkCandidates(List<DevToolsNetworkArtifact> network) {
        List<DevToolsNetworkArtifact> result = new ArrayList<>();
        java.util.Set<String> seen = new java.util.LinkedHashSet<>();
        for (DevToolsNetworkArtifact entry : network) {
            if (entry == null || entry.url() == null || entry.url().isBlank() || seen.contains(entry.url())) {
                continue;
            }
            String type = entry.resourceType() == null ? "" : entry.resourceType().toLowerCase(Locale.ROOT);
            String signal = (entry.url() + " " + type).toLowerCase(Locale.ROOT);
            if (List.of("script", "xhr", "fetch", "websocket", "document").contains(type)
                || List.of("api", "sign", "token", "encrypt", "decrypt", "jsonp", "webpack").stream().anyMatch(signal::contains)) {
                seen.add(entry.url());
                result.add(entry);
            }
        }
        return result;
    }

    private List<ReverseRecommendation> recommendReverseRoutes(
        String html,
        List<String> sources,
        List<String> inline,
        List<DevToolsNetworkArtifact> network
    ) {
        StringBuilder corpusBuilder = new StringBuilder(html.length() > 8000 ? html.substring(0, 8000) : html);
        sources.forEach(value -> corpusBuilder.append('\n').append(value));
        inline.forEach(value -> corpusBuilder.append('\n').append(value));
        network.forEach(value -> corpusBuilder.append('\n').append(value.url()));
        String corpus = corpusBuilder.toString().toLowerCase(Locale.ROOT);

        List<ReverseRecommendation> result = new ArrayList<>();
        addRecommendation(result, corpus, "analyze_crypto", 100, "发现加密、签名或摘要相关标记，优先交给 Node.js crypto 逆向分析",
            List.of("cryptojs", "crypto.subtle", "aes", "rsa", "md5", "sha1", "sha256", "encrypt", "decrypt", "signature", "sign"));
        addRecommendation(result, corpus, "analyze_webpack", 90, "发现 webpack 模块运行时，适合进入模块表和导出函数逆向",
            List.of("__webpack_require__", "webpackjsonp", "webpackchunk", "webpack://"));
        addRecommendation(result, corpus, "simulate_browser", 80, "脚本依赖浏览器运行时对象，适合用 Node.js 浏览器环境模拟",
            List.of("localstorage", "sessionstorage", "navigator.", "document.", "window.", "canvas", "webdriver"));
        addRecommendation(result, corpus, "analyze_ast", 60, "存在外链或内联脚本，适合进行 AST 结构分析和函数定位",
            List.of(".js", "function", "=>", "eval(", "new function"));
        result.sort(Comparator.comparingInt(ReverseRecommendation::priority).reversed().thenComparing(ReverseRecommendation::kind));
        return result;
    }

    private void addRecommendation(List<ReverseRecommendation> result, String corpus, String kind, int priority, String reason, List<String> markers) {
        List<String> evidence = markers.stream()
            .filter(marker -> corpus.contains(marker.toLowerCase(Locale.ROOT)))
            .limit(8)
            .toList();
        if (!evidence.isEmpty()) {
            result.add(new ReverseRecommendation(kind, priority, reason, evidence));
        }
    }

    private String fullXPath(Element element) {
        List<String> parts = new ArrayList<>();
        Element current = element;
        while (current != null && !"#root".equals(current.tagName())) {
            if (!current.id().isBlank()) {
                parts.add(current.tagName() + "[@id=" + xpathLiteral(current.id()) + "]");
                break;
            }
            int index = 1;
            Element sibling = current.previousElementSibling();
            while (sibling != null) {
                if (sibling.tagName().equals(current.tagName())) {
                    index++;
                }
                sibling = sibling.previousElementSibling();
            }
            parts.add(current.tagName() + "[" + index + "]");
            current = current.parent();
        }
        java.util.Collections.reverse(parts);
        return parts.isEmpty() ? "" : "/" + String.join("/", parts);
    }

    private String xpathLiteral(String value) {
        if (!value.contains("'")) {
            return "'" + value + "'";
        }
        if (!value.contains("\"")) {
            return "\"" + value + "\"";
        }
        String[] parts = value.split("'");
        return "concat(" + String.join(", \"'\", ", java.util.Arrays.stream(parts).map(part -> "'" + part + "'").toList()) + ")";
    }

    public record ElementSnapshot(String tag, String css, String xpath, String text, Map<String, String> attrs) {
    }

    public record DevToolsNetworkArtifact(String url, String method, int status, String resourceType) {
    }

    public record ReverseRecommendation(String kind, int priority, String reason, List<String> evidence) {
    }

    public record DevToolsReport(
        List<ElementSnapshot> elements,
        List<String> scriptSources,
        List<String> inlineScriptSamples,
        List<DevToolsNetworkArtifact> networkCandidates,
        List<Map<String, String>> consoleEvents,
        List<ReverseRecommendation> reverseRecommendations,
        Map<String, Object> summary
    ) {
        public ReverseRecommendation bestReverseRoute() {
            return reverseRecommendations.isEmpty() ? null : reverseRecommendations.get(0);
        }
    }
}
