package main

import (
	"fmt"
	"strings"

	scrapy "gospider/scrapy"
)

func newEcommerceReviewSpider(siteFamily string) *scrapy.Spider {
	profile := profileForFamily(siteFamily)
	return scrapy.NewSpider("ecommerce-review", func(response *scrapy.Response) ([]any, error) {
		family := siteFamilyFromResponse(response)
		current := profileForFamily(family)
		jsonLDProducts := extractJSONLDProducts(response.Text, 1)
		universalFields := map[string]any{
			"embedded_json_blocks": extractEmbeddedJSONBlocks(response.Text, 5, 2000),
			"api_candidates":       extractAPICandidates(response.Text, 20),
			"script_sources":       response.XPath("//script/@src").GetAll(),
			"json_ld_products":     jsonLDProducts,
			"video_candidates":     collectVideoLinks(response.URL, append(response.XPath("//video/@src").GetAll(), response.XPath("//source/@src").GetAll()...), 10),
			"excerpt":              excerpt(response.Text, 800),
		}

		if family == "jd" {
			payload := safeJSONMap(response.Text)
			commentsPreview := []map[string]any{}
			if comments, ok := payload["comments"].([]any); ok {
				for _, raw := range comments {
					comment, ok := raw.(map[string]any)
					if !ok {
						continue
					}
					commentsPreview = append(commentsPreview, map[string]any{
						"id":       comment["id"],
						"score":    comment["score"],
						"nickname": comment["nickname"],
						"content":  excerpt(fmt.Sprint(comment["content"]), 120),
					})
					if len(commentsPreview) >= 5 {
						break
					}
				}
			}
			itemID := strings.TrimSpace(fmt.Sprint(payload["productId"]))
			if itemID == "" {
				itemID = extractJDItemID(response.URL, response.Text)
			}
			return []any{
				scrapy.NewItem().
					Set("kind", "jd_review_summary").
					Set("site_family", family).
					Set("url", response.URL).
					Set("item_id", itemID).
					Set("rating", firstRegexMatch(response.Text, current.RatingPatterns)).
					Set("review_count", fmt.Sprint(payload["maxPage"])).
					Set("max_page", payload["maxPage"]).
					Set("comments_preview", commentsPreview).
					Set("embedded_json_blocks", universalFields["embedded_json_blocks"]).
					Set("api_candidates", universalFields["api_candidates"]).
					Set("script_sources", universalFields["script_sources"]).
					Set("json_ld_products", universalFields["json_ld_products"]).
					Set("video_candidates", universalFields["video_candidates"]).
					Set("excerpt", universalFields["excerpt"]).
					Set("note", "Public universal ecommerce review extraction with JD review fast path."),
			}, nil
		}

		if family != "jd" && family != "generic" && len(jsonLDProducts) > 0 {
			product := jsonLDProducts[0]
			return []any{
				scrapy.NewItem().
					Set("kind", fmt.Sprintf("%s_review_summary", family)).
					Set("site_family", family).
					Set("url", response.URL).
					Set("item_id", fallbackString(product["sku"], firstRegexMatch(response.Text, current.ItemIDPatterns))).
					Set("rating", fallbackString(product["rating"], firstRegexMatch(response.Text, current.RatingPatterns))).
					Set("review_count", fallbackString(product["review_count"], firstRegexMatch(response.Text, current.ReviewCountPatterns))).
					Set("brand", product["brand"]).
					Set("category", product["category"]).
					Set("embedded_json_blocks", universalFields["embedded_json_blocks"]).
					Set("api_candidates", universalFields["api_candidates"]).
					Set("script_sources", universalFields["script_sources"]).
					Set("json_ld_products", universalFields["json_ld_products"]).
					Set("video_candidates", universalFields["video_candidates"]).
					Set("excerpt", universalFields["excerpt"]).
					Set("note", "Public ecommerce review fast path via JSON-LD aggregate rating extraction."),
			}, nil
		}

		return []any{
			scrapy.NewItem().
				Set("kind", "ecommerce_review").
				Set("site_family", family).
				Set("url", response.URL).
				Set("item_id", firstRegexMatch(response.Text, current.ItemIDPatterns)).
				Set("rating", firstRegexMatch(response.Text, current.RatingPatterns)).
				Set("review_count", firstRegexMatch(response.Text, current.ReviewCountPatterns)).
				Set("review_id_candidates", collectRegexMatches(response.Text, []string{`(?:commentId|reviewId|id)["'=:\s]+([A-Za-z0-9_-]+)`}, 10)).
				Set("embedded_json_blocks", universalFields["embedded_json_blocks"]).
				Set("api_candidates", universalFields["api_candidates"]).
				Set("script_sources", universalFields["script_sources"]).
				Set("json_ld_products", universalFields["json_ld_products"]).
				Set("video_candidates", universalFields["video_candidates"]).
				Set("excerpt", universalFields["excerpt"]).
				Set("note", "Public universal ecommerce review extraction."),
		}, nil
	}).
		AddStartURL(profile.ReviewURL).
		WithStartMeta("site_family", siteFamily).
		WithStartMeta("runner", profile.Runner).
		WithStartHeader("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36").
		WithStartHeader("Referer", "https://item.jd.com/100000000000.html")
}
