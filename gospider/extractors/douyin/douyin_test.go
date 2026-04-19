package douyin

import "testing"

func TestExtractVideoIDSupportsKnownPatterns(t *testing.T) {
	cases := map[string]string{
		"https://www.douyin.com/video/123456789":     "123456789",
		"https://www.douyin.com/?modal_id=987654321": "987654321",
	}
	for input, expected := range cases {
		if actual := ExtractVideoID(input); actual != expected {
			t.Fatalf("expected %s, got %s", expected, actual)
		}
	}
}

func TestExtractorSupportsDouyinHost(t *testing.T) {
	if !NewExtractor().Supports("https://www.douyin.com/video/123456789") {
		t.Fatal("expected douyin url to be supported")
	}
}
