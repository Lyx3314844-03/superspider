package com.javaspider.media.parser;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.nio.charset.*;
import java.util.*;
import java.util.regex.*;

/**
 * YouTube 视频解析器 - 增强版
 * 支持提取视频信息、多格式 URL、标题、作者等
 */
public class YouTubeParser implements VideoParser {

    private static final String USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

    private final Map<String, String> headers;
    private int timeout;

    public YouTubeParser() {
        this.headers = new HashMap<>();
        this.headers.put("User-Agent", USER_AGENT);
        this.headers.put("Accept-Language", "en-US,en;q=0.9");
        this.timeout = 30000;
    }

    public YouTubeParser(int timeoutMs) {
        this();
        this.timeout = timeoutMs;
    }

    @Override
    public boolean supports(String url) {
        return url.contains("youtube.com") || url.contains("youtu.be");
    }

    @Override
    public VideoInfo parse(String url) throws Exception {
        System.out.println("Parsing YouTube video: " + url);

        // 提取视频 ID
        String videoId = extractVideoId(url);
        if (videoId == null) {
            throw new Exception("无法提取 YouTube 视频 ID: " + url);
        }

        // 获取页面 HTML
        String html = fetchPage(url);

        // 解析视频信息
        VideoInfo info = extractVideoInfo(html, url, videoId);

        if (info == null) {
            throw new Exception("无法解析视频信息");
        }

        return info;
    }

    /**
     * 从 HTML 提取视频信息
     */
    public VideoInfo extractVideoInfo(String html, String url, String videoId) {
        try {
            // 查找 ytInitialPlayerResponse
            JSONObject playerResponse = findPlayerResponse(html);
            if (playerResponse == null) {
                System.err.println("未找到 ytInitialPlayerResponse");
                return createBasicInfo(url, videoId);
            }

            VideoInfo info = new VideoInfo();
            info.setUrl(url);
            info.setPlatform("YouTube");
            info.setVideoId(videoId);

            // 提取视频详情
            JSONObject videoDetails = playerResponse.optJSONObject("videoDetails");
            if (videoDetails != null) {
                info.setTitle(videoDetails.optString("title", "Unknown"));
                info.setAuthor(videoDetails.optString("author", "Unknown"));
                info.setDuration(videoDetails.optInt("lengthSeconds", 0));
                info.setDescription(videoDetails.optString("shortDescription", ""));

                // 提取缩略图
                JSONObject thumbnail = videoDetails.optJSONObject("thumbnail");
                if (thumbnail != null) {
                    JSONArray thumbnails = thumbnail.optJSONArray("thumbnails");
                    if (thumbnails != null && thumbnails.length() > 0) {
                        JSONObject lastThumb = thumbnails.getJSONObject(thumbnails.length() - 1);
                        info.setCoverUrl(lastThumb.optString("url", ""));
                    }
                }
            }

            // 提取流媒体数据
            JSONObject streamingData = playerResponse.optJSONObject("streamingData");
            if (streamingData != null) {
                List<Map<String, Object>> formats = extractFormats(streamingData);
                info.setFormats(formats);

                // 设置最佳视频 URL
                for (Map<String, Object> fmt : formats) {
                    if ((Boolean) fmt.get("hasAudio") && (Boolean) fmt.get("hasVideo")) {
                        info.setVideoUrl((String) fmt.get("url"));
                        break;
                    }
                }
            }

            return info;

        } catch (Exception e) {
            System.err.println("解析视频信息失败：" + e.getMessage());
            return createBasicInfo(url, videoId);
        }
    }

    /**
     * 查找 ytInitialPlayerResponse JSON 数据
     */
    private JSONObject findPlayerResponse(String html) {
        String[] patterns = {
            "ytInitialPlayerResponse\\s*=\\s*\\{.+?\\};",
            "var\\s+ytInitialPlayerResponse\\s*=\\s*\\{.+?\\};"
        };

        for (String patternStr : patterns) {
            Pattern pattern = Pattern.compile(patternStr, Pattern.DOTALL);
            Matcher matcher = pattern.matcher(html);

            if (matcher.find()) {
                String jsonStr = matcher.group();
                // 提取 JSON 部分
                int start = jsonStr.indexOf('{');
                int end = jsonStr.lastIndexOf('}') + 1;

                if (start >= 0 && end > start) {
                    jsonStr = jsonStr.substring(start, end);
                    try {
                        return new JSONObject(jsonStr);
                    } catch (Exception e) {
                        System.err.println("JSON 解析失败：" + e.getMessage());
                    }
                }
            }
        }

        return null;
    }

    /**
     * 提取格式信息
     */
    private List<Map<String, Object>> extractFormats(JSONObject streamingData) {
        List<Map<String, Object>> formats = new ArrayList<>();

        try {
            // 提取普通格式
            JSONArray formatsArray = streamingData.optJSONArray("formats");
            if (formatsArray != null) {
                for (int i = 0; i < formatsArray.length(); i++) {
                    JSONObject fmt = formatsArray.getJSONObject(i);
                    formats.add(parseFormat(fmt));
                }
            }

            // 提取自适应格式
            JSONArray adaptiveFormats = streamingData.optJSONArray("adaptiveFormats");
            if (adaptiveFormats != null) {
                for (int i = 0; i < adaptiveFormats.length(); i++) {
                    JSONObject fmt = adaptiveFormats.getJSONObject(i);
                    formats.add(parseFormat(fmt));
                }
            }

        } catch (Exception e) {
            System.err.println("提取格式失败：" + e.getMessage());
        }

        return formats;
    }

    /**
     * 解析单个格式
     */
    private Map<String, Object> parseFormat(JSONObject fmt) {
        Map<String, Object> format = new HashMap<>();

        format.put("itag", fmt.optInt("itag", 0));
        format.put("mimeType", fmt.optString("mimeType", ""));
        format.put("quality", fmt.optString("quality", ""));
        format.put("width", fmt.optInt("width", 0));
        format.put("height", fmt.optInt("height", 0));
        format.put("bitrate", fmt.optInt("bitrate", 0));
        format.put("url", fmt.optString("url", ""));
        format.put("codecs", fmt.optString("codecs", ""));

        String mimeType = fmt.optString("mimeType", "");
        format.put("hasAudio", hasAudio(mimeType));
        format.put("hasVideo", hasVideo(mimeType));

        return format;
    }

    /**
     * 检查是否包含音频
     */
    private boolean hasAudio(String mimeType) {
        return mimeType.contains("mp4a") ||
               mimeType.contains("opus") ||
               mimeType.contains("ac-3") ||
               mimeType.contains("webma");
    }

    /**
     * 检查是否包含视频
     */
    private boolean hasVideo(String mimeType) {
        return mimeType.contains("video/") ||
               mimeType.contains("avc") ||
               mimeType.contains("vp9") ||
               mimeType.contains("vp8") ||
               mimeType.contains("hevc");
    }

    /**
     * 创建基本信息（当无法解析时）
     */
    private VideoInfo createBasicInfo(String url, String videoId) {
        VideoInfo info = new VideoInfo();
        info.setUrl(url);
        info.setPlatform("YouTube");
        info.setVideoId(videoId);
        info.setTitle(videoId);
        return info;
    }

    /**
     * 从 URL 提取视频 ID
     */
    private String extractVideoId(String url) {
        try {
            URI uri = new URI(url);
            String path = uri.getPath();
            String query = uri.getQuery();

            // youtu.be 短链接
            if (uri.getHost() != null && uri.getHost().contains("youtu.be")) {
                return path.substring(1);
            }

            // 标准链接
            if (query != null) {
                String[] params = query.split("&");
                for (String param : params) {
                    if (param.startsWith("v=")) {
                        return param.substring(2);
                    }
                }
            }

            // /embed/ 或 /v/ 格式
            if (path.contains("/embed/")) {
                String[] parts = path.split("/embed/");
                if (parts.length > 1) {
                    return parts[1].split("[/?]")[0];
                }
            }

            if (path.contains("/v/")) {
                String[] parts = path.split("/v/");
                if (parts.length > 1) {
                    return parts[1].split("[/?]")[0];
                }
            }

        } catch (Exception e) {
            // 使用正则备用方案
            String[] patterns = {
                "[?&]v=([a-zA-Z0-9_-]+)",
                "youtu\\.be/([a-zA-Z0-9_-]+)",
                "/embed/([a-zA-Z0-9_-]+)",
                "/v/([a-zA-Z0-9_-]+)"
            };

            for (String patternStr : patterns) {
                Pattern pattern = Pattern.compile(patternStr);
                Matcher matcher = pattern.matcher(url);
                if (matcher.find()) {
                    return matcher.group(1);
                }
            }
        }

        return null;
    }

    /**
     * 获取页面 HTML
     */
    private String fetchPage(String urlString) throws Exception {
        URL url = new URL(urlString);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();

        conn.setRequestMethod("GET");
        conn.setConnectTimeout(timeout);
        conn.setReadTimeout(timeout);

        // 设置请求头
        for (Map.Entry<String, String> entry : headers.entrySet()) {
            conn.setRequestProperty(entry.getKey(), entry.getValue());
        }

        int responseCode = conn.getResponseCode();
        if (responseCode != HttpURLConnection.HTTP_OK) {
            throw new Exception("HTTP 错误：" + responseCode);
        }

        BufferedReader reader = new BufferedReader(
            new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8)
        );

        StringBuilder html = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            html.append(line).append("\n");
        }
        reader.close();

        conn.disconnect();

        return html.toString();
    }

    /**
     * 获取最佳视频格式
     */
    public Map<String, Object> getBestFormat(VideoInfo info) {
        if (info.getFormats() == null || info.getFormats().isEmpty()) {
            return null;
        }

        // 选择最高清晰度的带音频视频
        Map<String, Object> best = null;
        int maxHeight = 0;

        for (Map<String, Object> fmt : info.getFormats()) {
            if ((Boolean) fmt.get("hasAudio") && (Boolean) fmt.get("hasVideo")) {
                int height = (Integer) fmt.get("height");
                if (height > maxHeight) {
                    maxHeight = height;
                    best = fmt;
                }
            }
        }

        return best;
    }

    /**
     * 按质量选择格式
     */
    public Map<String, Object> selectFormatByQuality(VideoInfo info, String quality) {
        if (info.getFormats() == null || info.getFormats().isEmpty()) {
            return null;
        }

        int targetHeight;
        switch (quality.toLowerCase()) {
            case "1080p": targetHeight = 1080; break;
            case "720p": targetHeight = 720; break;
            case "480p": targetHeight = 480; break;
            default: targetHeight = 0; // best
        }

        Map<String, Object> selected = null;

        for (Map<String, Object> fmt : info.getFormats()) {
            if ((Boolean) fmt.get("hasAudio") && (Boolean) fmt.get("hasVideo")) {
                int height = (Integer) fmt.get("height");

                if (targetHeight == 0) {
                    // best quality
                    if (selected == null || height > (Integer) selected.get("height")) {
                        selected = fmt;
                    }
                } else {
                    // specific quality
                    if (height >= targetHeight) {
                        if (selected == null || height < (Integer) selected.get("height")) {
                            selected = fmt;
                        }
                    }
                }
            }
        }

        return selected;
    }
}
