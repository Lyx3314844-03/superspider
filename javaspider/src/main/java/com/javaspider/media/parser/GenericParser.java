package com.javaspider.media.parser;

import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 通用视频解析器
 */
public class GenericParser implements VideoParser {
    
    @Override
    public boolean supports(String url) {
        return true; // 支持所有 URL
    }
    
    @Override
    public VideoInfo parse(String url) throws Exception {
        VideoInfo info = new VideoInfo();
        info.setUrl(url);
        info.setPlatform(detectPlatform(url));

        if (isDirectMediaUrl(url)) {
            info.setTitle(fallbackTitle(url));
            info.setVideoId(extractVideoId(url));
            info.setVideoUrl(url);
            info.getVideoUrls().add(url);
            info.getFormats().add(Map.of("kind", classifyMediaUrl(url), "url", url));
            return info;
        }

        try {
            String html = fetchPage(url);
            return parseHtml(url, html, info);
        } catch (Exception e) {
            info.setTitle(fallbackTitle(url));
        }

        return info;
    }

    public VideoInfo parseArtifacts(String pageUrl, String html, List<String> artifactTexts) {
        VideoInfo info = new VideoInfo();
        info.setUrl(pageUrl);
        info.setPlatform(detectPlatform(pageUrl));
        if (html != null && !html.isBlank()) {
            info = parseHtml(pageUrl, html, info);
        } else {
            info.setTitle(fallbackTitle(pageUrl));
            info.setVideoId(extractVideoId(pageUrl));
        }

        LinkedHashSet<String> videoUrls = new LinkedHashSet<>(info.getVideoUrls());
        for (String artifactText : artifactTexts) {
            if (artifactText == null || artifactText.isBlank()) {
                continue;
            }
            Matcher matcher = Pattern.compile(
                "(https?://[^\"'\\s<>]+(?:\\.m3u8|\\.mpd|\\.mp4|\\.webm|\\.m4v|\\.mov)[^\"'\\s<>]*)",
                Pattern.CASE_INSENSITIVE
            ).matcher(artifactText);
            while (matcher.find()) {
                addVideoUrl(videoUrls, normalizeEscapedUrl(matcher.group(1), pageUrl));
            }
            try {
                JsonElement payload = JsonParser.parseString(artifactText.trim());
                collectFromJson(payload, pageUrl, info, videoUrls);
            } catch (Exception ignored) {
                // best-effort artifact parsing
            }
        }

        info.getVideoUrls().clear();
        info.getVideoUrls().addAll(videoUrls);
        if (!info.getVideoUrls().isEmpty()) {
            info.setVideoUrl(info.getVideoUrls().get(0));
        }
        info.getFormats().clear();
        for (String videoUrl : info.getVideoUrls()) {
            info.getFormats().add(Map.of("kind", classifyMediaUrl(videoUrl), "url", videoUrl));
        }
        return info;
    }

    VideoInfo parseHtml(String url, String html, VideoInfo info) {
        Document document = Jsoup.parse(html == null ? "" : html, url);
        info.setTitle(firstNonBlank(
            cleanText(document.select("meta[property=og:title]").attr("content")),
            cleanText(document.select("meta[name=twitter:title]").attr("content")),
            cleanText(document.title()),
            cleanText(info.getTitle()),
            fallbackTitle(url)
        ));
        info.setDescription(firstNonBlank(
            cleanText(document.select("meta[property=og:description]").attr("content")),
            cleanText(document.select("meta[name=description]").attr("content")),
            cleanText(firstMatch(html,
                "\"(?:desc|description)\"\\s*:\\s*\"([^\"]+)\""
            )),
            cleanText(info.getDescription())
        ));
        info.setCoverUrl(firstNonBlank(
            normalizeEscapedUrl(document.select("meta[property=og:image]").attr("content"), url),
            normalizeEscapedUrl(document.select("meta[name=twitter:image]").attr("content"), url),
            normalizeEscapedUrl(document.select("video").attr("poster"), url),
            cleanText(info.getCoverUrl())
        ));
        info.setVideoId(firstNonBlank(info.getVideoId(), extractVideoId(url)));
        if (info.getDuration() <= 0) {
            info.setDuration(parseInteger(firstMatch(html, "\"duration\"\\s*:\\s*(\\d+)")));
        }

        LinkedHashSet<String> videoUrls = new LinkedHashSet<>(info.getVideoUrls());
        for (Element element : document.select("meta[property=og:video], meta[property=og:video:url], meta[name=twitter:player:stream]")) {
            addVideoUrl(videoUrls, normalizeEscapedUrl(element.attr("content"), url));
        }
        for (Element element : document.select("video[src], source[src]")) {
            addVideoUrl(videoUrls, normalizeEscapedUrl(element.attr("src"), url));
        }

        Matcher matcher = Pattern.compile(
            "(https?://[^\"'\\s<>]+(?:\\.m3u8|\\.mpd|\\.mp4|\\.webm|\\.m4v|\\.mov)[^\"'\\s<>]*)",
            Pattern.CASE_INSENSITIVE
        ).matcher(html);
        while (matcher.find()) {
            addVideoUrl(videoUrls, normalizeEscapedUrl(matcher.group(1), url));
        }

        Matcher ldJson = Pattern.compile(
            "(?is)<script[^>]+type=[\"']application/ld\\+json[\"'][^>]*>(.*?)</script>"
        ).matcher(html);
        while (ldJson.find()) {
            try {
                JsonElement payload = JsonParser.parseString(ldJson.group(1).trim());
                collectFromJson(payload, url, info, videoUrls);
            } catch (Exception ignored) {
                // best-effort
            }
        }

        info.getVideoUrls().clear();
        info.getVideoUrls().addAll(videoUrls);
        if (!info.getVideoUrls().isEmpty()) {
            info.setVideoUrl(info.getVideoUrls().get(0));
        }
        info.getFormats().clear();
        for (String videoUrl : info.getVideoUrls()) {
            info.getFormats().add(Map.of("kind", classifyMediaUrl(videoUrl), "url", videoUrl));
        }
        return info;
    }

    private String detectPlatform(String url) {
        String lower = url.toLowerCase(Locale.ROOT);
        if (lower.contains("bilibili.com") || lower.contains("b23.tv")) {
            return "Bilibili";
        }
        if (lower.contains("iqiyi.com")) {
            return "IQIYI";
        }
        if (lower.contains("qq.com") || lower.contains("v.qq.com")) {
            return "Tencent";
        }
        if (lower.contains("douyin.com")) {
            return "Douyin";
        }
        if (Pattern.compile("/video/((?:BV|av)[A-Za-z0-9]+)", Pattern.CASE_INSENSITIVE).matcher(url).find()) {
            return "Bilibili";
        }
        if (Pattern.compile("/video/(\\d+)", Pattern.CASE_INSENSITIVE).matcher(url).find()) {
            return "Douyin";
        }
        return "Generic";
    }

    private String fetchPage(String urlString) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) new URL(urlString).openConnection();
        conn.setRequestMethod("GET");
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(15000);
        conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36");
        conn.setRequestProperty("Referer", urlString);

        BufferedReader reader = new BufferedReader(
            new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8)
        );
        StringBuilder html = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            html.append(line).append('\n');
        }
        reader.close();
        conn.disconnect();
        return html.toString();
    }

    private String firstMatch(String text, String... patterns) {
        for (String patternText : patterns) {
            Matcher matcher = Pattern.compile(patternText, Pattern.CASE_INSENSITIVE | Pattern.DOTALL).matcher(text);
            if (matcher.find()) {
                return matcher.group(1).trim();
            }
        }
        return "";
    }

    private void collectFromJson(JsonElement value, String pageUrl, VideoInfo info, Set<String> urls) {
        if (value == null || value.isJsonNull()) {
            return;
        }
        if (value.isJsonArray()) {
            for (JsonElement item : value.getAsJsonArray()) {
                collectFromJson(item, pageUrl, info, urls);
            }
            return;
        }
        if (!value.isJsonObject()) {
            return;
        }
        var object = value.getAsJsonObject();
        if (object.has("@type") && "VideoObject".equalsIgnoreCase(cleanText(stringValue(object.get("@type"))))) {
            info.setTitle(firstNonBlank(cleanText(stringValue(object.get("name"))), cleanText(stringValue(object.get("headline"))), info.getTitle()));
            info.setDescription(firstNonBlank(cleanText(stringValue(object.get("description"))), info.getDescription()));
            info.setCoverUrl(firstNonBlank(info.getCoverUrl(), normalizeEscapedUrl(stringValue(object.get("thumbnailUrl")), pageUrl)));
        }
        for (String key : List.of(
            "contentUrl", "embedUrl", "url", "videoUrl", "video_url",
            "playAddr", "play_api", "playUrl", "downloadAddr", "download_url",
            "m3u8Url", "m3u8_url", "dashUrl", "dash_url", "mp4Url", "mp4_url"
        )) {
            addVideoUrl(urls, normalizeEscapedUrl(stringValue(object.get(key)), pageUrl));
        }
        for (Map.Entry<String, JsonElement> entry : object.entrySet()) {
            collectFromJson(entry.getValue(), pageUrl, info, urls);
        }
    }

    private String stringValue(JsonElement value) {
        if (value == null || value.isJsonNull()) {
            return "";
        }
        if (value.isJsonPrimitive()) {
            return value.getAsString();
        }
        return "";
    }

    private String normalizeEscapedUrl(String value, String pageUrl) {
        if (value == null || value.isBlank()) {
            return "";
        }
        String normalized = value
            .replace("\\u002F", "/")
            .replace("\\u003A", ":")
            .replace("\\/", "/")
            .trim();
        if (normalized.isEmpty() || normalized.startsWith("data:") || normalized.startsWith("javascript:")) {
            return "";
        }
        if (normalized.startsWith("//")) {
            try {
                return java.net.URI.create(pageUrl).getScheme() + ":" + normalized;
            } catch (Exception ignored) {
                return "https:" + normalized;
            }
        }
        try {
            return java.net.URI.create(pageUrl).resolve(normalized).toString();
        } catch (Exception ignored) {
            return normalized;
        }
    }

    private void addVideoUrl(Set<String> urls, String value) {
        if (value != null && !value.isBlank()) {
            urls.add(value);
        }
    }

    private boolean isDirectMediaUrl(String url) {
        String lower = url.toLowerCase(Locale.ROOT);
        return lower.contains(".m3u8") || lower.contains(".mpd") || lower.contains(".mp4")
            || lower.contains(".webm") || lower.contains(".m4v") || lower.contains(".mov");
    }

    private String classifyMediaUrl(String url) {
        String lower = url.toLowerCase(Locale.ROOT);
        if (lower.contains(".m3u8")) {
            return "hls";
        }
        if (lower.contains(".mpd") || lower.contains("dash")) {
            return "dash";
        }
        if (lower.contains(".mp4") || lower.contains(".webm") || lower.contains(".m4v") || lower.contains(".mov")) {
            return "mp4";
        }
        return "download";
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (!isBlank(value)) {
                return value;
            }
        }
        return "";
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private String cleanText(String value) {
        return value == null ? "" : value.replaceAll("\\s+", " ").trim();
    }

    private int parseInteger(String value) {
        try {
            return value == null || value.isBlank() ? 0 : Integer.parseInt(value);
        } catch (NumberFormatException ignored) {
            return 0;
        }
    }

    private String fallbackTitle(String url) {
        try {
            URL parsed = new URL(url);
            String path = parsed.getPath();
            int lastSlash = path.lastIndexOf('/');
            if (lastSlash >= 0 && lastSlash + 1 < path.length()) {
                return path.substring(lastSlash + 1).replaceAll("\\.[^.]+$", "");
            }
        } catch (Exception ignored) {
        }
        return "Unknown";
    }

    private String extractVideoId(String url) {
        String[] patterns = {
            "/video/((?:BV|av)[A-Za-z0-9]+)",
            "/bangumi/play/(ep\\d+)",
            "/v_(\\w+)\\.html",
            "/x/(\\w+)\\.html",
            "/video/(\\d+)",
            "modal_id=(\\d+)"
        };
        for (String patternText : patterns) {
            Matcher matcher = Pattern.compile(patternText, Pattern.CASE_INSENSITIVE).matcher(url);
            if (matcher.find()) {
                return matcher.group(1);
            }
        }
        return "";
    }
}
