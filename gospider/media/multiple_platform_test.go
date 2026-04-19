package media

import "testing"

func TestMultiPlatformDownloaderDetectPlatformRecognizesChineseMediaSites(t *testing.T) {
	downloader := NewMultiPlatformDownloader(t.TempDir())

	cases := map[string]string{
		"https://v.youku.com/v_show/id_demo.html": "youku",
		"https://www.iqiyi.com/v_19rrdemo.html":   "iqiyi",
		"https://v.qq.com/x/page/demo123.html":    "tencent",
	}

	for input, expected := range cases {
		if actual := downloader.DetectPlatform(input); actual != expected {
			t.Fatalf("DetectPlatform(%q) = %q, want %q", input, actual, expected)
		}
	}
}

func TestDiscoverVideoInfoFromHTMLFindsManifestAndVideoObject(t *testing.T) {
	html := `
	<html>
	  <head>
	    <title>Fallback Title</title>
	    <meta property="og:video" content="/streams/master.m3u8" />
	    <meta property="og:image" content="/cover.jpg" />
	    <script type="application/ld+json">
	      {
	        "@context": "https://schema.org",
	        "@type": "VideoObject",
	        "name": "Universal Fixture",
	        "description": "fixture description",
	        "contentUrl": "https://cdn.example.com/video.mp4",
	        "thumbnailUrl": "https://cdn.example.com/poster.png"
	      }
	    </script>
	  </head>
	  <body>
	    <video><source src="/dash/manifest.mpd" /></video>
	  </body>
	</html>`

	info := discoverVideoInfoFromHTML("https://example.com/watch/demo", html)
	if info == nil {
		t.Fatal("expected generic discovery to succeed")
	}
	if info.Title != "Universal Fixture" {
		t.Fatalf("unexpected title: %s", info.Title)
	}
	if info.Description != "fixture description" {
		t.Fatalf("unexpected description: %s", info.Description)
	}
	if info.HLSURL != "https://example.com/streams/master.m3u8" {
		t.Fatalf("unexpected hls url: %s", info.HLSURL)
	}
	if info.DASHURL != "https://example.com/dash/manifest.mpd" {
		t.Fatalf("unexpected dash url: %s", info.DASHURL)
	}
	if info.MP4URL != "https://cdn.example.com/video.mp4" {
		t.Fatalf("unexpected mp4 url: %s", info.MP4URL)
	}
	if info.CoverURL != "https://example.com/cover.jpg" {
		t.Fatalf("unexpected cover url: %s", info.CoverURL)
	}
}

func TestDiscoverVideoInfoFromArtifactsFindsMediaInJSONPayload(t *testing.T) {
	info := DiscoverVideoInfoFromArtifacts(
		"https://example.com/watch/demo",
		"",
		`{"player":{"videoUrl":"https://cdn.example.com/direct.mp4","dashUrl":"https://cdn.example.com/manifest.mpd","baseUrl":"https://cdn.example.com/video.m4s","pic":"https://cdn.example.com/poster.jpg","desc":"fixture artifact"}}`,
	)
	if info == nil {
		t.Fatal("expected artifact discovery to succeed")
	}
	if info.MP4URL != "https://cdn.example.com/direct.mp4" {
		t.Fatalf("unexpected mp4 url: %s", info.MP4URL)
	}
	if info.DASHURL != "https://cdn.example.com/manifest.mpd" {
		t.Fatalf("unexpected dash url: %s", info.DASHURL)
	}
	if got := info.CoverURL; got != "https://cdn.example.com/poster.jpg" {
		t.Fatalf("unexpected cover url: %s", got)
	}
	if got := info.Description; got != "fixture artifact" {
		t.Fatalf("unexpected description: %s", got)
	}
	foundM4S := false
	for _, candidate := range info.CandidateURLs {
		if candidate == "https://cdn.example.com/video.m4s" {
			foundM4S = true
			break
		}
	}
	if !foundM4S {
		t.Fatalf("expected .m4s baseUrl candidate, got %#v", info.CandidateURLs)
	}
}
