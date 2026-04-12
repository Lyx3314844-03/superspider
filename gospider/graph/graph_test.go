package graph

import "testing"

func TestBuildFromHTMLExtractsTitleLinksAndImages(t *testing.T) {
	builder := NewBuilder()
	err := builder.BuildFromHTML(`
		<html>
		  <head><title>Go Graph Demo</title></head>
		  <body>
		    <h1>Headline</h1>
		    <a href="https://example.com/page">Read more</a>
		    <img src="https://example.com/image.png" alt="demo" />
		  </body>
		</html>
	`)
	if err != nil {
		t.Fatalf("unexpected build error: %v", err)
	}

	if builder.RootID != "document" {
		t.Fatalf("expected root document, got %q", builder.RootID)
	}
	if len(builder.Links()) != 1 {
		t.Fatalf("expected 1 link edge, got %d", len(builder.Links()))
	}
	if len(builder.Images()) != 1 {
		t.Fatalf("expected 1 image edge, got %d", len(builder.Images()))
	}
	if got := builder.Nodes["title-0"].Text; got != "Go Graph Demo" {
		t.Fatalf("expected title node text, got %q", got)
	}
	if got := builder.Stats()["type_heading"]; got < 1 {
		t.Fatalf("expected at least one heading node, got %d", got)
	}
}
