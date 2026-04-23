package main

import (
	"encoding/json"
	"fmt"
	"strings"

	scrapy "gospider/scrapy"
)

func newEcommerceDetailSpider(siteFamily string) *scrapy.Spider {
	profile := profileForFamily(siteFamily)

	parsePrice := func(response *scrapy.Response) ([]any, error) {
		detail, _ := response.Request.Meta["detail"].(map[string]any)
		var payload []map[string]any
		_ = json.Unmarshal([]byte(response.Text), &payload)
		if len(payload) > 0 {
			detail["price"] = strings.TrimSpace(fmt.Sprint(payload[0]["p"]))
			detail["original_price"] = strings.TrimSpace(fmt.Sprint(payload[0]["op"]))
		}
		return []any{scrapy.NewItem().
			Set("kind", detail["kind"]).
			Set("site_family", detail["site_family"]).
			Set("title", detail["title"]).
			Set("url", detail["url"]).
			Set("item_id", detail["item_id"]).
			Set("price", detail["price"]).
			Set("original_price", detail["original_price"]).
			Set("shop", detail["shop"]).
			Set("review_count", detail["review_count"]).
			Set("image_candidates", detail["image_candidates"]).
			Set("review_url", detail["review_url"]).
			Set("html_excerpt", detail["html_excerpt"]).
			Set("note", detail["note"])}, nil
	}

	return scrapy.NewSpider("ecommerce-detail", func(response *scrapy.Response) ([]any, error) {
		family := siteFamilyFromResponse(response)
		current := profileForFamily(family)
		links := response.XPath("//a/@href").GetAll()
		jsonLDProducts := extractJSONLDProducts(response.Text, 1)
		universalFields := map[string]any{
			"embedded_json_blocks": extractEmbeddedJSONBlocks(response.Text, 5, 2000),
			"api_candidates":       extractAPICandidates(response.Text, 20),
			"script_sources":       response.XPath("//script/@src").GetAll(),
			"json_ld_products":     jsonLDProducts,
			"image_candidates":     collectImageLinks(response.URL, response.XPath("//img/@src").GetAll(), 10),
			"video_candidates":     collectVideoLinks(response.URL, append(response.XPath("//video/@src").GetAll(), response.XPath("//source/@src").GetAll()...), 10),
			"html_excerpt":         excerpt(response.Text, 800),
		}

		if family == "jd" {
			itemID := extractJDItemID(response.URL, response.Text)
			detail := map[string]any{
				"kind":         "jd_detail_product",
				"site_family":  family,
				"title":        bestTitle(response),
				"url":          response.URL,
				"item_id":      itemID,
				"shop":         firstRegexMatch(response.Text, current.ShopPatterns),
				"review_count": firstRegexMatch(response.Text, current.ReviewCountPatterns),
				"review_url":   firstLinkWithKeywords(response.URL, links, current.ReviewLinkKeywords),
				"note":         "Public universal ecommerce detail extraction with JD price fast path.",
			}
			for key, value := range universalFields {
				detail[key] = value
			}
			if itemID != "" {
				request := scrapy.NewRequest(buildJDPriceAPIURL([]string{itemID}), parsePrice).
					SetMeta("detail", detail).
					SetHeader("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36").
					SetHeader("Referer", response.URL)
				return []any{request}, nil
			}
			return []any{scrapy.NewItem().
				Set("kind", detail["kind"]).
				Set("site_family", detail["site_family"]).
				Set("title", detail["title"]).
				Set("url", detail["url"]).
				Set("item_id", detail["item_id"]).
				Set("shop", detail["shop"]).
				Set("review_count", detail["review_count"]).
				Set("image_candidates", detail["image_candidates"]).
				Set("review_url", detail["review_url"]).
				Set("html_excerpt", detail["html_excerpt"]).
				Set("note", detail["note"])}, nil
		}

		if family != "jd" && family != "generic" && len(jsonLDProducts) > 0 {
			product := jsonLDProducts[0]
			return []any{scrapy.NewItem().
				Set("kind", fmt.Sprintf("%s_detail_product", family)).
				Set("site_family", family).
				Set("title", fallbackString(product["name"], bestTitle(response))).
				Set("url", fallbackString(product["url"], response.URL)).
				Set("item_id", fallbackString(product["sku"], firstRegexMatch(response.Text, current.ItemIDPatterns))).
				Set("price", fallbackString(product["price"], firstRegexMatch(response.Text, current.PricePatterns))).
				Set("currency", product["currency"]).
				Set("brand", product["brand"]).
				Set("category", product["category"]).
				Set("rating", fallbackString(product["rating"], firstRegexMatch(response.Text, current.RatingPatterns))).
				Set("review_count", fallbackString(product["review_count"], firstRegexMatch(response.Text, current.ReviewCountPatterns))).
				Set("shop", firstRegexMatch(response.Text, current.ShopPatterns)).
				Set("review_url", firstLinkWithKeywords(response.URL, links, current.ReviewLinkKeywords)).
				Set("embedded_json_blocks", universalFields["embedded_json_blocks"]).
				Set("api_candidates", universalFields["api_candidates"]).
				Set("script_sources", universalFields["script_sources"]).
				Set("json_ld_products", universalFields["json_ld_products"]).
				Set("image_candidates", universalFields["image_candidates"]).
				Set("video_candidates", universalFields["video_candidates"]).
				Set("html_excerpt", universalFields["html_excerpt"]).
				Set("note", "Public ecommerce detail fast path via JSON-LD product extraction.")}, nil
		}

		return []any{
			scrapy.NewItem().
				Set("kind", "ecommerce_detail").
				Set("site_family", family).
				Set("title", bestTitle(response)).
				Set("url", response.URL).
				Set("item_id", firstRegexMatch(response.Text, current.ItemIDPatterns)).
				Set("price", firstRegexMatch(response.Text, current.PricePatterns)).
				Set("shop", firstRegexMatch(response.Text, current.ShopPatterns)).
				Set("review_count", firstRegexMatch(response.Text, current.ReviewCountPatterns)).
				Set("review_url", firstLinkWithKeywords(response.URL, links, current.ReviewLinkKeywords)).
				Set("embedded_json_blocks", universalFields["embedded_json_blocks"]).
				Set("api_candidates", universalFields["api_candidates"]).
				Set("script_sources", universalFields["script_sources"]).
				Set("json_ld_products", universalFields["json_ld_products"]).
				Set("image_candidates", universalFields["image_candidates"]).
				Set("video_candidates", universalFields["video_candidates"]).
				Set("html_excerpt", universalFields["html_excerpt"]).
				Set("note", "Public universal ecommerce detail extraction."),
		}, nil
	}).
		AddStartURL(profile.DetailURL).
		WithStartMeta("site_family", siteFamily).
		WithStartMeta("runner", profile.Runner).
		WithStartHeader("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36").
		WithStartHeader("Referer", "https://www.jd.com/")
}

func fallbackString(value any, fallback string) string {
	text := strings.TrimSpace(fmt.Sprint(value))
	if text == "" || text == "<nil>" {
		return fallback
	}
	return text
}
