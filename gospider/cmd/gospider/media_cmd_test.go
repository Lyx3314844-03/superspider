package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"gospider/extractors/bilibili"
	"gospider/extractors/iqiyi"
	"gospider/extractors/tencent"
	"gospider/extractors/youku"
)

func TestDetectPlatformRecognizesSupportedMediaSites(t *testing.T) {
	cases := map[string]string{
		"https://www.youtube.com/watch?v=demo":        "youtube",
		"https://v.youku.com/v_show/id_demo.html":     "youku",
		"https://www.iqiyi.com/v_demo.html":           "iqiyi",
		"https://v.qq.com/x/page/demo.html":           "tencent",
		"https://www.bilibili.com/video/BV1demo":      "bilibili",
		"https://example.com/video.mp4":               "unknown",
	}

	for input, expected := range cases {
		if actual := detectPlatform(input); actual != expected {
			t.Fatalf("detectPlatform(%q) = %q, want %q", input, actual, expected)
		}
	}
}

func TestChooseYoukuStreamPrefersPrimaryHLSThenDash(t *testing.T) {
	info := &youku.YoukuVideoInfo{
		M3U8URL: "https://example.com/master.m3u8",
		MPDURL:  "https://example.com/master.mpd",
		Streams: []youku.YoukuStream{
			{HLSURL: "https://example.com/fallback.m3u8"},
		},
	}

	url, stream := chooseYoukuStream(info)
	if url != "https://example.com/master.m3u8" {
		t.Fatalf("unexpected stream url: %s", url)
	}
	if stream.kind != "hls" || stream.fileExt != ".ts" {
		t.Fatalf("unexpected stream metadata: %+v", stream)
	}
}

func TestChooseYoukuStreamPrefersBestQualityCandidate(t *testing.T) {
	info := &youku.YoukuVideoInfo{
		Streams: []youku.YoukuStream{
			{Quality: "720p", HLSURL: "https://example.com/720.m3u8"},
			{Quality: "1080p", DASHURL: "https://example.com/1080.mpd"},
		},
	}

	url, stream := chooseYoukuStream(info)
	if url != "https://example.com/1080.mpd" {
		t.Fatalf("unexpected youku stream url: %s", url)
	}
	if stream.kind != "dash" || stream.fileExt != ".mp4" {
		t.Fatalf("unexpected youku stream metadata: %+v", stream)
	}
}

func TestChooseTencentURLReturnsFirstAvailableFormat(t *testing.T) {
	info := &tencent.VideoInfo{
		Formats: []tencent.VideoFormat{
			{Quality: "sd", URL: ""},
			{Quality: "hd", URL: "https://example.com/video.mp4"},
		},
	}

	if actual := chooseTencentURL(info); actual != "https://example.com/video.mp4" {
		t.Fatalf("unexpected tencent url: %s", actual)
	}
}

func TestChooseTencentURLPrefersHigherQualityFormat(t *testing.T) {
	info := &tencent.VideoInfo{
		Formats: []tencent.VideoFormat{
			{Quality: "720p", QualityID: 2, URL: "https://example.com/720.mp4"},
			{Quality: "1080p", QualityID: 4, URL: "https://example.com/1080.mp4"},
		},
	}

	if actual := chooseTencentURL(info); actual != "https://example.com/1080.mp4" {
		t.Fatalf("unexpected tencent best-quality url: %s", actual)
	}
}

func TestChooseIqiyiStreamPrefersHLSThenDash(t *testing.T) {
	info := &iqiyi.VideoInfo{
		M3U8URL: "https://media.example.com/master.m3u8",
		DASHURL: "https://media.example.com/manifest.mpd",
	}

	url, stream := chooseIqiyiStream(info)
	if url != "https://media.example.com/master.m3u8" {
		t.Fatalf("unexpected iqiyi stream url: %s", url)
	}
	if stream.kind != "hls" || stream.fileExt != ".ts" {
		t.Fatalf("unexpected iqiyi stream metadata: %+v", stream)
	}
}

func TestChooseIqiyiStreamPrefersBestQualityCandidate(t *testing.T) {
	info := &iqiyi.VideoInfo{
		Streams: []iqiyi.StreamInfo{
			{Quality: "720p", M3U8URL: "https://media.example.com/720.m3u8"},
			{Quality: "1080p", DASHURL: "https://media.example.com/1080.mpd"},
		},
	}

	url, stream := chooseIqiyiStream(info)
	if url != "https://media.example.com/1080.mpd" {
		t.Fatalf("unexpected iqiyi candidate stream url: %s", url)
	}
	if stream.kind != "dash" || stream.fileExt != ".mp4" {
		t.Fatalf("unexpected iqiyi candidate stream metadata: %+v", stream)
	}
}

func TestChooseBilibiliURLPrefersDirectVideoStream(t *testing.T) {
	info := &bilibili.BilibiliVideoInfo{
		BVID: "BV1demo",
		Video: &bilibili.BilibiliStream{
			BaseURL: "https://media.example.com/video.m4s",
		},
		DASHURL: "https://media.example.com/fallback.mpd",
	}

	if actual := chooseBilibiliURL(info); actual != "https://media.example.com/video.m4s" {
		t.Fatalf("unexpected bilibili url: %s", actual)
	}
}

func TestMediaFilenameSanitizesAndKeepsExtension(t *testing.T) {
	filename := mediaFilename(` demo:/title*? `, "fallback", ".mp4")
	if filename != "demotitle.mp4" {
		t.Fatalf("unexpected filename: %s", filename)
	}
}

func TestMediaDRMCommandDetectsCommercialProtectionFromManifestContent(t *testing.T) {
	output := captureStdout(t, func() {
		if code := mediaDRMCommand([]string{
			"--content",
			`<MPD><ContentProtection schemeIdUri="urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"><cenc:pssh>AAAA</cenc:pssh></ContentProtection></MPD>`,
		}); code != 0 {
			t.Fatalf("expected drm command to succeed, got %d", code)
		}
	})

	var payload map[string]any
	if err := json.Unmarshal([]byte(output), &payload); err != nil {
		t.Fatalf("expected json output: %v", err)
	}

	drmInfo := payload["drm_info"].(map[string]any)
	if drmInfo["drm_type"] != "widevine" {
		t.Fatalf("unexpected drm type: %#v", drmInfo)
	}
	if drmInfo["is_drm_protected"] != true {
		t.Fatalf("expected protected drm payload: %#v", drmInfo)
	}
	if payload["downloadable"] != false {
		t.Fatalf("expected commercial drm to be non-downloadable: %#v", payload)
	}
}

func TestMediaDRMCommandAllowsAES128Manifest(t *testing.T) {
	output := captureStdout(t, func() {
		if code := mediaDRMCommand([]string{
			"--content",
			`#EXTM3U
#EXT-X-KEY:METHOD=AES-128,URI="https://example.com/key.bin",IV=0xabcdef`,
		}); code != 0 {
			t.Fatalf("expected drm command to succeed, got %d", code)
		}
	})

	var payload map[string]any
	if err := json.Unmarshal([]byte(output), &payload); err != nil {
		t.Fatalf("expected json output: %v", err)
	}

	drmInfo := payload["drm_info"].(map[string]any)
	if drmInfo["drm_type"] != "aes-128" {
		t.Fatalf("unexpected drm type: %#v", drmInfo)
	}
	if payload["downloadable"] != true {
		t.Fatalf("expected aes-128 manifest to remain downloadable: %#v", payload)
	}
}

func TestResolveArtifactBundleAutoDiscoversFiles(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "page.html"), []byte("<html></html>"), 0644); err != nil {
		t.Fatalf("failed to write html fixture: %v", err)
	}
	if err := os.WriteFile(filepath.Join(dir, "network.json"), []byte(`{"video":"ok"}`), 0644); err != nil {
		t.Fatalf("failed to write network fixture: %v", err)
	}
	if err := os.WriteFile(filepath.Join(dir, "trace.har"), []byte(`{}`), 0644); err != nil {
		t.Fatalf("failed to write har fixture: %v", err)
	}

	htmlFile, networkFile, harFile := resolveArtifactBundle(dir, "", "", "")
	if filepath.Base(htmlFile) != "page.html" {
		t.Fatalf("unexpected html artifact: %s", htmlFile)
	}
	if filepath.Base(networkFile) != "network.json" {
		t.Fatalf("unexpected network artifact: %s", networkFile)
	}
	if filepath.Base(harFile) != "trace.har" {
		t.Fatalf("unexpected har artifact: %s", harFile)
	}
}
