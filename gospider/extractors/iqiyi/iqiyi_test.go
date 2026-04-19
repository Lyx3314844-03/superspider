package iqiyi

import "testing"

func TestExtractVideoIDSupportsKnownIqiyiPatterns(t *testing.T) {
	extractor := NewIqiyiExtractor()

	cases := map[string]string{
		"https://www.iqiyi.com/v_19rrn1abcd.html":       "19rrn1abcd",
		"https://www.iqiyi.com/play/19rrn2wxyz":         "19rrn2wxyz",
		"https://www.iqiyi.com/?curid=19rrn3demo&foo=1": "19rrn3demo",
	}

	for input, expected := range cases {
		if actual := extractor.extractVideoID(input); actual != expected {
			t.Fatalf("extractVideoID(%q) = %q, want %q", input, actual, expected)
		}
	}
}

func TestExtractVideoDataFindsStreamsAndMetadata(t *testing.T) {
	extractor := NewIqiyiExtractor()
	info := &VideoInfo{}
	html := `
<html>
  <head>
    <title>示例视频 - 爱奇艺</title>
    <meta property="og:image" content="https://static.example.com/cover.jpg" />
    <script>
      var payload = {
        "duration": 321,
        "quality": ["1080p", "720p"],
        "m3u8Url": "https://media.example.com/master.m3u8",
        "dashUrl": "https://media.example.com/manifest.mpd",
        "streams": [
          {"quality": "1080p", "m3u8Url": "https://media.example.com/master.m3u8"},
          {"quality": "720p", "dashUrl": "https://media.example.com/manifest.mpd"}
        ]
      };
    </script>
  </head>
</html>`

	extractor.extractVideoData(html, info)

	if info.M3U8URL != "https://media.example.com/master.m3u8" {
		t.Fatalf("unexpected m3u8 url: %s", info.M3U8URL)
	}
	if info.DASHURL != "https://media.example.com/manifest.mpd" {
		t.Fatalf("unexpected dash url: %s", info.DASHURL)
	}
	if info.CoverURL != "https://static.example.com/cover.jpg" {
		t.Fatalf("unexpected cover url: %s", info.CoverURL)
	}
	if info.Duration != 321 {
		t.Fatalf("unexpected duration: %d", info.Duration)
	}
	if len(info.QualityOptions) != 2 || info.QualityOptions[0] != "1080p" {
		t.Fatalf("unexpected quality options: %#v", info.QualityOptions)
	}
	if len(info.Streams) != 2 {
		t.Fatalf("unexpected stream candidates: %#v", info.Streams)
	}
	if info.Streams[0].Quality != "1080p" || info.Streams[0].M3U8URL != "https://media.example.com/master.m3u8" {
		t.Fatalf("unexpected first stream: %#v", info.Streams[0])
	}
	if info.Streams[1].Quality != "720p" || info.Streams[1].DASHURL != "https://media.example.com/manifest.mpd" {
		t.Fatalf("unexpected second stream: %#v", info.Streams[1])
	}
}
