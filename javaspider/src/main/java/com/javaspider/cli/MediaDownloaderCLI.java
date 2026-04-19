package com.javaspider.cli;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javaspider.media.*;
import com.javaspider.media.drm.DRMChecker;
import com.javaspider.media.parser.*;
import com.javaspider.media.ffmpeg.FFmpegProcessor;

import java.io.*;
import java.util.*;

/**
 * 媒体下载命令行工具
 */
public class MediaDownloaderCLI {
    
    private static final String VERSION = "1.0.0";
    static final String FFMPEG_PATH_PROPERTY = "javaspider.ffmpeg.path";
    
    public static void main(String[] args) {
        if (args.length == 0) {
            printHelp();
            return;
        }
        
        String command = args[0];
        
        switch (command) {
            case "download":
                handleDownload(Arrays.copyOfRange(args, 1, args.length));
                break;
            case "info":
                handleInfo(Arrays.copyOfRange(args, 1, args.length));
                break;
            case "artifact":
                handleArtifact(Arrays.copyOfRange(args, 1, args.length));
                break;
            case "drm":
                handleDrm(Arrays.copyOfRange(args, 1, args.length));
                break;
            case "convert":
                handleConvert(Arrays.copyOfRange(args, 1, args.length));
                break;
            case "merge":
                handleMerge(Arrays.copyOfRange(args, 1, args.length));
                break;
            case "doctor":
                handleDoctor(Arrays.copyOfRange(args, 1, args.length));
                break;
            case "version":
                System.out.println("MediaDownloader CLI v" + VERSION);
                break;
            case "help":
            case "--help":
            case "-h":
                printHelp();
                break;
            default:
                System.out.println("Unknown command: " + command);
                printHelp();
        }
    }
    
    /**
     * 处理下载命令
     */
    private static void handleDownload(String[] args) {
        if (args.length < 1) {
            System.out.println("Error: URL required");
            System.out.println("Usage: download <url> [options]");
            return;
        }
        
        String url = args[0];
        String outputDir = "./downloads";
        String quality = "best";
        boolean audioOnly = false;
        String htmlFile = "";
        String networkFile = "";
        String harFile = "";
        String artifactDir = "";
        
        // 解析选项
        for (int i = 1; i < args.length; i++) {
            switch (args[i]) {
                case "-o":
                case "--output":
                    if (i + 1 < args.length) {
                        outputDir = args[++i];
                    }
                    break;
                case "-q":
                case "--quality":
                    if (i + 1 < args.length) {
                        quality = args[++i];
                    }
                    break;
                case "-a":
                case "--audio-only":
                    audioOnly = true;
                    break;
                case "--html-file":
                    if (i + 1 < args.length) {
                        htmlFile = args[++i];
                    }
                    break;
                case "--network-file":
                    if (i + 1 < args.length) {
                        networkFile = args[++i];
                    }
                    break;
                case "--har-file":
                    if (i + 1 < args.length) {
                        harFile = args[++i];
                    }
                    break;
                case "--artifact-dir":
                    if (i + 1 < args.length) {
                        artifactDir = args[++i];
                    }
                    break;
            }
        }

        String[] artifacts = resolveArtifactBundle(artifactDir, htmlFile, networkFile, harFile);
        htmlFile = artifacts[0];
        networkFile = artifacts[1];
        harFile = artifacts[2];
        
        System.out.println("========== Media Downloader ==========");
        System.out.println("URL: " + url);
        System.out.println("Output: " + outputDir);
        System.out.println("Quality: " + quality);
        System.out.println("Audio only: " + audioOnly);
        System.out.println();
        
        try {
            // 1. 解析视频
            VideoInfo info = (!htmlFile.isBlank() || !networkFile.isBlank() || !harFile.isBlank())
                ? parseVideoArtifacts(url, htmlFile, networkFile, harFile)
                : parseVideoInfo(url, true);
            System.out.println("Title: " + info.getTitle());
            System.out.println("Platform: " + info.getPlatform());
            if (info.isDRMProtected()) {
                System.out.println("Warning: DRM protection detected; download may require license handling.");
            }
            System.out.println();
            if (audioOnly) {
                if (downloadAudioOnly(info, url, outputDir, quality)) {
                    System.out.println("\nDownload completed!");
                }
                return;
            }
            String mediaUrl = resolveMediaUrl(info, url);
            
            // 2. 下载
            String outputFile = downloadResolvedAsset(info, mediaUrl, outputDir, quality, MediaType.VIDEO);
            System.out.println("Downloaded: " + outputFile);
            
            System.out.println("\nDownload completed!");
            
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    /**
     * 处理信息命令
     */
    private static void handleInfo(String[] args) {
        if (args.length < 1) {
            System.out.println("Error: URL required");
            return;
        }

        String url = args[0];
        String htmlFile = "";
        String networkFile = "";
        String harFile = "";
        String artifactDir = "";

        for (int i = 1; i < args.length; i++) {
            switch (args[i]) {
                case "--html-file" -> {
                    if (i + 1 < args.length) {
                        htmlFile = args[++i];
                    }
                }
                case "--network-file" -> {
                    if (i + 1 < args.length) {
                        networkFile = args[++i];
                    }
                }
                case "--har-file" -> {
                    if (i + 1 < args.length) {
                        harFile = args[++i];
                    }
                }
                case "--artifact-dir" -> {
                    if (i + 1 < args.length) {
                        artifactDir = args[++i];
                    }
                }
                default -> {
                    // keep compatibility with the positional URL-only surface
                }
            }
        }

        String[] artifacts = resolveArtifactBundle(artifactDir, htmlFile, networkFile, harFile);
        htmlFile = artifacts[0];
        networkFile = artifacts[1];
        harFile = artifacts[2];

        try {
            VideoInfo info = (!htmlFile.isBlank() || !networkFile.isBlank() || !harFile.isBlank())
                ? parseVideoArtifacts(url, htmlFile, networkFile, harFile)
                : parseVideoInfo(url, false);
            String displayTitle = fallbackVideoTitle(url, info.getTitle());

            System.out.println("========== Video Info ==========");
            System.out.println("Title: " + displayTitle);
            System.out.println("Platform: " + info.getPlatform());
            System.out.println("Duration: " + info.getDuration() + "s");
            System.out.println("Views: " + info.getViewCount());
            System.out.println("Description: " + info.getDescription());
            System.out.println("Audio tracks: " + info.getAudioUrls().size());
            System.out.println("DRM protected: " + info.isDRMProtected());
            System.out.println("================================");

        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            // 输出基本信息作为后备
            if (url.contains("youtube.com") || url.contains("youtu.be")) {
                System.out.println("Platform: YouTube");
                System.out.println("Title: " + fallbackVideoTitle(url, null));
            }
        }
    }

    private static void handleDrm(String[] args) {
        String url = "";
        String inlineContent = "";
        String htmlFile = "";
        String m3u8File = "";
        String mpdFile = "";

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--url" -> {
                    if (i + 1 < args.length) {
                        url = args[++i];
                    }
                }
                case "--content" -> {
                    if (i + 1 < args.length) {
                        inlineContent = args[++i];
                    }
                }
                case "--html-file" -> {
                    if (i + 1 < args.length) {
                        htmlFile = args[++i];
                    }
                }
                case "--m3u8-file" -> {
                    if (i + 1 < args.length) {
                        m3u8File = args[++i];
                    }
                }
                case "--mpd-file" -> {
                    if (i + 1 < args.length) {
                        mpdFile = args[++i];
                    }
                }
                default -> {
                    // keep the lightweight CLI permissive
                }
            }
        }

        DRMChecker checker = new DRMChecker();
        DRMChecker.DRMResult result;
        String source = "url";

        try {
            if (!m3u8File.isBlank()) {
                result = checker.checkFromM3U8(java.nio.file.Files.readString(java.nio.file.Path.of(m3u8File)));
                source = "m3u8";
            } else if (!mpdFile.isBlank()) {
                result = checker.checkFromMPD(java.nio.file.Files.readString(java.nio.file.Path.of(mpdFile)));
                source = "mpd";
            } else if (!htmlFile.isBlank()) {
                result = checker.checkFromHTML(java.nio.file.Files.readString(java.nio.file.Path.of(htmlFile)));
                source = "html";
            } else if (!inlineContent.isBlank()) {
                if (inlineContent.contains("#EXTM3U")) {
                    result = checker.checkFromM3U8(inlineContent);
                    source = "m3u8";
                } else if (inlineContent.contains("<ContentProtection") || inlineContent.contains("<MPD")) {
                    result = checker.checkFromMPD(inlineContent);
                    source = "mpd";
                } else {
                    result = checker.checkFromHTML(inlineContent);
                    source = "html";
                }
            } else if (!url.isBlank()) {
                result = checker.checkFromURL(url);
            } else {
                System.out.println("drm requires --url, --content, --html-file, --m3u8-file, or --mpd-file");
                return;
            }

            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("command", "drm");
            payload.put("runtime", "java");
            payload.put("source", source);
            payload.put("url", url);
            payload.put("protected", result.isProtected());
            payload.put("drm_type", result.getDrmType().name());
            payload.put("license_url", result.getLicenseUrl() == null ? "" : result.getLicenseUrl());
            payload.put("detected_systems", result.getDetectedSystems());
            ObjectMapper mapper = new ObjectMapper();
            System.out.println(mapper.writeValueAsString(payload));
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
        }
    }

    private static String fallbackVideoTitle(String url, String currentTitle) {
        if (currentTitle != null && !currentTitle.isBlank() && !"null".equalsIgnoreCase(currentTitle)) {
            return currentTitle;
        }

        String videoId = url;
        String shortPrefix = "youtu.be/";
        if (url.contains("v=")) {
            videoId = url.substring(url.indexOf("v=") + 2);
            if (videoId.contains("&")) {
                videoId = videoId.substring(0, videoId.indexOf("&"));
            }
        } else if (url.contains(shortPrefix)) {
            videoId = url.substring(url.indexOf(shortPrefix) + shortPrefix.length());
            if (videoId.contains("?")) {
                videoId = videoId.substring(0, videoId.indexOf("?"));
            }
        }
        return videoId;
    }

    static VideoInfo parseVideoInfo(String url, boolean requireMedia) throws Exception {
        VideoParser primary = getParser(url);
        VideoInfo candidate = null;
        Exception primaryFailure = null;

        if (primary != null) {
            try {
                candidate = primary.parse(url);
                if (candidate != null && (!requireMedia || hasMediaCandidate(candidate))) {
                    return candidate;
                }
            } catch (Exception e) {
                primaryFailure = e;
            }
        }

        if (!(primary instanceof GenericParser)) {
            try {
                VideoInfo fallback = new GenericParser().parse(url);
                if (fallback != null && (!requireMedia || hasMediaCandidate(fallback))) {
                    return fallback;
                }
                if (fallback != null && candidate == null) {
                    candidate = fallback;
                }
            } catch (Exception e) {
                if (primaryFailure == null) {
                    primaryFailure = e;
                }
            }
        }

        if (candidate != null && !requireMedia) {
            return candidate;
        }
        if (primaryFailure != null) {
            throw primaryFailure;
        }
        throw new IllegalStateException(requireMedia ? "Unable to resolve downloadable media URL" : "Unsupported platform");
    }

    private static boolean hasMediaCandidate(VideoInfo info) {
        if (info == null) {
            return false;
        }
        if (info.getVideoUrl() != null && !info.getVideoUrl().isBlank()) {
            return true;
        }
        if (info.getVideoUrls() != null) {
            for (String value : info.getVideoUrls()) {
                if (value != null && !value.isBlank()) {
                    return true;
                }
            }
        }
        if (info.getAudioUrls() != null) {
            for (String value : info.getAudioUrls()) {
                if (value != null && !value.isBlank()) {
                    return true;
                }
            }
        }
        return false;
    }

    private static void handleArtifact(String[] args) {
        String url = "https://example.com/";
        String artifactDir = "";
        String htmlFile = "";
        String networkFile = "";
        String harFile = "";
        String outputDir = "./downloads";
        boolean download = false;

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--url" -> {
                    if (i + 1 < args.length) {
                        url = args[++i];
                    }
                }
                case "--artifact-dir" -> {
                    if (i + 1 < args.length) {
                        artifactDir = args[++i];
                    }
                }
                case "--html-file" -> {
                    if (i + 1 < args.length) {
                        htmlFile = args[++i];
                    }
                }
                case "--network-file" -> {
                    if (i + 1 < args.length) {
                        networkFile = args[++i];
                    }
                }
                case "--har-file" -> {
                    if (i + 1 < args.length) {
                        harFile = args[++i];
                    }
                }
                case "--output", "-o" -> {
                    if (i + 1 < args.length) {
                        outputDir = args[++i];
                    }
                }
                case "--download" -> download = true;
                default -> {
                    // ignore unknown here for parity with the lightweight media surface
                }
            }
        }

        String[] artifacts = resolveArtifactBundle(artifactDir, htmlFile, networkFile, harFile);
        htmlFile = artifacts[0];
        networkFile = artifacts[1];
        harFile = artifacts[2];

        if (artifactDir.isBlank() && htmlFile.isBlank() && networkFile.isBlank() && harFile.isBlank()) {
            System.out.println("artifact requires --artifact-dir or explicit artifact files");
            return;
        }

        try {
            VideoInfo info = parseVideoArtifacts(url, htmlFile, networkFile, harFile);
            Map<String, Object> videoPayload = new LinkedHashMap<>();
            videoPayload.put("title", info.getTitle());
            videoPayload.put("platform", info.getPlatform());
            videoPayload.put("video_id", info.getVideoId());
            videoPayload.put("description", info.getDescription());
            videoPayload.put("cover_url", info.getCoverUrl());
            videoPayload.put("video_url", info.getVideoUrl());
            videoPayload.put("video_urls", info.getVideoUrls());
            videoPayload.put("audio_urls", info.getAudioUrls());
            videoPayload.put("drm_protected", info.isDRMProtected());
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("command", "media artifact");
            payload.put("runtime", "java");
            payload.put("url", url);
            payload.put("artifact_dir", artifactDir);
            payload.put("html_file", htmlFile);
            payload.put("network_file", networkFile);
            payload.put("har_file", harFile);
            payload.put("video", videoPayload);
            payload.put("download", Map.of(
                "requested", download,
                "output", ""
            ));

            if (download) {
                String mediaUrl = resolveMediaUrl(info, url);
                if (mediaUrl.contains(".m3u8")) {
                    HLSDownloader hls = new HLSDownloader(outputDir);
                    HLSDownloader.DownloadResult result = hls.download(mediaUrl, info.getTitle() + ".ts");
                    payload.put("download", Map.of("requested", true, "output", result.outputFile));
                } else if (mediaUrl.contains(".mpd")) {
                    DASHDownloader dash = new DASHDownloader(outputDir);
                    DASHDownloader.DownloadResult result = dash.download(mediaUrl, "best");
                    payload.put("download", Map.of("requested", true, "output", result.outputFile));
                } else {
                    AdvancedMediaDownloader downloader = new AdvancedMediaDownloader(outputDir);
                    MediaItem item = new MediaItem(info.getTitle(), mediaUrl, MediaType.VIDEO);
                    item.setDownloadUrl(mediaUrl);
                    String output = downloader.downloadWithResume(item);
                    payload.put("download", Map.of("requested", true, "output", output));
                }
            }

            ObjectMapper mapper = new ObjectMapper();
            System.out.println(mapper.writerWithDefaultPrettyPrinter().writeValueAsString(payload));
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
        }
    }

    private static VideoInfo parseVideoArtifacts(String url, String htmlFile, String networkFile, String harFile) throws IOException {
        GenericParser parser = new GenericParser();
        String html = htmlFile.isBlank() ? "" : java.nio.file.Files.readString(java.nio.file.Path.of(htmlFile));
        List<String> artifacts = new ArrayList<>();
        if (!networkFile.isBlank()) {
            artifacts.add(java.nio.file.Files.readString(java.nio.file.Path.of(networkFile)));
        }
        if (!harFile.isBlank()) {
            artifacts.add(java.nio.file.Files.readString(java.nio.file.Path.of(harFile)));
        }
        return parser.parseArtifacts(url, html, artifacts);
    }

    private static String[] resolveArtifactBundle(String artifactDir, String htmlFile, String networkFile, String harFile) {
        htmlFile = discoverArtifactPath(
            artifactDir,
            htmlFile,
            List.of("page.html", "content.html", "document.html", "browser.html", "response.html", "index.html"),
            List.of("*page*.html", "*content*.html", "*.html")
        );
        networkFile = discoverArtifactPath(
            artifactDir,
            networkFile,
            List.of("network.json", "requests.json", "trace.json", "network.log", "network.txt"),
            List.of("*network*.json", "*request*.json", "*trace*.json", "*network*.txt")
        );
        harFile = discoverArtifactPath(
            artifactDir,
            harFile,
            List.of("trace.har", "network.har", "session.har", "browser.har", "page.har"),
            List.of("*.har")
        );
        return new String[]{htmlFile, networkFile, harFile};
    }

    private static boolean downloadAudioOnly(VideoInfo info, String originalUrl, String outputDir, String quality) throws Exception {
        String audioUrl = resolveAudioUrl(info);
        if (audioUrl != null && !audioUrl.isBlank()) {
            String outputFile = downloadResolvedAsset(info, audioUrl, outputDir, quality, MediaType.AUDIO);
            System.out.println("Downloaded audio: " + outputFile);
            return true;
        }

        FFmpegProcessor ffmpeg = createFFmpegProcessor();
        DependencyCheck ffmpegCheck = checkFFmpeg(ffmpeg);
        if (!ffmpegCheck.available()) {
            System.out.println("FFmpeg dependency check failed for audio-only.");
            System.out.println(ffmpegCheck.message());
            return false;
        }

        String mediaUrl = resolveMediaUrl(info, originalUrl);
        String downloaded = downloadResolvedAsset(info, mediaUrl, outputDir, quality, MediaType.VIDEO);
        String audioOutput = buildAudioOutputPath(outputDir, defaultMediaTitle(info, originalUrl));
        String extracted = ffmpeg.extractAudio(downloaded, audioOutput);
        System.out.println("Downloaded source: " + downloaded);
        System.out.println("Extracted audio: " + extracted);
        return true;
    }

    private static String downloadResolvedAsset(VideoInfo info, String mediaUrl, String outputDir, String quality, MediaType mediaType) throws Exception {
        if (mediaUrl == null || mediaUrl.isBlank()) {
            throw new IllegalStateException("Unable to resolve downloadable media URL");
        }
        String title = defaultMediaTitle(info, mediaUrl);
        if (mediaUrl.contains(".m3u8")) {
            HLSDownloader hls = new HLSDownloader(outputDir);
            HLSDownloader.DownloadResult result = hls.download(mediaUrl, sanitizeFileName(title) + ".ts");
            return result.outputFile;
        }
        if (mediaUrl.contains(".mpd")) {
            DASHDownloader dash = new DASHDownloader(outputDir);
            DASHDownloader.DownloadResult result = dash.download(mediaUrl, quality);
            return result.outputFile;
        }

        AdvancedMediaDownloader downloader = new AdvancedMediaDownloader(outputDir);
        MediaItem item = new MediaItem(title, mediaUrl, mediaType);
        item.setDownloadUrl(mediaUrl);
        return downloader.downloadWithResume(item);
    }

    private static String discoverArtifactPath(String artifactDir, String currentValue, List<String> candidates, List<String> patterns) {
        if (currentValue != null && !currentValue.isBlank()) {
            return currentValue;
        }
        if (artifactDir == null || artifactDir.isBlank()) {
            return "";
        }
        File root = new File(artifactDir);
        if (!root.isDirectory()) {
            return "";
        }
        for (String candidate : candidates) {
            File file = new File(root, candidate);
            if (file.isFile()) {
                return file.getPath();
            }
        }
        for (String pattern : patterns) {
            File[] matches = root.listFiles((dir, name) -> {
                String regex = pattern.replace(".", "\\.").replace("*", ".*");
                return name.matches(regex);
            });
            if (matches != null) {
                Arrays.sort(matches, Comparator.comparing(File::getName));
                for (File file : matches) {
                    if (file.isFile()) {
                        return file.getPath();
                    }
                }
            }
        }
        return "";
    }

    private static String resolveMediaUrl(VideoInfo info, String originalUrl) {
        if (info != null) {
            if (info.getVideoUrl() != null && !info.getVideoUrl().isBlank()) {
                return info.getVideoUrl();
            }
            if (info.getVideoUrls() != null) {
                for (String value : info.getVideoUrls()) {
                    if (value != null && !value.isBlank()) {
                        return value;
                    }
                }
            }
        }
        return originalUrl;
    }

    private static String resolveAudioUrl(VideoInfo info) {
        if (info != null && info.getAudioUrls() != null) {
            for (String value : info.getAudioUrls()) {
                if (value != null && !value.isBlank()) {
                    return value;
                }
            }
        }
        if (info != null && info.getVideoUrl() != null && isAudioUrl(info.getVideoUrl())) {
            return info.getVideoUrl();
        }
        return null;
    }

    private static boolean isAudioUrl(String value) {
        if (value == null) {
            return false;
        }
        String lower = value.toLowerCase(Locale.ROOT);
        return lower.contains(".mp3") || lower.contains(".m4a") || lower.contains(".aac")
            || lower.contains(".flac") || lower.contains(".ogg") || lower.contains(".wav");
    }

    private static String defaultMediaTitle(VideoInfo info, String fallbackUrl) {
        return fallbackVideoTitle(fallbackUrl, info == null ? null : info.getTitle());
    }

    private static String buildAudioOutputPath(String outputDir, String title) {
        return new File(outputDir, sanitizeFileName(title) + ".mp3").getPath();
    }

    private static String sanitizeFileName(String value) {
        String base = value == null || value.isBlank() ? "audio" : value;
        return base.replaceAll("[^a-zA-Z0-9\\u4e00-\\u9fa5._-]", "_").replaceAll("_+", "_");
    }
    
    /**
     * 处理转换命令
     */
    private static void handleConvert(String[] args) {
        if (args.length < 2) {
            System.out.println("Usage: convert <input> <format>");
            return;
        }
        
        String input = args[0];
        String format = args[1];
        
        try {
            FFmpegProcessor ffmpeg = createFFmpegProcessor();
            DependencyCheck ffmpegCheck = checkFFmpeg(ffmpeg);

            if (!ffmpegCheck.available()) {
                System.out.println("FFmpeg dependency check failed for convert.");
                System.out.println(ffmpegCheck.message());
                return;
            }
            
            String output = ffmpeg.convert(input, input + "." + format, format);
            System.out.println("Converted: " + output);
            
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
        }
    }
    
    /**
     * 处理合并命令
     */
    private static void handleMerge(String[] args) {
        if (args.length < 2) {
            System.out.println("Usage: merge <output> <input1> [input2] ...");
            return;
        }
        
        String output = args[0];
        List<String> inputs = new ArrayList<>();
        for (int i = 1; i < args.length; i++) {
            inputs.add(args[i]);
        }
        
        try {
            FFmpegProcessor ffmpeg = createFFmpegProcessor();
            DependencyCheck ffmpegCheck = checkFFmpeg(ffmpeg);
            if (!ffmpegCheck.available()) {
                System.out.println("FFmpeg dependency check failed for merge.");
                System.out.println(ffmpegCheck.message());
                return;
            }

            String result = ffmpeg.merge(inputs, output);
            System.out.println("Merged: " + result);
            
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
        }
    }

    /**
     * 处理依赖检查命令
     */
    private static void handleDoctor(String[] args) {
        boolean jsonOutput = Arrays.asList(args).contains("--json");
        DoctorReport report = buildDoctorReport();

        if (jsonOutput) {
            printDoctorJson(report);
            return;
        }

        System.out.println("========== MediaDownloader Doctor ==========");
        for (DoctorCheck check : report.checks()) {
            String label = switch (check.name()) {
                case "java" -> "Java";
                case "working-directory" -> "Working directory";
                case "ffmpeg" -> "FFmpeg";
                default -> check.name();
            };
            System.out.println(label + ": " + check.details());
        }
    }
    
    /**
     * 获取合适的解析器
     */
    private static VideoParser getParser(String url) {
        List<VideoParser> parsers = Arrays.asList(
            new YoukuParser(),
            new YouTubeParser(),
            new BilibiliParser(),
            new IqiyiParser(),
            new TencentParser(),
            new GenericParser()
        );
        
        for (VideoParser parser : parsers) {
            if (parser.supports(url)) {
                return parser;
            }
        }
        
        return null;
    }
    
    /**
     * 打印帮助信息
     */
    private static void printHelp() {
        System.out.println("MediaDownloader CLI v" + VERSION);
        System.out.println();
        System.out.println("Usage: <command> [options]");
        System.out.println();
        System.out.println("Commands:");
        System.out.println("  download <url> [options]  Download video");
        System.out.println("  info <url>                Show video info");
        System.out.println("  artifact [options]        Parse or download from artifact directory");
        System.out.println("  drm [options]             Inspect DRM signals from HTML/manifests/URLs");
        System.out.println("  convert <input> <format>  Convert video format");
        System.out.println("  merge <output> <inputs>   Merge videos");
        System.out.println("  doctor [--json]           Check runtime dependencies");
        System.out.println("  version                   Show version");
        System.out.println("  help                      Show this help");
        System.out.println();
        System.out.println("Download Options:");
        System.out.println("  -o, --output <dir>        Output directory");
        System.out.println("  -q, --quality <quality>   Video quality (best, 1080p, 720p, etc.)");
        System.out.println("  -a, --audio-only          Download audio only");
        System.out.println();
        System.out.println("Examples:");
        System.out.println("  download https://www.youku.tv/v/xxx.html");
        System.out.println("  download https://www.youku.tv/v/xxx.html -o ./videos -q 1080p");
        System.out.println("  info https://www.youku.tv/v/xxx.html");
        System.out.println("  drm --content \"#EXTM3U ...\"");
        System.out.println("  convert video.mp4 avi");
        System.out.println("  merge output.mp4 part1.mp4 part2.mp4");
        System.out.println("  doctor");
        System.out.println("  doctor --json");
    }

    private static FFmpegProcessor createFFmpegProcessor() {
        String configuredPath = resolveFFmpegPath();
        return configuredPath == null ? new FFmpegProcessor() : new FFmpegProcessor(configuredPath, null);
    }

    private static DoctorReport buildDoctorReport() {
        List<DoctorCheck> checks = new ArrayList<>();
        checks.add(new DoctorCheck("java", "passed", System.getProperty("java.version")));
        checks.add(new DoctorCheck("working-directory", "passed", System.getProperty("user.dir")));

        FFmpegProcessor ffmpeg = createFFmpegProcessor();
        DependencyCheck ffmpegCheck = checkFFmpeg(ffmpeg);
        String ffmpegStatus = ffmpegCheck.available() ? "passed" : "failed";
        String ffmpegMessage = ffmpegCheck.message();
        if (ffmpegCheck.available()) {
            String version = ffmpeg.getVersion().lines().findFirst().orElse("Unknown");
            ffmpegMessage = ffmpegMessage + " | " + version;
        }
        checks.add(new DoctorCheck("ffmpeg", ffmpegStatus, ffmpegMessage));

        String summary = checks.stream().anyMatch(check -> "failed".equals(check.status())) ? "failed" : "passed";
        int exitCode = "passed".equals(summary) ? 0 : 1;
        return new DoctorReport("doctor", "java", summary, exitCode, checks);
    }

    private static void printDoctorJson(DoctorReport report) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            System.out.println(mapper.writeValueAsString(report));
        } catch (Exception e) {
            System.err.println("Error: failed to render doctor report JSON: " + e.getMessage());
        }
    }

    private static DependencyCheck checkFFmpeg(FFmpegProcessor ffmpeg) {
        String configuredPath = resolveFFmpegPath();
        if (ffmpeg.isAvailable()) {
            String source = configuredPath != null ? configuredPath : "PATH";
            return new DependencyCheck(true, "available (" + source + ")");
        }

        if (configuredPath != null) {
            return new DependencyCheck(
                false,
                "missing or unusable at " + configuredPath +
                    ". Update system property '" + FFMPEG_PATH_PROPERTY + "' or env FFMPEG_PATH."
            );
        }

        return new DependencyCheck(
            false,
            "missing from PATH. Install FFmpeg or set system property '" +
                FFMPEG_PATH_PROPERTY + "' or env FFMPEG_PATH."
        );
    }

    private static String resolveFFmpegPath() {
        String configuredPath = System.getProperty(FFMPEG_PATH_PROPERTY);
        if (configuredPath == null || configuredPath.isBlank()) {
            configuredPath = System.getenv("FFMPEG_PATH");
        }

        if (configuredPath != null && !configuredPath.isBlank()) {
            return configuredPath;
        }

        List<String> commonPaths = List.of(
            "C:\\ffmpeg\\ffmpeg.exe",
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
            "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg"
        );

        for (String candidate : commonPaths) {
            if (new File(candidate).isFile()) {
                return candidate;
            }
        }

        return null;
    }

    record DependencyCheck(boolean available, String message) {
    }

    record DoctorCheck(String name, String status, String details) {
    }

    record DoctorReport(String command, String runtime, String summary, int exit_code, List<DoctorCheck> checks) {
    }
}
