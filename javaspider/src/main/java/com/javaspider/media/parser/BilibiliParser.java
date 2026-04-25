package com.javaspider.media.parser;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class BilibiliParser implements VideoParser {
    private final GenericParser genericParser = new GenericParser();
    private static final String USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

    @Override
    public boolean supports(String url) {
        String lower = url.toLowerCase();
        return lower.contains("bilibili.com") || lower.contains("b23.tv");
    }

    @Override
    public VideoInfo parse(String url) throws Exception {
        String bvid = extractBvid(url);
        if (bvid.isBlank()) {
            VideoInfo info = genericParser.parse(url);
            info.setPlatform("Bilibili");
            return info;
        }

        try {
            VideoInfo info = parseViaApi(url, bvid);
            if (!info.getVideoUrls().isEmpty() || !info.getAudioUrls().isEmpty()) {
                return info;
            }
        } catch (Exception ignored) {
            // Fall back to HTML parsing when Bilibili blocks or changes an API response.
        }

        VideoInfo info = genericParser.parse(url);
        info.setPlatform("Bilibili");
        info.setVideoId(bvid);
        return info;
    }

    private VideoInfo parseViaApi(String pageUrl, String bvid) throws Exception {
        JsonObject view = fetchJson("https://api.bilibili.com/x/web-interface/view?bvid=" + bvid, pageUrl);
        if (view.get("code").getAsInt() != 0) {
            throw new IllegalStateException("view API returned " + view.get("code").getAsInt());
        }
        JsonObject data = view.getAsJsonObject("data");
        String cid = jsonString(data, "cid", "");

        VideoInfo info = new VideoInfo();
        info.setUrl(pageUrl);
        info.setPlatform("Bilibili");
        info.setVideoId(bvid);
        info.setTitle(jsonString(data, "title", bvid));
        info.setDescription(jsonString(data, "desc", ""));
        info.setCoverUrl(normalizeUrl(jsonString(data, "pic", "")));
        info.setDuration(jsonInt(data, "duration"));
        if (data.has("owner") && data.get("owner").isJsonObject()) {
            info.setAuthor(jsonString(data.getAsJsonObject("owner"), "name", ""));
        }

        if (!cid.isBlank()) {
            String playUrl = "https://api.bilibili.com/x/player/playurl?bvid=" + bvid
                + "&cid=" + cid + "&qn=80&fnval=16&fnver=0&fourk=1";
            JsonObject play = fetchJson(playUrl, pageUrl);
            if (play.get("code").getAsInt() == 0 && play.has("data")) {
                collectStreams(play.getAsJsonObject("data"), info);
            }
        }
        return info;
    }

    private void collectStreams(JsonObject data, VideoInfo info) {
        if (data.has("dash") && data.get("dash").isJsonObject()) {
            JsonObject dash = data.getAsJsonObject("dash");
            collectStreamArray(dash, "video", info.getVideoUrls());
            collectStreamArray(dash, "audio", info.getAudioUrls());
        }
        if (data.has("durl") && data.get("durl").isJsonArray()) {
            for (JsonElement item : data.getAsJsonArray("durl")) {
                if (item.isJsonObject()) {
                    String value = jsonString(item.getAsJsonObject(), "url", "");
                    if (!value.isBlank()) {
                        info.getVideoUrls().add(normalizeUrl(value));
                    }
                }
            }
        }
        if (!info.getVideoUrls().isEmpty()) {
            info.setVideoUrl(info.getVideoUrls().get(0));
        }
    }

    private void collectStreamArray(JsonObject dash, String key, java.util.List<String> target) {
        if (!dash.has(key) || !dash.get(key).isJsonArray()) {
            return;
        }
        JsonArray streams = dash.getAsJsonArray(key);
        for (JsonElement stream : streams) {
            if (!stream.isJsonObject()) {
                continue;
            }
            JsonObject object = stream.getAsJsonObject();
            String value = firstNonBlank(
                jsonString(object, "baseUrl", ""),
                jsonString(object, "base_url", "")
            );
            if (!value.isBlank()) {
                target.add(normalizeUrl(value));
            }
        }
    }

    private JsonObject fetchJson(String apiUrl, String referer) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) new URL(apiUrl).openConnection();
        conn.setRequestMethod("GET");
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(15000);
        conn.setRequestProperty("User-Agent", USER_AGENT);
        conn.setRequestProperty("Referer", referer);
        conn.setRequestProperty("Accept", "application/json, text/plain, */*");
        try (InputStreamReader reader = new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8)) {
            return JsonParser.parseReader(reader).getAsJsonObject();
        } finally {
            conn.disconnect();
        }
    }

    private String extractBvid(String url) {
        Matcher matcher = Pattern.compile("(BV[A-Za-z0-9]+)").matcher(url);
        return matcher.find() ? matcher.group(1) : "";
    }

    private String jsonString(JsonObject object, String key, String fallback) {
        if (object == null || !object.has(key) || object.get(key).isJsonNull()) {
            return fallback;
        }
        try {
            return object.get(key).getAsString();
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private int jsonInt(JsonObject object, String key) {
        if (object == null || !object.has(key) || object.get(key).isJsonNull()) {
            return 0;
        }
        try {
            return object.get(key).getAsInt();
        } catch (Exception ignored) {
            return 0;
        }
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return "";
    }

    private String normalizeUrl(String value) {
        if (value == null) {
            return "";
        }
        String normalized = value
            .replace("\\u002F", "/")
            .replace("\\u003A", ":")
            .replace("\\/", "/")
            .trim();
        if (normalized.startsWith("//")) {
            return "https:" + normalized;
        }
        return normalized;
    }
}
