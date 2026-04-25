package parser

import "testing"

func TestXPathFirstStrictSupportsSafeSubset(t *testing.T) {
	parser := NewHTMLParser(`<html><a href="/docs">Docs</a></html>`)
	value, err := parser.XPathFirstStrict("//a/@href")
	if err != nil {
		t.Fatalf("unexpected xpath error: %v", err)
	}
	if value != "/docs" {
		t.Fatalf("unexpected xpath value: %q", value)
	}
}

func TestXPathFirstStrictSupportsFullXPath(t *testing.T) {
	parser := NewHTMLParser(`<html><div><span>One</span><span>Two</span></div></html>`)
	value, err := parser.XPathFirstStrict("//div/span[2]/text()")
	if err != nil {
		t.Fatalf("unexpected xpath error: %v", err)
	}
	if value != "Two" {
		t.Fatalf("unexpected xpath value: %q", value)
	}
}

func TestSelectorExtractorSupportsComplexCSSAndXPath(t *testing.T) {
	html := `<html><body>
		<article class="product" data-sku="A1"><h2><span>Alpha</span></h2><a class="buy" href="/alpha">Buy</a></article>
		<article class="product featured" data-sku="B2"><h2><span>Beta</span></h2><a class="buy" href="/beta">Buy</a></article>
	</body></html>`

	result, err := NewSelectorExtractor().Extract(html, []ExtractRule{
		{Field: "names", Type: "css", Expr: "article.product > h2 span::text", All: true},
		{Field: "featured_sku", Type: "xpath", Expr: "//article[contains(@class, 'featured')]/@data-sku"},
		{Field: "links", Type: "css", Expr: "article.product a.buy::attr(href)", All: true},
	})
	if err != nil {
		t.Fatalf("unexpected extract error: %v", err)
	}

	names := result["names"].([]string)
	if len(names) != 2 || names[0] != "Alpha" || names[1] != "Beta" {
		t.Fatalf("unexpected names: %#v", names)
	}
	if result["featured_sku"] != "B2" {
		t.Fatalf("unexpected featured sku: %#v", result["featured_sku"])
	}
	links := result["links"].([]string)
	if len(links) != 2 || links[0] != "/alpha" || links[1] != "/beta" {
		t.Fatalf("unexpected links: %#v", links)
	}
}

func TestLocatorAnalyzerBuildsCssAndXPathCandidates(t *testing.T) {
	html := `<html><body><form>
		<input id="search-box" name="q" placeholder="Search products">
		<button data-testid="submit-search">Search</button>
	</form></body></html>`

	plan, err := NewLocatorAnalyzer().Analyze(html, LocatorTarget{Name: "q"})
	if err != nil {
		t.Fatalf("unexpected analyze error: %v", err)
	}
	expressions := map[string]bool{}
	for _, candidate := range plan.Candidates {
		expressions[candidate.Kind+" "+candidate.Expr] = true
	}
	if !expressions["css #search-box"] {
		t.Fatalf("expected css id candidate, got %#v", plan.Candidates)
	}
	if !expressions["xpath //input[@name='q']"] {
		t.Fatalf("expected xpath name candidate, got %#v", plan.Candidates)
	}
}

func TestDevToolsAnalyzerSnapshotsElementsAndSelectsNodeReverseRoute(t *testing.T) {
	html := `<html><body>
		<input id="kw" name="q">
		<script src="/static/app.js"></script>
		<script>const token = CryptoJS.MD5(window.navigator.userAgent).toString();</script>
	</body></html>`

	report, err := NewDevToolsAnalyzer().Analyze(html, []DevToolsNetworkArtifact{
		{URL: "https://example.com/api/search?sign=abc", Method: "GET", Status: 200, ResourceType: "xhr"},
	}, nil)
	if err != nil {
		t.Fatalf("unexpected analyze error: %v", err)
	}
	if len(report.Elements) < 3 {
		t.Fatalf("expected element snapshots, got %#v", report.Elements)
	}
	if route := report.BestReverseRoute(); route == nil || route.Kind != "analyze_crypto" {
		t.Fatalf("expected analyze_crypto route, got %#v", route)
	}
}
