package bilibili

import "testing"

func TestExtractIDsSupportsBVIDAndCID(t *testing.T) {
	extractor := NewBilibiliExtractor()

	bvid, cid, err := extractor.extractIDs("https://www.bilibili.com/video/BV1xx411c7mD?cid=987654")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if bvid != "BV1xx411c7mD" {
		t.Fatalf("unexpected bvid: %s", bvid)
	}
	if cid != "987654" {
		t.Fatalf("unexpected cid: %s", cid)
	}
}

func TestQualityToStringIncludesHighValueFormats(t *testing.T) {
	extractor := NewBilibiliExtractor()

	if actual := extractor.qualityToString(80); actual != "1080P" {
		t.Fatalf("unexpected 80 quality mapping: %s", actual)
	}
	if actual := extractor.qualityToString(120); actual != "4K" {
		t.Fatalf("unexpected 120 quality mapping: %s", actual)
	}
	if actual := extractor.qualityToString(999); actual != "Q999" {
		t.Fatalf("unexpected fallback quality mapping: %s", actual)
	}
}

func TestIsBilibiliURLRecognizesPrimaryDomains(t *testing.T) {
	if !IsBilibiliURL("https://www.bilibili.com/video/BV1demo") {
		t.Fatal("expected bilibili.com url to be recognized")
	}
	if !IsBilibiliURL("https://b23.tv/BV1demo") {
		t.Fatal("expected b23.tv url to be recognized")
	}
	if IsBilibiliURL("https://example.com/video/BV1demo") {
		t.Fatal("did not expect non-bilibili url to be recognized")
	}
}
