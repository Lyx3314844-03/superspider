package com.javaspider.media;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

/**
 * FFmpeg 工具类
 * 提供视频合并、转码、截图等功能
 */
public class FFmpegUtil {
    
    private String ffmpegPath;
    private String workingDir;
    
    /**
     * 默认构造函数
     */
    public FFmpegUtil() {
        this.ffmpegPath = findFFmpeg();
        this.workingDir = System.getProperty("user.dir");
    }
    
    /**
     * 指定 FFmpeg 路径
     * @param ffmpegPath FFmpeg 路径
     */
    public FFmpegUtil(String ffmpegPath) {
        this.ffmpegPath = ffmpegPath;
        this.workingDir = System.getProperty("user.dir");
    }
    
    /**
     * 设置工作目录
     * @param dir 工作目录
     */
    public void setWorkingDir(String dir) {
        this.workingDir = dir;
    }
    
    /**
     * 查找 FFmpeg
     */
    public static String findFFmpeg() {
        // 检查环境变量
        String path = System.getenv("FFMPEG_PATH");
        if (path != null && !path.isEmpty()) {
            return path;
        }
        
        // 检查常见路径
        String[] paths = {
            "ffmpeg",
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/opt/homebrew/bin/ffmpeg"
        };
        
        for (String p : paths) {
            try {
                ProcessBuilder pb = new ProcessBuilder(p, "-version");
                Process process = pb.start();
                process.waitFor(5, TimeUnit.SECONDS);
                if (process.exitValue() == 0) {
                    return p;
                }
            } catch (Exception e) {
                // 忽略
            }
        }
        
        return null;
    }
    
    /**
     * 检查 FFmpeg 是否可用
     */
    public boolean isAvailable() {
        return ffmpegPath != null;
    }
    
    /**
     * 获取 FFmpeg 路径
     */
    public String getFFmpegPath() {
        return ffmpegPath;
    }
    
    /**
     * 合并音视频
     * @param videoFile 视频文件
     * @param audioFile 音频文件
     * @param outputFile 输出文件
     * @return 是否成功
     */
    public boolean combineAudioVideo(String videoFile, String audioFile, String outputFile) {
        if (!isAvailable()) {
            System.err.println("FFmpeg 不可用");
            return false;
        }
        
        try {
            ProcessBuilder pb = new ProcessBuilder(
                ffmpegPath,
                "-i", videoFile,
                "-i", audioFile,
                "-c:v", "copy",
                "-c:a", "aac",
                "-strict", "experimental",
                "-y",
                outputFile
            );
            pb.inheritIO();
            Process process = pb.start();
            process.waitFor();
            
            return process.exitValue() == 0;
            
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }
    
    /**
     * 合并多个视频文件
     * @param videoFiles 视频文件列表
     * @param outputFile 输出文件
     * @return 是否成功
     */
    public boolean concatVideos(List<String> videoFiles, String outputFile) {
        if (!isAvailable() || videoFiles.isEmpty()) {
            return false;
        }
        
        try {
            // 创建临时列表文件
            Path listFile = Files.createTempFile("ffmpeg_list", ".txt");
            
            try (PrintWriter writer = new PrintWriter(listFile.toFile())) {
                for (String file : videoFiles) {
                    writer.println("file '" + file + "'");
                }
            }
            
            ProcessBuilder pb = new ProcessBuilder(
                ffmpegPath,
                "-f", "concat",
                "-safe", "0",
                "-i", listFile.toString(),
                "-c:v", "copy",
                "-c:a", "aac",
                "-y",
                outputFile
            );
            pb.inheritIO();
            Process process = pb.start();
            process.waitFor();
            
            // 清理临时文件
            Files.delete(listFile);
            
            return process.exitValue() == 0;
            
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }
    
    /**
     * 转码视频
     * @param inputFile 输入文件
     * @param outputFile 输出文件
     * @param format 输出格式 (mp4, mkv, avi 等)
     * @param quality 质量 (low, medium, high)
     * @return 是否成功
     */
    public boolean transcode(String inputFile, String outputFile, String format, String quality) {
        if (!isAvailable()) {
            return false;
        }
        
        try {
            List<String> command = new ArrayList<>();
            command.add(ffmpegPath);
            command.add("-i");
            command.add(inputFile);
            
            // 根据质量设置参数
            if ("low".equals(quality)) {
                command.add("-crf");
                command.add("28");
            } else if ("high".equals(quality)) {
                command.add("-crf");
                command.add("18");
            } else {
                command.add("-crf");
                command.add("23"); // medium
            }
            
            command.add("-c:v");
            command.add("libx264");
            command.add("-c:a");
            command.add("aac");
            command.add("-y");
            command.add(outputFile);
            
            ProcessBuilder pb = new ProcessBuilder(command);
            pb.inheritIO();
            Process process = pb.start();
            process.waitFor();
            
            return process.exitValue() == 0;
            
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }
    
    /**
     * 生成视频截图
     * @param videoFile 视频文件
     * @param outputFile 输出文件
     * @param timestamp 时间戳 (格式：HH:MM:SS 或秒数)
     * @return 是否成功
     */
    public boolean takeScreenshot(String videoFile, String outputFile, String timestamp) {
        if (!isAvailable()) {
            return false;
        }
        
        try {
            ProcessBuilder pb = new ProcessBuilder(
                ffmpegPath,
                "-ss", timestamp,
                "-i", videoFile,
                "-vframes", "1",
                "-y",
                outputFile
            );
            pb.inheritIO();
            Process process = pb.start();
            process.waitFor();
            
            return process.exitValue() == 0;
            
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }
    
    /**
     * 提取音频
     * @param videoFile 视频文件
     * @param outputFile 输出文件
     * @param format 音频格式 (mp3, aac, flac)
     * @return 是否成功
     */
    public boolean extractAudio(String videoFile, String outputFile, String format) {
        if (!isAvailable()) {
            return false;
        }
        
        try {
            List<String> command = new ArrayList<>();
            command.add(ffmpegPath);
            command.add("-i");
            command.add(videoFile);
            command.add("-vn");
            command.add("-acodec");
            
            if ("mp3".equals(format)) {
                command.add("libmp3lame");
            } else if ("flac".equals(format)) {
                command.add("flac");
            } else {
                command.add("aac");
            }
            
            command.add("-y");
            command.add(outputFile);
            
            ProcessBuilder pb = new ProcessBuilder(command);
            pb.inheritIO();
            Process process = pb.start();
            process.waitFor();
            
            return process.exitValue() == 0;
            
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }
    
    /**
     * 获取视频信息
     * @param videoFile 视频文件
     * @return 视频信息 Map
     */
    public Map<String, Object> getVideoInfo(String videoFile) {
        Map<String, Object> info = new HashMap<>();
        
        if (!isAvailable()) {
            return info;
        }
        
        try {
            ProcessBuilder pb = new ProcessBuilder(
                ffmpegPath,
                "-i", videoFile
            );
            pb.redirectErrorStream(true);
            Process process = pb.start();
            
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;
            
            while ((line = reader.readLine()) != null) {
                // 解析 Duration
                if (line.contains("Duration:")) {
                    String[] parts = line.split("Duration:")[1].split(",")[0].trim().split(":");
                    if (parts.length == 3) {
                        int hours = Integer.parseInt(parts[0].trim());
                        int minutes = Integer.parseInt(parts[1].trim());
                        double seconds = Double.parseDouble(parts[2].trim());
                        info.put("duration", hours * 3600 + minutes * 60 + seconds);
                    }
                }
                
                // 解析 Video
                if (line.contains("Video:")) {
                    if (line.contains("Stream")) {
                        String[] parts = line.split("Video:", 2);
                        if (parts.length > 1) {
                            info.put("video_codec", parts[1].split(",")[0].trim());
                        }
                    }
                }

                // 解析 Audio
                if (line.contains("Audio:")) {
                    if (line.contains("Stream")) {
                        String[] parts = line.split("Audio:", 2);
                        if (parts.length > 1) {
                            info.put("audio_codec", parts[1].split(",")[0].trim());
                        }
                    }
                }
            }
            
            reader.close();
            process.waitFor();
            
        } catch (Exception e) {
            e.printStackTrace();
        }
        
        return info;
    }
    
    /**
     * 压缩视频
     * @param inputFile 输入文件
     * @param outputFile 输出文件
     * @param targetSize 目标大小 (MB)
     * @return 是否成功
     */
    public boolean compress(String inputFile, String outputFile, int targetSize) {
        if (!isAvailable()) {
            return false;
        }
        
        try {
            // 计算比特率
            Map<String, Object> info = getVideoInfo(inputFile);
            Double duration = (Double) info.get("duration");
            
            if (duration == null || duration == 0) {
                return false;
            }
            
            // 目标比特率 (kbps)
            int targetBitrate = (int) ((targetSize * 8 * 1000) / duration);
            
            ProcessBuilder pb = new ProcessBuilder(
                ffmpegPath,
                "-i", inputFile,
                "-b:v", targetBitrate + "k",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-y",
                outputFile
            );
            pb.inheritIO();
            Process process = pb.start();
            process.waitFor();
            
            return process.exitValue() == 0;
            
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }
    
    /**
     * 裁剪视频
     * @param inputFile 输入文件
     * @param outputFile 输出文件
     * @param startTime 开始时间 (HH:MM:SS)
     * @param duration 持续时间 (秒)
     * @return 是否成功
     */
    public boolean trim(String inputFile, String outputFile, String startTime, double duration) {
        if (!isAvailable()) {
            return false;
        }
        
        try {
            ProcessBuilder pb = new ProcessBuilder(
                ffmpegPath,
                "-ss", startTime,
                "-t", String.valueOf(duration),
                "-i", inputFile,
                "-c:v", "copy",
                "-c:a", "copy",
                "-y",
                outputFile
            );
            pb.inheritIO();
            Process process = pb.start();
            process.waitFor();
            
            return process.exitValue() == 0;
            
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }
    
    /**
     * 添加水印
     * @param videoFile 视频文件
     * @param watermarkFile 水印文件
     * @param outputFile 输出文件
     * @param position 位置 (topleft, topright, bottomleft, bottomright)
     * @return 是否成功
     */
    public boolean addWatermark(String videoFile, String watermarkFile, String outputFile, String position) {
        if (!isAvailable()) {
            return false;
        }
        
        try {
            String overlay = "";
            switch (position.toLowerCase()) {
                case "topright":
                    overlay = "W-w-10:10";
                    break;
                case "bottomleft":
                    overlay = "10:H-h-10";
                    break;
                case "bottomright":
                    overlay = "W-w-10:H-h-10";
                    break;
                default: // topleft
                    overlay = "10:10";
            }
            
            ProcessBuilder pb = new ProcessBuilder(
                ffmpegPath,
                "-i", videoFile,
                "-i", watermarkFile,
                "-filter_complex", "overlay=" + overlay,
                "-y",
                outputFile
            );
            pb.inheritIO();
            Process process = pb.start();
            process.waitFor();
            
            return process.exitValue() == 0;
            
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }
}
