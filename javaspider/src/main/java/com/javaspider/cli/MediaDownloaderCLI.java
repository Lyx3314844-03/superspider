package com.javaspider.cli;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javaspider.media.*;
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
            VideoParser parser = getParser(url);
            if (parser == null) {
                System.out.println("Unsupported platform");
                return;
            }

            VideoInfo info = (!htmlFile.isBlank() || !networkFile.isBlank() || !harFile.isBlank())
                ? parseVideoArtifacts(url, htmlFile, networkFile, harFile)
                : parser.parse(url);
            System.out.println("Title: " + info.getTitle());
            System.out.println("Platform: " + info.getPlatform());
            System.out.println();
            String mediaUrl = resolveMediaUrl(info, url);
            
            // 2. 下载
            if (mediaUrl.contains(".m3u8")) {
                // HLS 流
                HLSDownloader hls = new HLSDownloader(outputDir);
                HLSDownloader.DownloadResult result = hls.download(mediaUrl, info.getTitle() + ".ts");
                System.out.println("Downloaded: " + result.outputFile);
                
            } else if (mediaUrl.contains(".mpd")) {
                // DASH 流
                DASHDownloader dash = new DASHDownloader(outputDir);
                DASHDownloader.DownloadResult result = dash.download(mediaUrl, quality);
                System.out.println("Downloaded: " + result.outputFile);
                
            } else {
                // 普通下载
                AdvancedMediaDownloader downloader = new AdvancedMediaDownloader(outputDir);
                MediaItem item = new MediaItem(info.getTitle(), mediaUrl, MediaType.VIDEO);
                String outputFile = downloader.downloadWithResume(item);
                System.out.println("Downloaded: " + outputFile);
            }
            
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
            VideoParser parser = getParser(url);
            if (parser == null) {
                // 尝试从 URL 推断平台
                if (url.contains("youtube.com") || url.contains("youtu.be")) {
                    System.out.println("Platform: YouTube");
                    System.out.println("Title: " + fallbackVideoTitle(url, null));
                    return;
                }
                System.out.println("Unsupported platform");
                return;
            }

            VideoInfo info = (!htmlFile.isBlank() || !networkFile.isBlank() || !harFile.isBlank())
                ? parseVideoArtifacts(url, htmlFile, networkFile, harFile)
                : parser.parse(url);
            String displayTitle = fallbackVideoTitle(url, info.getTitle());

            System.out.println("========== Video Info ==========");
            System.out.println("Title: " + displayTitle);
            System.out.println("Platform: " + info.getPlatform());
            System.out.println("Duration: " + info.getDuration() + "s");
            System.out.println("Views: " + info.getViewCount());
            System.out.println("Description: " + info.getDescription());
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
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("command", "media artifact");
            payload.put("runtime", "java");
            payload.put("url", url);
            payload.put("artifact_dir", artifactDir);
            payload.put("html_file", htmlFile);
            payload.put("network_file", networkFile);
            payload.put("har_file", harFile);
            payload.put("video", Map.of(
                "title", info.getTitle(),
                "platform", info.getPlatform(),
                "video_id", info.getVideoId(),
                "description", info.getDescription(),
                "cover_url", info.getCoverUrl(),
                "video_url", info.getVideoUrl(),
                "video_urls", info.getVideoUrls()
            ));
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
