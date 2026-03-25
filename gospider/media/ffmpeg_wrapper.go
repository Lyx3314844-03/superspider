package media

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// FFmpegWrapper FFmpeg 操作封装
type FFmpegWrapper struct {
	FFmpegPath string
	OutputDir  string
}

// NewFFmpegWrapper 创建 FFmpeg 封装器
func NewFFmpegWrapper(ffmpegPath, outputDir string) *FFmpegWrapper {
	return &FFmpegWrapper{
		FFmpegPath: ffmpegPath,
		OutputDir:  outputDir,
	}
}

// AutoDetectFFmpeg 自动检测 FFmpeg 安装
func AutoDetectFFmpeg() (string, error) {
	// 常见 FFmpeg 安装路径
	paths := []string{
		"ffmpeg.exe", // PATH 中的
		"C:\\ffmpeg\\ffmpeg.exe",
		"C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
	}

	for _, path := range paths {
		if _, err := os.Stat(path); err == nil {
			return path, nil
		}
	}

	// 尝试从 PATH 查找
	path, err := exec.LookPath("ffmpeg")
	if err != nil {
		return "", fmt.Errorf("未找到 FFmpeg，请安装或添加到 PATH")
	}

	return path, nil
}

// MergeVideos 合并视频文件 (使用 concat demuxer)
func (f *FFmpegWrapper) MergeVideos(inputFiles []string, outputFile string) error {
	// 创建临时文件列表
	tempFile := filepath.Join(f.OutputDir, "merge_list.txt")
	content := ""
	for _, file := range inputFiles {
		absPath, _ := filepath.Abs(file)
		// 转义单引号
		absPath = strings.Replace(absPath, "'", "'\\''", -1)
		content += fmt.Sprintf("file '%s'\n", absPath)
	}

	if err := os.WriteFile(tempFile, []byte(content), 0644); err != nil {
		return err
	}
	defer os.Remove(tempFile)

	// 执行合并
	cmd := exec.Command(f.FFmpegPath,
		"-y",                    // 覆盖输出
		"-f", "concat",          // 输入格式
		"-safe", "0",            // 允许任意路径
		"-i", tempFile,          // 输入文件列表
		"-c", "copy",            // 直接复制流
		"-fflags", "+genpts",    // 生成时间戳
		outputFile,
	)

	var stderr bytes.Buffer
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("合并失败：%v\n%s", err, stderr.String())
	}

	return nil
}

// CombineAudioVideo 合并音视频
func (f *FFmpegWrapper) CombineAudioVideo(videoFile, audioFile, outputFile string) error {
	cmd := exec.Command(f.FFmpegPath,
		"-y",
		"-i", videoFile,
		"-i", audioFile,
		"-c:v", "copy",
		"-c:a", "aac",
		"-strict", "experimental",
		outputFile,
	)

	var stderr bytes.Buffer
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("合并失败：%v\n%s", err, stderr.String())
	}

	return nil
}

// DownloadHLS 下载 HLS 流 (m3u8)
func (f *FFmpegWrapper) DownloadHLS(m3u8URL, outputFile string) error {
	cmd := exec.Command(f.FFmpegPath,
		"-y",
		"-i", m3u8URL,
		"-c", "copy",
		"-bsf:a", "aac_adtstoasc",
		outputFile,
	)

	var stderr bytes.Buffer
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("下载失败：%v\n%s", err, stderr.String())
	}

	return nil
}

// CheckDRM 检测视频是否加密
func (f *FFmpegWrapper) CheckDRM(videoFile string) (bool, string, error) {
	cmd := exec.Command(f.FFmpegPath,
		"-i", videoFile,
	)

	output, _ := cmd.CombinedOutput()
	// ffmpeg 返回错误是正常的

	outputStr := string(output)

	// 检测加密标志
	drmIndicators := []string{
		"Encryption initialization data",
		"cenc",
		"cbcs",
		"Protection System Specific Header",
		"pssh",
	}

	for _, indicator := range drmIndicators {
		if strings.Contains(strings.ToLower(outputStr), strings.ToLower(indicator)) {
			return true, indicator, nil
		}
	}

	return false, "", nil
}

// GetVideoInfo 获取视频基本信息
func (f *FFmpegWrapper) GetVideoInfo(videoFile string) (map[string]string, error) {
	cmd := exec.Command(f.FFmpegPath,
		"-i", videoFile,
	)

	output, err := cmd.CombinedOutput()
	if err != nil {
		// 继续处理输出
	}

	info := make(map[string]string)
	outputStr := string(output)

	// 简单解析
	if strings.Contains(outputStr, "Duration:") {
		// 提取时长
		info["raw"] = outputStr
	}

	return info, nil
}

// IsAvailable 检查 FFmpeg 是否可用
func (f *FFmpegWrapper) IsAvailable() bool {
	_, err := os.Stat(f.FFmpegPath)
	return err == nil
}
