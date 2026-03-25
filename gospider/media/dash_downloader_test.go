package media

import (
	"os"
	"testing"
)

// TestDASHDownloaderCreation 测试 DASH 下载器创建
func TestDASHDownloaderCreation(t *testing.T) {
	downloader := NewDASHDownloader("./downloads")
	
	if downloader == nil {
		t.Fatal("DASH 下载器创建失败")
	}
	
	if downloader.outputDir != "./downloads" {
		t.Errorf("期望输出目录为./downloads, 实际为：%s", downloader.outputDir)
	}
	
	if downloader.concurrent != 5 {
		t.Errorf("期望并发数为 5, 实际为：%d", downloader.concurrent)
	}
}

// TestDASHDownloaderSetConcurrent 测试设置并发数
func TestDASHDownloaderSetConcurrent(t *testing.T) {
	downloader := NewDASHDownloader("./downloads")
	downloader.SetConcurrent(10)
	
	if downloader.concurrent != 10 {
		t.Errorf("期望并发数为 10, 实际为：%d", downloader.concurrent)
	}
}

// TestDASHDownloaderSelectQuality 测试清晰度选择
func TestDASHDownloaderSelectQuality(t *testing.T) {
	downloader := NewDASHDownloader("./downloads")
	
	formats := []DASHFormat{
		{ID: "1", Quality: "360p", Height: 360},
		{ID: "2", Quality: "480p", Height: 480},
		{ID: "3", Quality: "720p", Height: 720},
		{ID: "4", Quality: "1080p", Height: 1080},
	}
	
	// 测试自动选择（最高清晰度）
	best := downloader.selectQuality(formats, "auto")
	if best.Height != 1080 {
		t.Errorf("期望选择 1080p, 实际为：%dp", best.Height)
	}
	
	// 测试指定 720p
	selected := downloader.selectQuality(formats, "720p")
	if selected.Height != 720 {
		t.Errorf("期望选择 720p, 实际为：%dp", selected.Height)
	}
	
	// 测试指定 1080p（应该选择 1080p 或更低的最接近值）
	selected = downloader.selectQuality(formats, "1080p")
	if selected.Height != 1080 {
		t.Errorf("期望选择 1080p, 实际为：%dp", selected.Height)
	}
}

// TestDASHDownloaderDetermineQuality 测试质量判断
func TestDASHDownloaderDetermineQuality(t *testing.T) {
	downloader := NewDASHDownloader("./downloads")
	
	tests := []struct {
		height   int
		expected string
	}{
		{2160, "4K"},
		{1440, "2K"},
		{1080, "1080p"},
		{720, "720p"},
		{480, "480p"},
		{360, "360p"},
		{240, "360p"},
	}
	
	for _, test := range tests {
		result := downloader.determineQuality(test.height)
		if result != test.expected {
			t.Errorf("高度 %d: 期望 %s, 实际为：%s", test.height, test.expected, result)
		}
	}
}

// TestDASHDownloaderHashURL 测试 URL 哈希
func TestDASHDownloaderHashURL(t *testing.T) {
	downloader := NewDASHDownloader("./downloads")
	
	url := "https://example.com/video.mp4"
	hash1 := downloader.hashURL(url)
	hash2 := downloader.hashURL(url)
	
	if hash1 != hash2 {
		t.Error("相同 URL 的哈希应该相同")
	}
	
	if len(hash1) == 0 {
		t.Error("哈希值不应为空")
	}
}

// TestDASHDownloaderParseDuration 测试时长解析
func TestDASHDownloaderParseDuration(t *testing.T) {
	downloader := NewDASHDownloader("./downloads")
	
	tests := []struct {
		duration string
		expected float64
	}{
		{"PT1H2M3S", 3723.0},
		{"PT30S", 30.0},
		{"PT2M", 120.0},
		{"PT1H", 3600.0},
		{"PT1H30S", 3630.0},
	}
	
	for _, test := range tests {
		result := downloader.parseDuration(test.duration)
		if result != test.expected {
			t.Errorf("时长 %s: 期望 %.1f, 实际为：%.1f", test.duration, test.expected, result)
		}
	}
}

// TestDASHDownloaderExtractContentType 测试内容类型提取
func TestDASHDownloaderExtractContentType(t *testing.T) {
	downloader := NewDASHDownloader("./downloads")
	
	tests := []struct {
		mimeType string
		expected string
	}{
		{"video/mp4", "video"},
		{"audio/mp4", "audio"},
		{"text/vtt", "other"},
		{"application/mpd", "other"},
	}
	
	for _, test := range tests {
		result := downloader.extractContentType(test.mimeType)
		if result != test.expected {
			t.Errorf("MIME 类型 %s: 期望 %s, 实际为：%s", test.mimeType, test.expected, result)
		}
	}
}

// TestDASHDownloadTaskSaveInfo 测试任务信息保存
func TestDASHDownloadTaskSaveInfo(t *testing.T) {
	task := &DASHDownloadTask{
		ID:         "test-task-001",
		MPDURL:     "https://example.com/video.mpd",
		Status:     "completed",
		OutputFile: "./downloads/test.mp4",
	}
	
	// 创建临时目录
	tmpDir := t.TempDir()
	outputFile := tmpDir + "/test.mp4"
	
	err := task.SaveTaskInfo(outputFile)
	if err != nil {
		t.Fatalf("保存任务信息失败：%v", err)
	}
	
	// 检查文件是否存在
	infoFile := tmpDir + "/test.json"
	if _, err := os.Stat(infoFile); os.IsNotExist(err) {
		t.Error("任务信息文件应该存在")
	}
}

// TestDASHDownloaderGetAvailableQualities 测试获取可用清晰度
func TestDASHDownloaderGetAvailableQualities(t *testing.T) {
	downloader := NewDASHDownloader("./downloads")
	
	formats := []DASHFormat{
		{ID: "1", Quality: "360p"},
		{ID: "2", Quality: "480p"},
		{ID: "3", Quality: "720p"},
		{ID: "4", Quality: "1080p"},
		{ID: "5", Quality: "1080p"}, // 重复
	}
	
	qualities := downloader.getAvailableQualities(formats)
	
	// 应该有 4 种不同的清晰度
	if len(qualities) != 4 {
		t.Errorf("期望 4 种清晰度，实际为：%d", len(qualities))
	}
}

// BenchmarkDASHDownloaderHashURL 性能测试
func BenchmarkDASHDownloaderHashURL(b *testing.B) {
	downloader := NewDASHDownloader("./downloads")
	url := "https://example.com/video.mp4"
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		downloader.hashURL(url)
	}
}

// BenchmarkDASHDownloaderSelectQuality 性能测试
func BenchmarkDASHDownloaderSelectQuality(b *testing.B) {
	downloader := NewDASHDownloader("./downloads")
	formats := make([]DASHFormat, 100)
	for i := range formats {
		formats[i] = DASHFormat{
			ID:      string(rune(i)),
			Height:  (i % 10) * 100,
			Quality: "auto",
		}
	}
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		downloader.selectQuality(formats, "1080p")
	}
}
