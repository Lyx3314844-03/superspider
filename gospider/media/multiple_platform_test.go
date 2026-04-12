package media

import "testing"

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
		`{"player":{"videoUrl":"https://cdn.example.com/direct.mp4","dashUrl":"https://cdn.example.com/manifest.mpd"}}`,
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
}
