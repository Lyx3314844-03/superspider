package main

import (
	"fmt"
	scrapy "gospider/scrapy"
	"strings"
	"testing"
)

func TestProfileForFamilyFallsBackToGenericForUnknownFamily(t *testing.T) {
	profile := profileForFamily("unknown-shop")
	if profile.Family != "generic" {
		t.Fatalf("expected generic fallback, got %q", profile.Family)
	}
}

func TestProfileForFamilySupportsSocialCommerceFamilies(t *testing.T) {
	if got := profileForFamily("xiaohongshu").Family; got != "xiaohongshu" {
		t.Fatalf("expected xiaohongshu profile, got %q", got)
	}
	if got := profileForFamily("douyin-shop").Family; got != "douyin-shop" {
		t.Fatalf("expected douyin-shop profile, got %q", got)
	}
}

func TestSiteFamilyFromResponseRecognizesSocialCommerceHosts(t *testing.T) {
	resp := &scrapy.Response{URL: "https://www.xiaohongshu.com/explore/demo"}
	if got := siteFamilyFromResponse(resp); got != "xiaohongshu" {
		t.Fatalf("expected xiaohongshu family, got %q", got)
	}

	resp = &scrapy.Response{URL: "https://haohuo.jinritemai.com/views/product/item2?id=1"}
	if got := siteFamilyFromResponse(resp); got != "douyin-shop" {
		t.Fatalf("expected douyin-shop family, got %q", got)
	}
}

func TestExtractBootstrapProductsFindsProductFromNextData(t *testing.T) {
	html := `<html><head><script type="application/json">{"sku":"SKU-1","name":"Demo Phone","price":"6999","image":"https://cdn.example.com/p1.jpg","shopName":"Demo Shop","aggregateRating":{"ratingValue":"4.9","reviewCount":"123"}}</script></head></html>`
	products := extractBootstrapProducts(html, 5)
	if len(products) == 0 {
		t.Fatal("expected bootstrap products to be extracted")
	}
	if got := strings.TrimSpace(fmt.Sprint(products[0]["sku"])); got != "SKU-1" {
		t.Fatalf("expected SKU-1, got %q", got)
	}
	if got := strings.TrimSpace(fmt.Sprint(products[0]["price"])); got != "6999" {
		t.Fatalf("expected price 6999, got %q", got)
	}
}

func TestExtractAPICandidatesFindsCandidatesFromEmbeddedJSON(t *testing.T) {
	html := `<html><head><script type="application/json">{"detailApi":"api/item/detail?id=1","reviewApi":"/api/review/list?sku=1"}</script></head></html>`
	candidates := extractAPICandidates(html, 10)
	if len(candidates) == 0 {
		t.Fatal("expected api candidates")
	}
	found := false
	for _, candidate := range candidates {
		if candidate == "api/item/detail?id=1" {
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("expected api/item/detail?id=1 in candidates, got %#v", candidates)
	}
}

func TestBuildAPIJobTemplatesBuildsReplayableJobs(t *testing.T) {
	templates := buildAPIJobTemplates(
		"https://shop.example.com/item/sku-1",
		"generic",
		[]string{"api/item/detail?id=1"},
		[]string{"SKU-1"},
		10,
	)
	if len(templates) == 0 {
		t.Fatal("expected api job templates")
	}
	if templates[0]["runtime"] != "http" {
		t.Fatalf("expected http runtime, got %#v", templates[0])
	}
}

func TestBuildNetworkReplayJobTemplatesFromArtifact(t *testing.T) {
	artifact := `{"network_events":[
		{"url":"https://shop.example.com/_next/static/app.js","method":"GET","status":200,"resource_type":"script"},
		{"url":"https://shop.example.com/api/item/detail?id=1","method":"POST","status":200,"resource_type":"fetch","request_headers":{"Content-Type":"application/json","Cookie":"session=secret"},"post_data":"{\"sku\":\"SKU-1\"}","response_headers":{"content-type":"application/json"}}
	]}`

	entries := normalizeNetworkEntries(artifact, 10)
	if len(entries) != 2 {
		t.Fatalf("expected normalized network entries, got %#v", entries)
	}
	candidates := extractNetworkAPICandidates(artifact, 10)
	if len(candidates) != 1 || candidates[0] != "https://shop.example.com/api/item/detail?id=1" {
		t.Fatalf("unexpected network api candidates: %#v", candidates)
	}
	templates := buildNetworkReplayJobTemplates("https://shop.example.com/item/sku-1", "generic", artifact, 10)
	if len(templates) != 1 {
		t.Fatalf("expected one replay template, got %#v", templates)
	}
	target, _ := templates[0]["target"].(map[string]any)
	if target["method"] != "POST" {
		t.Fatalf("expected POST replay target, got %#v", target)
	}
	if target["body"] != `{"sku":"SKU-1"}` {
		t.Fatalf("expected request body to be preserved, got %#v", target)
	}
	headers, _ := target["headers"].(map[string]any)
	if _, ok := headers["Cookie"]; ok {
		t.Fatalf("expected sensitive cookie header to be omitted, got %#v", headers)
	}
}

func TestUniversalEcommerceDetectorIdentifiesMarketplaceAndJSONLD(t *testing.T) {
	html := `<script type="application/ld+json">{"@type":"Product","name":"Demo","offers":{"price":"9.99","priceCurrency":"USD"}}</script><button>Add to cart</button>`
	result := DetectEcommerceSite("https://www.amazon.com/dp/B0TEST", html)
	if !result.IsEcommerce {
		t.Fatal("expected ecommerce detection")
	}
	if result.SiteFamily != "amazon" {
		t.Fatalf("expected amazon site family, got %q", result.SiteFamily)
	}
	if !result.HasJSONLD {
		t.Fatal("expected JSON-LD signal")
	}
}
