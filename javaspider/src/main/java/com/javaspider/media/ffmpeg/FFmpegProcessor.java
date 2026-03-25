package com.javaspider.media.ffmpeg;

import java.io.*;
import java.util.*;
import java.util.concurrent.*;

/**
 * FFmpeg 处理器
 * 支持视频转换、合并、剪辑等操作
 */
public class FFmpegProcessor {
    
    private final String ffmpegPath;
    private final String workingDir;
    
    public FFmpegProcessor() {
        this(null, null);
    }
    
    public FFmpegProcessor(String ffmpegPath, String workingDir) {
        this.ffmpegPath = ffmpegPath != null ? ffmpegPath : "ffmpeg";
        this.workingDir = workingDir != null ? workingDir : System.getProperty("java.io.tmpdir");
    }
    
    /**
     * 检查 FFmpeg 是否可用
     */
    public boolean isAvailable() {
        try {
            ProcessBuilder pb = new ProcessBuilder(ffmpegPath, "-version");
            Process process = pb.start();
            int exitCode = process.waitFor();
            return exitCode == 0;
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * 获取 FFmpeg 版本
     */
    public String getVersion() {
        try {
            ProcessBuilder pb = new ProcessBuilder(ffmpegPath, "-version");
            return executeAndGetOutput(pb);
        } catch (Exception e) {
            return "Unknown";
        }
    }
    
    /**
     * 转换视频格式
     */
    public String convert(String inputFile, String outputFile, String format) throws Exception {
        String output = outputFile + "." + format;
        
        ProcessBuilder pb = new ProcessBuilder(
            ffmpegPath,
            "-i", inputFile,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-y",
            output
        );
        
        execute(pb);
        return output;
    }
    
    /**
     * 调整视频质量
     */
    public String changeQuality(String inputFile, String outputFile, int crf) throws Exception {
        ProcessBuilder pb = new ProcessBuilder(
            ffmpegPath,
            "-i", inputFile,
            "-c:v", "libx264",
            "-crf", String.valueOf(crf),
            "-c:a", "copy",
            "-y",
            outputFile
        );
        
        execute(pb);
        return outputFile;
    }
    
    /**
     * 裁剪视频
     */
    public String crop(String inputFile, String outputFile, int x, int y, int width, int height) throws Exception {
        ProcessBuilder pb = new ProcessBuilder(
            ffmpegPath,
            "-i", inputFile,
            "-vf", String.format("crop=%d:%d:%d:%d", width, height, x, y),
            "-c:a", "copy",
            "-y",
            outputFile
        );
        
        execute(pb);
        return outputFile;
    }
    
    /**
     * 合并视频
     */
    public String merge(List<String> inputFiles, String outputFile) throws Exception {
        // 创建文件列表
        File listFile = new File(workingDir, "merge_list_" + System.currentTimeMillis() + ".txt");
        try (PrintWriter writer = new PrintWriter(listFile)) {
            for (String file : inputFiles) {
                writer.println("file '" + file + "'");
            }
        }
        
        ProcessBuilder pb = new ProcessBuilder(
            ffmpegPath,
            "-f", "concat",
            "-safe", "0",
            "-i", listFile.getAbsolutePath(),
            "-c", "copy",
            "-y",
            outputFile
        );
        
        execute(pb);
        listFile.delete();
        
        return outputFile;
    }
    
    /**
     * 提取音频
     */
    public String extractAudio(String inputFile, String outputFile) throws Exception {
        ProcessBuilder pb = new ProcessBuilder(
            ffmpegPath,
            "-i", inputFile,
            "-vn",
            "-acodec", "libmp3lame",
            "-ab", "192k",
            "-y",
            outputFile
        );
        
        execute(pb);
        return outputFile;
    }
    
    /**
     * 添加水印
     */
    public String addWatermark(String inputFile, String watermarkFile, String outputFile, 
                               String position) throws Exception {
        ProcessBuilder pb = new ProcessBuilder(
            ffmpegPath,
            "-i", inputFile,
            "-i", watermarkFile,
            "-filter_complex", String.format("overlay=%s", position),
            "-c:a", "copy",
            "-y",
            outputFile
        );
        
        execute(pb);
        return outputFile;
    }
    
    /**
     * 获取视频信息
     */
    public VideoInfo getVideoInfo(String inputFile) throws Exception {
        ProcessBuilder pb = new ProcessBuilder(
            ffmpegPath,
            "-i", inputFile
        );
        
        String output = executeAndGetOutput(pb);
        return parseVideoInfo(output);
    }
    
    /**
     * 创建 GIF
     */
    public String createGIF(String inputFile, String outputFile, int startTime, int duration) throws Exception {
        ProcessBuilder pb = new ProcessBuilder(
            ffmpegPath,
            "-ss", String.valueOf(startTime),
            "-t", String.valueOf(duration),
            "-i", inputFile,
            "-vf", "fps=10,scale=320:-1:flags=lanczos",
            "-y",
            outputFile
        );
        
        execute(pb);
        return outputFile;
    }
    
    /**
     * 截图
     */
    public String takeScreenshot(String inputFile, String outputFile, double timestamp) throws Exception {
        ProcessBuilder pb = new ProcessBuilder(
            ffmpegPath,
            "-ss", String.valueOf(timestamp),
            "-i", inputFile,
            "-vframes", "1",
            "-y",
            outputFile
        );
        
        execute(pb);
        return outputFile;
    }
    
    /**
     * 执行命令
     */
    private void execute(ProcessBuilder pb) throws Exception {
        pb.redirectErrorStream(true);
        Process process = pb.start();
        
        // 读取输出
        new Thread(() -> {
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(process.getInputStream()))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    System.out.println(line);
                }
            } catch (IOException e) {
                e.printStackTrace();
            }
        }).start();
        
        int exitCode = process.waitFor();
        if (exitCode != 0) {
            throw new Exception("FFmpeg exited with code: " + exitCode);
        }
    }
    
    /**
     * 执行并获取输出
     */
    private String executeAndGetOutput(ProcessBuilder pb) throws Exception {
        pb.redirectErrorStream(true);
        Process process = pb.start();
        
        StringBuilder output = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
            }
        }
        
        process.waitFor();
        return output.toString();
    }
    
    /**
     * 解析视频信息
     */
    private VideoInfo parseVideoInfo(String output) {
        VideoInfo info = new VideoInfo();
        
        // 简单解析
        if (output.contains("Video:")) {
            info.hasVideo = true;
        }
        if (output.contains("Audio:")) {
            info.hasAudio = true;
        }
        
        // 提取时长
        int durationIndex = output.indexOf("Duration:");
        if (durationIndex > 0) {
            String durationStr = output.substring(durationIndex + 9, durationIndex + 20);
            info.duration = durationStr.trim();
        }
        
        return info;
    }
    
    /**
     * 视频信息类
     */
    public static class VideoInfo {
        public boolean hasVideo;
        public boolean hasAudio;
        public String duration;
        public String resolution;
        public String codec;
        public String bitrate;
        
        @Override
        public String toString() {
            return "VideoInfo{" +
                    "hasVideo=" + hasVideo +
                    ", hasAudio=" + hasAudio +
                    ", duration='" + duration + '\'' +
                    '}';
        }
    }
}
