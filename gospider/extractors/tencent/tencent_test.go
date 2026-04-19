package tencent

import "testing"

func TestExtractVideoIDSupportsTencentPatterns(t *testing.T) {
	extractor := NewTencentExtractor()

	cases := map[string]string{
		"https://v.qq.com/x/cover/mzc00200abc/demo123.html": "demo123",
		"https://v.qq.com/x/page/demo456.html":              "demo456",
		"https://v.qq.com/x/demo789.html":                   "demo789",
		"https://v.qq.com/x/cover/demo999":                  "demo999",
		"https://v.qq.com/iframe/player.html?vid=demoabc":   "demoabc",
	}

	for input, expected := range cases {
		if actual := extractor.extractVideoID(input); actual != expected {
			t.Fatalf("unexpected video id for %s: %s", input, actual)
		}
	}
}

func TestGetDownloadURLReturnsErrorWhenNoFormatsExist(t *testing.T) {
	extractor := NewTencentExtractor()

	if _, err := extractor.GetDownloadURL("https://example.com/video.html"); err == nil {
		t.Fatal("expected error when url is not a supported tencent video url")
	}
}
