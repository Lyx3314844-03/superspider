package core

import (
	"strings"
	"testing"
)

func TestParseCurlCommandSupportsHeadersAndBody(t *testing.T) {
	parsed, err := parseCurlCommand(`curl -X POST "https://example.com/api" -H "Accept: application/json" -d "{\"name\":\"ultra\"}"`)
	if err != nil {
		t.Fatalf("parse failed: %v", err)
	}

	if parsed.Method != "POST" {
		t.Fatalf("expected POST method, got %s", parsed.Method)
	}
	if parsed.URL != "https://example.com/api" {
		t.Fatalf("unexpected url: %s", parsed.URL)
	}
	if parsed.Headers["Accept"] != "application/json" {
		t.Fatalf("unexpected headers: %#v", parsed.Headers)
	}
	if parsed.Data != `{"name":"ultra"}` {
		t.Fatalf("unexpected body: %s", parsed.Data)
	}
}

func TestConvertToRestyUsesParsedCurlCommand(t *testing.T) {
	converter := NewCurlToGoConverter()
	code := converter.ConvertToResty(`curl -X POST "https://example.com/api" -H "Accept: application/json" -d "{\"name\":\"ultra\"}"`)

	if !strings.Contains(code, `req.Execute("POST", "https://example.com/api")`) {
		t.Fatalf("expected parsed request target, got: %s", code)
	}
	if !strings.Contains(code, `"Accept": "application/json"`) {
		t.Fatalf("expected parsed headers, got: %s", code)
	}
	if !strings.Contains(code, `req = req.SetBody("{\"name\":\"ultra\"}")`) {
		t.Fatalf("expected parsed body, got: %s", code)
	}
}
