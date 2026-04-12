package media

import "testing"

func TestParseM3U8KeepsRelativeSegmentURLs(t *testing.T) {
	downloader := NewHLSDownloader(t.TempDir())
	content := "#EXTM3U\n#EXT-X-VERSION:3\n#EXTINF:4,\nseg0.ts\n#EXTINF:4,\nseg1.ts\n#EXT-X-ENDLIST\n"

	playlist, err := downloader.ParseM3U8(content, "http://127.0.0.1:8080/master.m3u8")
	if err != nil {
		t.Fatalf("parse failed: %v", err)
	}
	if len(playlist.MediaSegments) != 2 {
		t.Fatalf("expected 2 segments, got %d", len(playlist.MediaSegments))
	}
	if playlist.MediaSegments[0].URL != "http://127.0.0.1:8080/seg0.ts" {
		t.Fatalf("unexpected first segment url: %s", playlist.MediaSegments[0].URL)
	}
	if playlist.MediaSegments[1].URL != "http://127.0.0.1:8080/seg1.ts" {
		t.Fatalf("unexpected second segment url: %s", playlist.MediaSegments[1].URL)
	}
}
