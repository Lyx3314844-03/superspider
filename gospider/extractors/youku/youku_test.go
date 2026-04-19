package youku

import "testing"

func TestExtractVideoIDSupportsStandardAndEmbedURLs(t *testing.T) {
	extractor := NewYoukuExtractor()

	cases := map[string]string{
		"https://v.youku.com/v_show/id_XNTk4Mjg1MjEzMg==.html": "XNTk4Mjg1MjEzMg==",
		"https://player.youku.com/embed/XMzAwMDAwMDAw":        "XMzAwMDAwMDAw",
	}

	for input, expected := range cases {
		actual, err := extractor.extractVideoID(input)
		if err != nil {
			t.Fatalf("unexpected error for %s: %v", input, err)
		}
		if actual != expected {
			t.Fatalf("unexpected video id for %s: %s", input, actual)
		}
	}
}

func TestExtractMetaTagSupportsNameAndItempropForms(t *testing.T) {
	extractor := NewYoukuExtractor()
	html := `
	<html>
	  <head>
	    <meta name="videoTitle" content="Fixture Youku Title" />
	    <meta itemprop="thumbnail" content="https://img.example.com/poster.jpg" />
	  </head>
	</html>`

	if actual := extractor.extractMetaTag(html, "videoTitle"); actual != "Fixture Youku Title" {
		t.Fatalf("unexpected title meta extraction: %s", actual)
	}
	if actual := extractor.extractMetaTag(html, "thumbnail"); actual != "https://img.example.com/poster.jpg" {
		t.Fatalf("unexpected thumbnail meta extraction: %s", actual)
	}
}
