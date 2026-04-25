package main

import (
	"encoding/json"
	"fmt"
	"strings"

	scrapy "gospider/scrapy"
)

func newEcommerceCatalogSpider(siteFamily string) *scrapy.Spider {
	profile := profileForFamily(siteFamily)

	parsePrices := func(response *scrapy.Response) ([]any, error) {
		metaProducts, _ := response.Request.Meta["products"].([]map[string]any)
		sourceURL, _ := response.Request.Meta["source_url"].(string)
		family, _ := response.Request.Meta["site_family"].(string)

		priceMap := map[string]map[string]string{}
		var payload []map[string]any
		_ = json.Unmarshal([]byte(response.Text), &payload)
		for _, item := range payload {
			skuID := strings.TrimSpace(fmt.Sprint(item["id"]))
			if skuID == "" {
				continue
			}
			priceMap[skuID] = map[string]string{
				"price":          strings.TrimSpace(fmt.Sprint(item["p"])),
				"original_price": strings.TrimSpace(fmt.Sprint(item["op"])),
			}
		}

		results := make([]any, 0, len(metaProducts))
		for _, product := range metaProducts {
			skuID := fmt.Sprint(product["product_id"])
			priceInfo := priceMap[skuID]
			results = append(results, scrapy.NewItem().
				Set("kind", "jd_catalog_product").
				Set("site_family", family).
				Set("source_url", sourceURL).
				Set("product_id", skuID).
				Set("name", product["name"]).
				Set("url", product["url"]).
				Set("image_url", product["image_url"]).
				Set("comment_count", product["comment_count"]).
				Set("price", priceInfo["price"]).
				Set("original_price", priceInfo["original_price"]))
		}
		return results, nil
	}

	return scrapy.NewSpider("ecommerce-catalog", func(response *scrapy.Response) ([]any, error) {
		family := siteFamilyFromResponse(response)
		current := profileForFamily(family)
		links := response.XPath("//a/@href").GetAll()
		jsonLDProducts := extractJSONLDProducts(response.Text, 5)
		bootstrapProducts := extractBootstrapProducts(response.Text, 5)
		networkArtifact := networkArtifactFromResponse(response)
		networkEntries := normalizeNetworkEntries(networkArtifact, 50)
		networkAPICandidates := extractNetworkAPICandidates(networkEntries, 20)
		apiCandidates := appendUniqueStrings(20, extractAPICandidates(response.Text, 20), networkAPICandidates)
		networkReplayTemplates := buildNetworkReplayJobTemplates(response.URL, family, networkEntries, 10)
		summary := scrapy.NewItem().
			Set("coupons_promotions", DetectCouponsPromotions(response.Text)).
			Set("stock_status", ExtractStockStatus(response.Text)).
			Set("kind", map[bool]string{true: "jd_catalog_page", false: "ecommerce_catalog_page"}[family == "jd"]).
			Set("site_family", family).
			Set("runner", current.Runner).
			Set("title", bestTitle(response)).
			Set("url", response.URL).
			Set("product_link_candidates", collectProductLinks(response.URL, links, current, 20)).
			Set("next_page", firstLinkWithKeywords(response.URL, links, current.NextLinkKeywords)).
			Set("sku_candidates", collectRegexMatches(response.Text, current.ItemIDPatterns, 10)).
			Set("price_excerpt", firstRegexMatch(response.Text, current.PricePatterns)).
			Set("image_candidates", collectImageLinks(response.URL, response.XPath("//img/@src").GetAll(), 10)).
			Set("video_candidates", collectVideoLinks(response.URL, append(response.XPath("//video/@src").GetAll(), response.XPath("//source/@src").GetAll()...), 10)).
			Set("script_sources", response.XPath("//script/@src").GetAll()).
			Set("api_candidates", apiCandidates).
			Set("network_entries", networkEntries).
			Set("network_api_candidates", networkAPICandidates).
			Set("network_replay_job_templates", networkReplayTemplates).
			Set("embedded_json_blocks", extractEmbeddedJSONBlocks(response.Text, 5, 2000)).
			Set("json_ld_products", jsonLDProducts).
			Set("bootstrap_products", bootstrapProducts).
			Set("page_excerpt", excerpt(response.Text, 800)).
			Set("note", "Public universal ecommerce catalog page extraction.")
		summary = summary.Set(
			"api_job_templates",
			mergeAPIJobTemplates(
				20,
				buildAPIJobTemplates(
					response.URL,
					family,
					apiCandidates,
					collectRegexMatches(response.Text, current.ItemIDPatterns, 10),
					10,
				),
				networkReplayTemplates,
			),
		)

		if family == "jd" {
			products := extractJDCatalogProducts(response.Text)
			if len(products) > 0 {
				request := scrapy.NewRequest(buildJDPriceAPIURL(collectProductIDs(products)), parsePrices).
					SetMeta("site_family", family).
					SetMeta("source_url", response.URL).
					SetMeta("products", products).
					SetHeader("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36").
					SetHeader("Referer", response.URL)
				return []any{summary, request}, nil
			}
		}

		structuredProducts := jsonLDProducts
		if len(structuredProducts) == 0 {
			structuredProducts = bootstrapProducts
		}
		if family != "jd" && len(structuredProducts) > 0 {
			results := []any{summary}
			productLinks, _ := summary["product_link_candidates"].([]string)
			skuCandidates, _ := summary["sku_candidates"].([]string)
			for index, product := range structuredProducts {
				productID := strings.TrimSpace(fmt.Sprint(product["sku"]))
				if productID == "" && len(skuCandidates) > 0 {
					productID = skuCandidates[0]
				}
				productURL := strings.TrimSpace(fmt.Sprint(product["url"]))
				if productURL == "" && index < len(productLinks) {
					productURL = productLinks[index]
				}
				results = append(results, scrapy.NewItem().
					Set("kind", map[bool]string{true: "ecommerce_catalog_product", false: fmt.Sprintf("%s_catalog_product", family)}[family == "generic"]).
					Set("site_family", family).
					Set("source_url", response.URL).
					Set("product_id", productID).
					Set("name", product["name"]).
					Set("url", productURL).
					Set("image_url", product["image"]).
					Set("brand", product["brand"]).
					Set("category", product["category"]).
					Set("price", product["price"]).
					Set("currency", product["currency"]).
					Set("rating", product["rating"]).
					Set("review_count", product["review_count"]).
					Set("shop", product["shop"]).
					Set("network_entries", networkEntries).
					Set("network_api_candidates", networkAPICandidates).
					Set("network_replay_job_templates", networkReplayTemplates).
					Set(
						"api_job_templates",
						mergeAPIJobTemplates(
							20,
							buildAPIJobTemplates(
								response.URL,
								family,
								apiCandidates,
								[]string{productID},
								10,
							),
							networkReplayTemplates,
						),
					))
			}
			return results, nil
		}

		return []any{summary}, nil
	}).
		AddStartURL(profile.CatalogURL).
		WithStartMeta("site_family", siteFamily).
		WithStartMeta("runner", profile.Runner).
		WithStartHeader("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36").
		WithStartHeader("Referer", "https://www.jd.com/")
}

func collectProductIDs(products []map[string]any) []string {
	values := make([]string, 0, len(products))
	for _, product := range products {
		values = append(values, fmt.Sprint(product["product_id"]))
	}
	return values
}
