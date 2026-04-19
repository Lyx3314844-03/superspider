package com.javaspider.media.parser;

import com.javaspider.media.drm.DRMChecker;
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

        if (isDirectMediaUrl(url) || isDirectAudioUrl(url)) {
            info.setTitle(fallbackTitle(url));
            info.setVideoId(extractVideoId(url));
            if (isDirectAudioUrl(url)) {
                info.getAudioUrls().add(url);
            } else {
                info.setVideoUrl(url);
                info.getVideoUrls().add(url);
            }
            addMediaFormats(info, info.getVideoUrls(), info.getAudioUrls());
            applyDrmSignals(info, "", List.of(), info.getVideoUrls(), info.getAudioUrls());
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
        LinkedHashSet<String> audioUrls = new LinkedHashSet<>(info.getAudioUrls());
        for (String artifactText : artifactTexts) {
            if (artifactText == null || artifactText.isBlank()) {
                continue;
            }
            Matcher matcher = Pattern.compile(
                "(https?://[^\"'\\s<>]+(?:\\.m3u8|\\.mpd|\\.mp4|\\.webm|\\.m4v|\\.mov|\\.m4s)[^\"'\\s<>]*)",
                Pattern.CASE_INSENSITIVE
            ).matcher(artifactText);
            while (matcher.find()) {
                addVideoUrl(videoUrls, normalizeEscapedUrl(matcher.group(1), pageUrl));
            }
            Matcher audioMatcher = Pattern.compile(
                "(https?://[^\"'\\s<>]+(?:\\.mp3|\\.m4a|\\.aac|\\.flac|\\.ogg|\\.wav)[^\"'\\s<>]*)",
                Pattern.CASE_INSENSITIVE
            ).matcher(artifactText);
            while (audioMatcher.find()) {
                addAudioUrl(audioUrls, normalizeEscapedUrl(audioMatcher.group(1), pageUrl));
            }
            try {
                JsonElement payload = JsonParser.parseString(artifactText.trim());
                collectFromJson(payload, pageUrl, info, videoUrls, audioUrls);
            } catch (Exception ignored) {
                // best-effort artifact parsing
            }
        }

        finalizeMediaInfo(info, html, artifactTexts, videoUrls, audioUrls);
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
            normalizeEscapedUrl(firstMatch(html,
                "\"(?:cover|pic|poster|thumbnailUrl|dynamic_cover|originCover)\"\\s*:\\s*\"([^\"]+)\""
            ), url),
            cleanText(info.getCoverUrl())
        ));
        info.setVideoId(firstNonBlank(info.getVideoId(), extractVideoId(url)));
        if (info.getDuration() <= 0) {
            info.setDuration(parseInteger(firstMatch(html, "\"duration\"\\s*:\\s*(\\d+)")));
        }

        LinkedHashSet<String> videoUrls = new LinkedHashSet<>(info.getVideoUrls());
        LinkedHashSet<String> audioUrls = new LinkedHashSet<>(info.getAudioUrls());
        for (Element element : document.select("meta[property=og:video], meta[property=og:video:url], meta[name=twitter:player:stream]")) {
            addVideoUrl(videoUrls, normalizeEscapedUrl(element.attr("content"), url));
        }
        for (Element element : document.select("video[src], source[src]")) {
            addVideoUrl(videoUrls, normalizeEscapedUrl(element.attr("src"), url));
        }
        for (Element element : document.select("audio[src], audio source[src]")) {
            addAudioUrl(audioUrls, normalizeEscapedUrl(element.attr("src"), url));
        }

        Matcher matcher = Pattern.compile(
            "(https?://[^\"'\\s<>]+(?:\\.m3u8|\\.mpd|\\.mp4|\\.webm|\\.m4v|\\.mov|\\.m4s)[^\"'\\s<>]*)",
            Pattern.CASE_INSENSITIVE
        ).matcher(html);
        while (matcher.find()) {
            addVideoUrl(videoUrls, normalizeEscapedUrl(matcher.group(1), url));
        }
        Matcher audioMatcher = Pattern.compile(
            "(https?://[^\"'\\s<>]+(?:\\.mp3|\\.m4a|\\.aac|\\.flac|\\.ogg|\\.wav)[^\"'\\s<>]*)",
            Pattern.CASE_INSENSITIVE
        ).matcher(html);
        while (audioMatcher.find()) {
            addAudioUrl(audioUrls, normalizeEscapedUrl(audioMatcher.group(1), url));
        }

        Matcher ldJson = Pattern.compile(
            "(?is)<script[^>]+type=[\"']application/ld\\+json[\"'][^>]*>(.*?)</script>"
        ).matcher(html);
        while (ldJson.find()) {
            try {
                JsonElement payload = JsonParser.parseString(ldJson.group(1).trim());
                collectFromJson(payload, url, info, videoUrls, audioUrls);
            } catch (Exception ignored) {
                // best-effort
            }
        }

        finalizeMediaInfo(info, html, List.of(), videoUrls, audioUrls);
        return info;
    }

    private String detectPlatform(String url) {
        String lower = url.toLowerCase(Locale.ROOT);
        if (lower.contains("youtube.com") || lower.contains("youtu.be")) {
            return "YouTube";
        }
        if (lower.contains("youku.com") || lower.contains("youku.tv") || lower.contains("youku")) {
            return "Youku";
        }
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

    private void collectFromJson(JsonElement value, String pageUrl, VideoInfo info, Set<String> urls, Set<String> audioUrls) {
        if (value == null || value.isJsonNull()) {
            return;
        }
        if (value.isJsonArray()) {
            for (JsonElement item : value.getAsJsonArray()) {
                collectFromJson(item, pageUrl, info, urls, audioUrls);
            }
            return;
        }
        if (!value.isJsonObject()) {
            return;
        }
        var object = value.getAsJsonObject();
        if (object.has("@type") && "VideoObject".equalsIgnoreCase(cleanText(stringValue(object.get("@type"))))) {
            info.setTitle(firstNonBlank(cleanText(stringValue(object.get("name"))), cleanText(stringValue(object.get("headline"))), info.getTitle()));
            info.setDescription(firstNonBlank(
                cleanText(stringValue(object.get("description"))),
                cleanText(stringValue(object.get("desc"))),
                info.getDescription()
            ));
            info.setCoverUrl(firstNonBlank(
                info.getCoverUrl(),
                normalizeEscapedUrl(stringValue(object.get("thumbnailUrl")), pageUrl),
                normalizeEscapedUrl(stringValue(object.get("cover")), pageUrl),
                normalizeEscapedUrl(stringValue(object.get("pic")), pageUrl),
                normalizeEscapedUrl(stringValue(object.get("poster")), pageUrl),
                normalizeEscapedUrl(stringValue(object.get("dynamic_cover")), pageUrl),
                normalizeEscapedUrl(stringValue(object.get("originCover")), pageUrl)
            ));
        }
        info.setDescription(firstNonBlank(
            info.getDescription(),
            cleanText(stringValue(object.get("description"))),
            cleanText(stringValue(object.get("desc")))
        ));
        info.setCoverUrl(firstNonBlank(
            info.getCoverUrl(),
            normalizeEscapedUrl(stringValue(object.get("thumbnailUrl")), pageUrl),
            normalizeEscapedUrl(stringValue(object.get("cover")), pageUrl),
            normalizeEscapedUrl(stringValue(object.get("pic")), pageUrl),
            normalizeEscapedUrl(stringValue(object.get("poster")), pageUrl),
            normalizeEscapedUrl(stringValue(object.get("dynamic_cover")), pageUrl),
            normalizeEscapedUrl(stringValue(object.get("originCover")), pageUrl)
        ));
        for (String key : List.of(
            "contentUrl", "embedUrl", "url", "videoUrl", "video_url",
            "playAddr", "play_api", "playUrl", "downloadAddr", "download_url",
            "m3u8Url", "m3u8_url", "dashUrl", "dash_url", "mp4Url", "mp4_url",
            "baseUrl", "base_url"
        )) {
            addVideoUrl(urls, normalizeEscapedUrl(stringValue(object.get(key)), pageUrl));
        }
        for (String key : List.of(
            "audioUrl", "audio_url", "audioPlayUrl", "audio_play_url",
            "audioBaseUrl", "audio_base_url", "audioDownloadUrl", "audio_download_url"
        )) {
            addAudioUrl(audioUrls, normalizeEscapedUrl(stringValue(object.get(key)), pageUrl));
        }
        for (Map.Entry<String, JsonElement> entry : object.entrySet()) {
            collectFromJson(entry.getValue(), pageUrl, info, urls, audioUrls);
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

    private void addAudioUrl(Set<String> urls, String value) {
        if (value != null && !value.isBlank()) {
            urls.add(value);
        }
    }

    private boolean isDirectMediaUrl(String url) {
        String lower = url.toLowerCase(Locale.ROOT);
        return lower.contains(".m3u8") || lower.contains(".mpd") || lower.contains(".mp4")
            || lower.contains(".webm") || lower.contains(".m4v") || lower.contains(".mov")
            || lower.contains(".m4s");
    }

    private boolean isDirectAudioUrl(String url) {
        String lower = url.toLowerCase(Locale.ROOT);
        return lower.contains(".mp3") || lower.contains(".m4a") || lower.contains(".aac")
            || lower.contains(".flac") || lower.contains(".ogg") || lower.contains(".wav");
    }

    private String classifyMediaUrl(String url) {
        String lower = url.toLowerCase(Locale.ROOT);
        if (lower.contains(".m3u8")) {
            return "hls";
        }
        if (lower.contains(".mpd") || lower.contains("dash")) {
            return "dash";
        }
        if (lower.contains(".mp4") || lower.contains(".webm") || lower.contains(".m4v") || lower.contains(".mov") || lower.contains(".m4s")) {
            return "mp4";
        }
        if (isDirectAudioUrl(url)) {
            return "audio";
        }
        return "download";
    }

    private void addMediaFormats(VideoInfo info, Collection<String> videoUrls, Collection<String> audioUrls) {
        info.getFormats().clear();
        for (String videoUrl : videoUrls) {
            info.getFormats().add(Map.of("kind", classifyMediaUrl(videoUrl), "url", videoUrl));
        }
        for (String audioUrl : audioUrls) {
            info.getFormats().add(Map.of("kind", "audio", "url", audioUrl));
        }
    }

    private void finalizeMediaInfo(
        VideoInfo info,
        String html,
        Collection<String> artifactTexts,
        Collection<String> videoUrls,
        Collection<String> audioUrls
    ) {
        info.getVideoUrls().clear();
        info.getVideoUrls().addAll(videoUrls);
        info.getAudioUrls().clear();
        info.getAudioUrls().addAll(audioUrls);
        if (!info.getVideoUrls().isEmpty()) {
            info.setVideoUrl(info.getVideoUrls().get(0));
        } else if (!info.getAudioUrls().isEmpty()) {
            info.setVideoUrl(info.getAudioUrls().get(0));
        }
        addMediaFormats(info, videoUrls, audioUrls);
        applyDrmSignals(info, html, artifactTexts, videoUrls, audioUrls);
    }

    private void applyDrmSignals(
        VideoInfo info,
        String html,
        Collection<String> artifactTexts,
        Collection<String> videoUrls,
        Collection<String> audioUrls
    ) {
        DRMChecker checker = new DRMChecker();
        boolean drmProtected = false;
        if (html != null && !html.isBlank()) {
            drmProtected = checker.checkFromHTML(html).isProtected();
        }
        for (String artifactText : artifactTexts) {
            if (artifactText == null || artifactText.isBlank()) {
                continue;
            }
            if (artifactText.contains("#EXTM3U")) {
                drmProtected = drmProtected || checker.checkFromM3U8(artifactText).isProtected();
            } else if (artifactText.contains("<ContentProtection") || artifactText.contains("<MPD")) {
                drmProtected = drmProtected || checker.checkFromMPD(artifactText).isProtected();
            } else {
                drmProtected = drmProtected || checker.checkFromHTML(artifactText).isProtected();
            }
        }
        for (String url : videoUrls) {
            drmProtected = drmProtected || checker.checkFromURL(url).isProtected();
        }
        for (String url : audioUrls) {
            drmProtected = drmProtected || checker.checkFromURL(url).isProtected();
        }
        info.setDRMProtected(drmProtected);
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
            "[?&]v=([A-Za-z0-9_-]+)",
            "youtu\\.be/([A-Za-z0-9_-]+)",
            "id_([A-Za-z0-9=]+)",
            "/video/((?:BV|av)[A-Za-z0-9]+)",
            "/bangumi/play/(ep\\d+)",
            "/v_(\\w+)\\.html",
            "/play/(\\w+)",
            "[?&]curid=([^&]+)",
            "/x/cover/[^/]+/([A-Za-z0-9]+)\\.html",
            "/x/page/([A-Za-z0-9]+)\\.html",
            "/x/(\\w+)\\.html",
            "[?&]vid=([A-Za-z0-9]+)",
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
