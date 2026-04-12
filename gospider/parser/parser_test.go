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
