package main

import (
	"encoding/json"
	"net/url"
	"regexp"
	"strconv"
	"strings"

	scrapy "gospider/scrapy"
)

const defaultSiteFamily = "jd"

type ecommerceProfile struct {
	Family              string
	CatalogURL          string
	DetailURL           string
	ReviewURL           string
	Runner              string
	DetailLinkKeywords  []string
	NextLinkKeywords    []string
	ReviewLinkKeywords  []string
	PricePatterns       []string
	ItemIDPatterns      []string
	ShopPatterns        []string
	ReviewCountPatterns []string
	RatingPatterns      []string
}

func profileForFamily(siteFamily string) ecommerceProfile {
	switch strings.ToLower(siteFamily) {
	case "generic":
		return ecommerceProfile{
			Family:              "generic",
			CatalogURL:          "https://shop.example.com/search?q=demo",
			DetailURL:           "https://shop.example.com/product/demo-item",
			ReviewURL:           "https://shop.example.com/product/demo-item/reviews",
			Runner:              "browser",
			DetailLinkKeywords:  []string{"/product", "/item", "/goods", "/sku", "detail", "productId", "itemId"},
			NextLinkKeywords:    []string{"page=", "next", "pagination", "load-more"},
			ReviewLinkKeywords:  []string{"review", "reviews", "comment", "comments", "rating"},
			PricePatterns:       []string{`(?:price|salePrice|currentPrice|finalPrice|minPrice|maxPrice|offerPrice)["'=:\s]+([0-9]+(?:\.[0-9]{1,2})?)`, `(?:￥|¥|\$|€|£)\s*([0-9]+(?:\.[0-9]{1,2})?)`},
			ItemIDPatterns:      []string{`(?:skuId|sku|wareId|productId|itemId|goods_id|goodsId|asin)["'=:\s]+([A-Za-z0-9_-]+)`},
			ShopPatterns:        []string{`(?:shopName|seller|sellerNick|storeName|merchantName|vendor|brand)["'=:\s]+([^"'\\n<,}]+)`},
			ReviewCountPatterns: []string{`(?:reviewCount|commentCount|comments|ratingsTotal|totalReviewCount)["'=:\s]+([0-9]+)`},
			RatingPatterns:      []string{`(?:rating|score|ratingValue|averageRating)["'=:\s]+([0-9]+(?:\.[0-9])?)`},
		}
	case "taobao":
		return ecommerceProfile{
			Family:              "taobao",
			CatalogURL:          "https://s.taobao.com/search?q=iphone",
			DetailURL:           "https://item.taobao.com/item.htm?id=100000000000",
			ReviewURL:           "https://rate.taobao.com/detailCommon.htm?id=100000000000",
			Runner:              "browser",
			DetailLinkKeywords:  []string{"item.taobao.com", "item.htm", "id=", "detail"},
			NextLinkKeywords:    []string{"page=", "next"},
			ReviewLinkKeywords:  []string{"review", "rate.taobao.com", "comment"},
			PricePatterns:       []string{`(?:price|promotionPrice|minPrice)["'=:\s]+([0-9]+(?:\.[0-9]{1,2})?)`, `(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)`},
			ItemIDPatterns:      []string{`(?:itemId|item_id|id)["'=:\s]+([A-Za-z0-9_-]+)`},
			ShopPatterns:        []string{`(?:shopName|sellerNick|nick)["'=:\s]+([^"'\\n<,}]+)`},
			ReviewCountPatterns: []string{`(?:reviewCount|commentCount|rateTotal)["'=:\s]+([0-9]+)`},
			RatingPatterns:      []string{`(?:score|rating)["'=:\s]+([0-9]+(?:\.[0-9])?)`},
		}
	case "tmall":
		return ecommerceProfile{
			Family:              "tmall",
			CatalogURL:          "https://list.tmall.com/search_product.htm?q=iphone",
			DetailURL:           "https://detail.tmall.com/item.htm?id=100000000000",
			ReviewURL:           "https://rate.tmall.com/list_detail_rate.htm?itemId=100000000000",
			Runner:              "browser",
			DetailLinkKeywords:  []string{"detail.tmall.com", "item.htm", "id=", "detail"},
			NextLinkKeywords:    []string{"page=", "next"},
			ReviewLinkKeywords:  []string{"review", "rate.tmall.com", "comment"},
			PricePatterns:       []string{`(?:price|promotionPrice|minPrice)["'=:\s]+([0-9]+(?:\.[0-9]{1,2})?)`, `(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)`},
			ItemIDPatterns:      []string{`(?:itemId|item_id|id)["'=:\s]+([A-Za-z0-9_-]+)`},
			ShopPatterns:        []string{`(?:shopName|sellerNick|shop)["'=:\s]+([^"'\\n<,}]+)`},
			ReviewCountPatterns: []string{`(?:reviewCount|commentCount|rateTotal)["'=:\s]+([0-9]+)`},
			RatingPatterns:      []string{`(?:score|rating)["'=:\s]+([0-9]+(?:\.[0-9])?)`},
		}
	case "pinduoduo":
		return ecommerceProfile{
			Family:              "pinduoduo",
			CatalogURL:          "https://mobile.yangkeduo.com/search_result.html?search_key=iphone",
			DetailURL:           "https://mobile.yangkeduo.com/goods.html?goods_id=100000000000",
			ReviewURL:           "https://mobile.yangkeduo.com/proxy/api/reviews/100000000000",
			Runner:              "browser",
			DetailLinkKeywords:  []string{"goods.html", "goods_id=", "product", "detail"},
			NextLinkKeywords:    []string{"page=", "next"},
			ReviewLinkKeywords:  []string{"review", "comment"},
			PricePatterns:       []string{`(?:minPrice|price|groupPrice)["'=:\s]+([0-9]+(?:\.[0-9]{1,2})?)`, `(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)`},
			ItemIDPatterns:      []string{`(?:goods_id|goodsId|skuId)["'=:\s]+([A-Za-z0-9_-]+)`},
			ShopPatterns:        []string{`(?:mall_name|storeName|shopName)["'=:\s]+([^"'\\n<,}]+)`},
			ReviewCountPatterns: []string{`(?:reviewCount|commentCount)["'=:\s]+([0-9]+)`},
			RatingPatterns:      []string{`(?:score|rating)["'=:\s]+([0-9]+(?:\.[0-9])?)`},
		}
	case "amazon":
		return ecommerceProfile{
			Family:              "amazon",
			CatalogURL:          "https://www.amazon.com/s?k=iphone",
			DetailURL:           "https://www.amazon.com/dp/B0EXAMPLE00",
			ReviewURL:           "https://www.amazon.com/product-reviews/B0EXAMPLE00",
			Runner:              "browser",
			DetailLinkKeywords:  []string{"/dp/", "/gp/product/", "/product/", "asin"},
			NextLinkKeywords:    []string{"page=", "next"},
			ReviewLinkKeywords:  []string{"review", "product-reviews"},
			PricePatterns:       []string{`(?:priceToPay|displayPrice|priceAmount)["'=:\s]+([0-9]+(?:\.[0-9]{1,2})?)`, `\$\s*([0-9]+(?:\.[0-9]{1,2})?)`},
			ItemIDPatterns:      []string{`(?:asin|parentAsin|sku)["'=:\s]+([A-Za-z0-9_-]+)`},
			ShopPatterns:        []string{`(?:seller|merchantName|bylineInfo)["'=:\s]+([^"'\\n<,}]+)`},
			ReviewCountPatterns: []string{`(?:reviewCount|totalReviewCount)["'=:\s]+([0-9]+)`},
			RatingPatterns:      []string{`(?:averageRating|rating)["'=:\s]+([0-9]+(?:\.[0-9])?)`},
		}
	default:
		return ecommerceProfile{
			Family:              "jd",
			CatalogURL:          "https://search.jd.com/Search?keyword=iphone",
			DetailURL:           "https://item.jd.com/100000000000.html",
			ReviewURL:           "https://club.jd.com/comment/productPageComments.action?productId=100000000000&score=0&sortType=5&page=0&pageSize=10&isShadowSku=0&fold=1",
			Runner:              "browser",
			DetailLinkKeywords:  []string{"item.jd.com", "sku=", "wareId=", "item.htm", "detail"},
			NextLinkKeywords:    []string{"page=", "pn-next", "next"},
			ReviewLinkKeywords:  []string{"comment", "review", "club.jd.com"},
			PricePatterns:       []string{`"p"\s*:\s*"([0-9]+(?:\.[0-9]{1,2})?)"`, `(?:price|jdPrice|promotionPrice)["'=:\s]+([0-9]+(?:\.[0-9]{1,2})?)`, `(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)`},
			ItemIDPatterns:      []string{`(?:skuId|sku|wareId|productId)["'=:\s]+([A-Za-z0-9_-]+)`},
			ShopPatterns:        []string{`(?:shopName|venderName|storeName)["'=:\s]+([^"'\\n<,}]+)`},
			ReviewCountPatterns: []string{`(?:commentCount|comment_num|reviewCount)["'=:\s]+([0-9]+)`},
			RatingPatterns:      []string{`(?:score|rating)["'=:\s]+([0-9]+(?:\.[0-9])?)`},
		}
	}
}

func firstRegexMatch(text string, patterns []string) string {
	for _, pattern := range patterns {
		re := regexp.MustCompile(`(?i)` + pattern)
		match := re.FindStringSubmatch(text)
		if len(match) > 1 {
			return strings.TrimSpace(match[1])
		}
	}
	return ""
}

func collectRegexMatches(text string, patterns []string, limit int) []string {
	values := make([]string, 0, limit)
	seen := map[string]bool{}
	for _, pattern := range patterns {
		re := regexp.MustCompile(`(?i)` + pattern)
		matches := re.FindAllStringSubmatch(text, -1)
		for _, match := range matches {
			if len(match) < 2 {
				continue
			}
			value := strings.TrimSpace(match[1])
			if value == "" || seen[value] {
				continue
			}
			seen[value] = true
			values = append(values, value)
			if len(values) >= limit {
				return values
			}
		}
	}
	return values
}

func normalizeLinks(baseURL string, links []string) []string {
	values := make([]string, 0, len(links))
	seen := map[string]bool{}
	base, _ := url.Parse(baseURL)
	for _, link := range links {
		link = strings.TrimSpace(link)
		if link == "" {
			continue
		}
		absolute := link
		if base != nil {
			if ref, err := url.Parse(link); err == nil {
				absolute = base.ResolveReference(ref).String()
			}
		}
		if !strings.HasPrefix(absolute, "http://") && !strings.HasPrefix(absolute, "https://") {
			continue
		}
		if !seen[absolute] {
			seen[absolute] = true
			values = append(values, absolute)
		}
	}
	return values
}

func collectProductLinks(baseURL string, links []string, profile ecommerceProfile, limit int) []string {
	values := make([]string, 0, limit)
	for _, link := range normalizeLinks(baseURL, links) {
		lowered := strings.ToLower(link)
		for _, keyword := range profile.DetailLinkKeywords {
			if strings.Contains(lowered, strings.ToLower(keyword)) {
				values = append(values, link)
				break
			}
		}
		if len(values) >= limit {
			break
		}
	}
	return values
}

func collectImageLinks(baseURL string, links []string, limit int) []string {
	values := make([]string, 0, limit)
	for _, link := range normalizeLinks(baseURL, links) {
		lowered := strings.ToLower(link)
		if strings.Contains(lowered, "image") ||
			strings.HasSuffix(lowered, ".jpg") ||
			strings.HasSuffix(lowered, ".jpeg") ||
			strings.HasSuffix(lowered, ".png") ||
			strings.HasSuffix(lowered, ".webp") ||
			strings.HasSuffix(lowered, ".gif") {
			values = append(values, link)
		}
		if len(values) >= limit {
			break
		}
	}
	return values
}

func firstLinkWithKeywords(baseURL string, links []string, keywords []string) string {
	for _, link := range normalizeLinks(baseURL, links) {
		lowered := strings.ToLower(link)
		for _, keyword := range keywords {
			if strings.Contains(lowered, strings.ToLower(keyword)) {
				return link
			}
		}
	}
	return ""
}

func siteFamilyFromResponse(response *scrapy.Response) string {
	if response != nil && response.Request != nil {
		if raw, ok := response.Request.Meta["site_family"].(string); ok && raw != "" {
			return raw
		}
	}
	lowered := ""
	if response != nil {
		lowered = strings.ToLower(response.URL)
	}
	switch {
	case strings.Contains(lowered, "taobao.com"):
		return "taobao"
	case strings.Contains(lowered, "tmall.com"):
		return "tmall"
	case strings.Contains(lowered, "yangkeduo.com") || strings.Contains(lowered, "pinduoduo.com"):
		return "pinduoduo"
	case strings.Contains(lowered, "amazon.com"):
		return "amazon"
	default:
		return "generic"
	}
}

func bestTitle(response *scrapy.Response) string {
	title := strings.TrimSpace(response.CSS("title").Get())
	if title != "" {
		return title
	}
	return strings.TrimSpace(response.CSS("h1").Get())
}

func excerpt(text string, limit int) string {
	normalized := strings.Join(strings.Fields(text), " ")
	if len(normalized) <= limit {
		return normalized
	}
	return normalized[:limit]
}

func buildJDPriceAPIURL(skuIDs []string) string {
	return "https://p.3.cn/prices/mgets?skuIds=" + strings.Join(skuIDs, ",") + "&type=1&area=1_72_4137_0"
}

func buildJDReviewAPIURL(productID string) string {
	return "https://club.jd.com/comment/productPageComments.action?productId=" + productID + "&score=0&sortType=5&page=0&pageSize=10&isShadowSku=0&fold=1"
}

func extractJDItemID(urlText string, html string) string {
	re := regexp.MustCompile(`/(\d+)\.html`)
	if match := re.FindStringSubmatch(urlText); len(match) > 1 {
		return match[1]
	}
	return firstRegexMatch(html, []string{
		`(?:skuId|sku|wareId|productId)["'=:\s]+([A-Za-z0-9_-]+)`,
		`"sku"\s*:\s*"(\d+)"`,
	})
}

func extractJDCatalogProducts(html string) []map[string]any {
	values := []map[string]any{}
	seen := map[string]bool{}
	skuRegex := regexp.MustCompile(`data-sku="(\d+)"`)
	for _, match := range skuRegex.FindAllStringSubmatch(html, -1) {
		if len(match) < 2 {
			continue
		}
		skuID := match[1]
		if seen[skuID] {
			continue
		}
		seen[skuID] = true

		nameRegex := regexp.MustCompile(`(?is)data-sku="` + regexp.QuoteMeta(skuID) + `"[\s\S]*?<em[^>]*>(.*?)</em>`)
		imageRegex := regexp.MustCompile(`(?is)data-sku="` + regexp.QuoteMeta(skuID) + `"[\s\S]*?(?:data-lazy-img|src)="//([^"]+)"`)
		commentRegex := regexp.MustCompile(`(?is)data-sku="` + regexp.QuoteMeta(skuID) + `"[\s\S]*?(?:comment-count|J_comment).*?(\d+)`)

		name := "JD Product " + skuID
		if match := nameRegex.FindStringSubmatch(html); len(match) > 1 {
			name = strings.TrimSpace(regexp.MustCompile(`<[^>]+>`).ReplaceAllString(match[1], ""))
		}

		imageURL := ""
		if match := imageRegex.FindStringSubmatch(html); len(match) > 1 {
			imageURL = "https://" + match[1]
		}

		commentCount := 0
		if match := commentRegex.FindStringSubmatch(html); len(match) > 1 {
			commentCount, _ = strconv.Atoi(match[1])
		}

		values = append(values, map[string]any{
			"product_id":    skuID,
			"name":          name,
			"url":           "https://item.jd.com/" + skuID + ".html",
			"image_url":     imageURL,
			"comment_count": commentCount,
		})
	}
	return values
}

func safeJSONMap(text string) map[string]any {
	payload := map[string]any{}
	_ = json.Unmarshal([]byte(text), &payload)
	return payload
}

func collectVideoLinks(baseURL string, links []string, limit int) []string {
	values := make([]string, 0, limit)
	for _, link := range normalizeLinks(baseURL, links) {
		lowered := strings.ToLower(link)
		if strings.Contains(lowered, "video") ||
			strings.HasSuffix(lowered, ".mp4") ||
			strings.HasSuffix(lowered, ".m3u8") ||
			strings.HasSuffix(lowered, ".webm") ||
			strings.HasSuffix(lowered, ".mov") {
			values = append(values, link)
		}
		if len(values) >= limit {
			break
		}
	}
	return values
}

func extractEmbeddedJSONBlocks(text string, limit int, maxChars int) []string {
	patterns := []string{
		`(?is)<script[^>]+type=["']application/ld\+json["'][^>]*>(.*?)</script>`,
		`(?is)__NEXT_DATA__\s*=\s*(\{.*?\})\s*;</script>`,
		`(?is)__NUXT__\s*=\s*(\{.*?\})\s*;`,
		`(?is)__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;`,
		`(?is)__PRELOADED_STATE__\s*=\s*(\{.*?\})\s*;`,
	}
	values := []string{}
	seen := map[string]bool{}
	for _, pattern := range patterns {
		re := regexp.MustCompile(pattern)
		for _, match := range re.FindAllStringSubmatch(text, -1) {
			if len(match) < 2 {
				continue
			}
			block := excerpt(match[1], maxChars)
			if block != "" && !seen[block] {
				seen[block] = true
				values = append(values, block)
			}
			if len(values) >= limit {
				return values
			}
		}
	}
	return values
}

func extractAPICandidates(text string, limit int) []string {
	patterns := []string{
		`https?://[^"'\\s<>]+`,
		`/(?:api|comment|comments|review|reviews|detail|item|items|sku|price|search)[^"'\\s<>]+`,
	}
	keywords := []string{"api", "comment", "review", "detail", "item", "sku", "price", "search"}
	values := []string{}
	seen := map[string]bool{}
	for _, pattern := range patterns {
		re := regexp.MustCompile(`(?i)` + pattern)
		for _, candidate := range re.FindAllString(text, -1) {
			lowered := strings.ToLower(candidate)
			matched := false
			for _, keyword := range keywords {
				if strings.Contains(lowered, keyword) {
					matched = true
					break
				}
			}
			if !matched || seen[candidate] {
				continue
			}
			seen[candidate] = true
			values = append(values, candidate)
			if len(values) >= limit {
				return values
			}
		}
	}
	return values
}

func extractJSONLDProducts(text string, limit int) []map[string]any {
	re := regexp.MustCompile(`(?is)<script[^>]+type=["']application/ld\+json["'][^>]*>(.*?)</script>`)
	values := []map[string]any{}
	for _, match := range re.FindAllStringSubmatch(text, -1) {
		if len(match) < 2 {
			continue
		}
		var payload any
		if err := json.Unmarshal([]byte(match[1]), &payload); err != nil {
			continue
		}
		walkJSONLDProducts(payload, &values, limit)
		if len(values) >= limit {
			return values[:limit]
		}
	}
	return values
}

func walkJSONLDProducts(payload any, values *[]map[string]any, limit int) {
	if len(*values) >= limit {
		return
	}
	switch node := payload.(type) {
	case map[string]any:
		nodeType := node["@type"]
		switch typed := nodeType.(type) {
		case string:
			if strings.EqualFold(typed, "Product") {
				*values = append(*values, map[string]any{
					"name":         stringValue(node["name"]),
					"sku":          stringValue(node["sku"]),
					"brand":        nestedName(node["brand"]),
					"category":     stringValue(node["category"]),
					"url":          stringValue(node["url"]),
					"image":        imageValue(node["image"]),
					"price":        nestedField(node["offers"], "price"),
					"currency":     nestedField(node["offers"], "priceCurrency"),
					"rating":       nestedField(node["aggregateRating"], "ratingValue"),
					"review_count": nestedField(node["aggregateRating"], "reviewCount"),
				})
			}
		case []any:
			for _, raw := range typed {
				if value, ok := raw.(string); ok && strings.EqualFold(value, "Product") {
					*values = append(*values, map[string]any{
						"name":         stringValue(node["name"]),
						"sku":          stringValue(node["sku"]),
						"brand":        nestedName(node["brand"]),
						"category":     stringValue(node["category"]),
						"url":          stringValue(node["url"]),
						"image":        imageValue(node["image"]),
						"price":        nestedField(node["offers"], "price"),
						"currency":     nestedField(node["offers"], "priceCurrency"),
						"rating":       nestedField(node["aggregateRating"], "ratingValue"),
						"review_count": nestedField(node["aggregateRating"], "reviewCount"),
					})
					break
				}
			}
		}
		for _, value := range node {
			walkJSONLDProducts(value, values, limit)
			if len(*values) >= limit {
				return
			}
		}
	case []any:
		for _, value := range node {
			walkJSONLDProducts(value, values, limit)
			if len(*values) >= limit {
				return
			}
		}
	}
}

func stringValue(value any) string {
	if text, ok := value.(string); ok {
		return text
	}
	return ""
}

func nestedField(value any, field string) string {
	if m, ok := value.(map[string]any); ok {
		return stringValue(m[field])
	}
	return ""
}

func nestedName(value any) string {
	if m, ok := value.(map[string]any); ok {
		return stringValue(m["name"])
	}
	return stringValue(value)
}

func imageValue(value any) string {
	switch typed := value.(type) {
	case string:
		return typed
	case []any:
		if len(typed) > 0 {
			return stringValue(typed[0])
		}
	}
	return ""
}
