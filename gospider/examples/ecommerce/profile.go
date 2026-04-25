package main

import (
	"encoding/json"
	"fmt"
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
	case "jd":
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
	case "xiaohongshu":
		return ecommerceProfile{
			Family:              "xiaohongshu",
			CatalogURL:          "https://www.xiaohongshu.com/search_result?keyword=iphone",
			DetailURL:           "https://www.xiaohongshu.com/explore/660000000000000000000000",
			ReviewURL:           "https://edith.xiaohongshu.com/api/sns/web/v2/comment/page",
			Runner:              "browser",
			DetailLinkKeywords:  []string{"/explore/", "/discovery/item/", "note_id=", "goods_id=", "item/"},
			NextLinkKeywords:    []string{"page=", "cursor=", "note_id=", "load-more"},
			ReviewLinkKeywords:  []string{"comment", "comments", "edith.xiaohongshu.com", "note_id="},
			PricePatterns:       []string{`(?:price|salePrice|currentPrice|minPrice|maxPrice)["'=:\s]+([0-9]+(?:\.[0-9]{1,2})?)`, `(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)`},
			ItemIDPatterns:      []string{`(?:noteId|note_id|itemId|item_id|goodsId|goods_id|skuId|sku)["'=:\s]+([A-Za-z0-9_-]+)`},
			ShopPatterns:        []string{`(?:shopName|seller|sellerNick|storeName|merchantName|brand)["'=:\s]+([^"'\\n<,}]+)`},
			ReviewCountPatterns: []string{`(?:commentCount|comments|reviewCount|interactCount)["'=:\s]+([0-9]+)`},
			RatingPatterns:      []string{`(?:rating|score|ratingValue|averageRating)["'=:\s]+([0-9]+(?:\.[0-9])?)`},
		}
	case "douyin-shop":
		return ecommerceProfile{
			Family:              "douyin-shop",
			CatalogURL:          "https://www.douyin.com/search/iphone?type=commodity",
			DetailURL:           "https://haohuo.jinritemai.com/views/product/item2?id=100000000000",
			ReviewURL:           "https://www.jinritemai.com/ecommerce/trade/comment/list?id=100000000000",
			Runner:              "browser",
			DetailLinkKeywords:  []string{"/product/", "/item", "item2", "product_id=", "detail", "commodity"},
			NextLinkKeywords:    []string{"page=", "cursor=", "offset=", "load-more"},
			ReviewLinkKeywords:  []string{"comment", "comments", "review", "jinritemai.com"},
			PricePatterns:       []string{`(?:price|salePrice|currentPrice|minPrice|maxPrice|promotionPrice)["'=:\s]+([0-9]+(?:\.[0-9]{1,2})?)`, `(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)`},
			ItemIDPatterns:      []string{`(?:productId|product_id|itemId|item_id|goodsId|goods_id|skuId|sku)["'=:\s]+([A-Za-z0-9_-]+)`},
			ShopPatterns:        []string{`(?:shopName|seller|sellerNick|storeName|merchantName|authorName|brand)["'=:\s]+([^"'\\n<,}]+)`},
			ReviewCountPatterns: []string{`(?:commentCount|comments|reviewCount|soldCount|sales)["'=:\s]+([0-9]+)`},
			RatingPatterns:      []string{`(?:rating|score|ratingValue|averageRating)["'=:\s]+([0-9]+(?:\.[0-9])?)`},
		}
	default:
		return profileForFamily("generic")
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
	case strings.Contains(lowered, "jd.com") || strings.Contains(lowered, "3.cn"):
		return "jd"
	case strings.Contains(lowered, "taobao.com"):
		return "taobao"
	case strings.Contains(lowered, "tmall.com"):
		return "tmall"
	case strings.Contains(lowered, "yangkeduo.com") || strings.Contains(lowered, "pinduoduo.com"):
		return "pinduoduo"
	case strings.Contains(lowered, "xiaohongshu.com") || strings.Contains(lowered, "xhslink.com"):
		return "xiaohongshu"
	case strings.Contains(lowered, "douyin.com") || strings.Contains(lowered, "jinritemai.com"):
		return "douyin-shop"
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
		`(?is)<script[^>]+type=["']application/json["'][^>]*>(.*?)</script>`,
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
	for _, rawPayload := range rawEmbeddedJSONPayloads(text) {
		var payload any
		if err := json.Unmarshal([]byte(rawPayload), &payload); err != nil {
			continue
		}
		walkAPICandidates(payload, &values, seen, limit)
		if len(values) >= limit {
			return values
		}
	}
	return values
}

type rawNetworkEntry struct {
	entry  map[string]any
	source string
}

func normalizeNetworkEntries(artifact any, limit int) []map[string]any {
	if limit <= 0 {
		return []map[string]any{}
	}
	rawEntries := rawNetworkEntriesFromArtifact(artifact, limit*4)
	values := []map[string]any{}
	seen := map[string]bool{}
	for _, raw := range rawEntries {
		entry := normalizeNetworkEntry(raw.entry, raw.source)
		if len(entry) == 0 {
			continue
		}
		key := fmt.Sprintf("%s|%s|%s", entry["method"], entry["url"], entry["post_data"])
		if seen[key] {
			continue
		}
		seen[key] = true
		values = append(values, entry)
		if len(values) >= limit {
			break
		}
	}
	return values
}

func extractNetworkAPICandidates(artifact any, limit int) []string {
	values := []string{}
	seen := map[string]bool{}
	for _, entry := range normalizeNetworkEntries(artifact, limit*4) {
		if !isReplayableNetworkEntry(entry) {
			continue
		}
		targetURL := stringValue(entry["url"])
		if targetURL == "" || seen[targetURL] {
			continue
		}
		seen[targetURL] = true
		values = append(values, targetURL)
		if len(values) >= limit {
			break
		}
	}
	return values
}

func buildNetworkReplayJobTemplates(baseURL string, siteFamily string, networkArtifact any, limit int) []map[string]any {
	family := strings.TrimSpace(siteFamily)
	if family == "" {
		family = "generic"
	}
	templates := []map[string]any{}
	seen := map[string]bool{}
	for _, entry := range normalizeNetworkEntries(networkArtifact, limit*4) {
		if !isReplayableNetworkEntry(entry) {
			continue
		}
		method := strings.ToUpper(fallbackString(entry["method"], "GET"))
		targetURL := stringValue(entry["url"])
		postData := stringValue(entry["post_data"])
		key := fmt.Sprintf("%s|%s|%s", method, targetURL, postData)
		if targetURL == "" || seen[key] {
			continue
		}
		seen[key] = true
		target := map[string]any{
			"url":     targetURL,
			"method":  method,
			"headers": safeReplayHeaders(entry["request_headers"], baseURL),
		}
		if method != "GET" && method != "HEAD" && postData != "" {
			target["body"] = postData
		}
		templates = append(templates, map[string]any{
			"name":    fmt.Sprintf("%s-network-api-%d", family, len(templates)+1),
			"runtime": "http",
			"target":  target,
			"output": map[string]any{
				"format": "json",
			},
			"metadata": map[string]any{
				"site_family":   family,
				"source_url":    baseURL,
				"source":        entry["source"],
				"status":        entry["status"],
				"resource_type": entry["resource_type"],
				"content_type":  entry["content_type"],
			},
		})
		if len(templates) >= limit {
			break
		}
	}
	return templates
}

func mergeAPIJobTemplates(limit int, groups ...[]map[string]any) []map[string]any {
	values := []map[string]any{}
	seen := map[string]bool{}
	for _, group := range groups {
		for _, template := range group {
			target, _ := template["target"].(map[string]any)
			method := strings.ToUpper(fallbackString(target["method"], "GET"))
			targetURL := stringValue(target["url"])
			body := stringValue(target["body"])
			key := fmt.Sprintf("%s|%s|%s", method, targetURL, body)
			if targetURL == "" || seen[key] {
				continue
			}
			seen[key] = true
			values = append(values, template)
			if len(values) >= limit {
				return values
			}
		}
	}
	return values
}

func appendUniqueStrings(limit int, groups ...[]string) []string {
	values := []string{}
	seen := map[string]bool{}
	for _, group := range groups {
		for _, raw := range group {
			value := strings.TrimSpace(raw)
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

func networkArtifactFromResponse(response *scrapy.Response) any {
	if response == nil || response.Request == nil {
		return nil
	}
	if value := firstArtifactValue(response.Request.Meta); value != nil {
		return value
	}
	if browserMeta, ok := response.Request.Meta["browser"].(map[string]any); ok {
		return firstArtifactValue(browserMeta)
	}
	return nil
}

func firstArtifactValue(values map[string]any) any {
	for _, key := range []string{"network_artifact", "network_entries", "network_events", "listen_network", "network", "har", "trace"} {
		if value, ok := values[key]; ok && !isEmptyArtifact(value) {
			return value
		}
	}
	return nil
}

func isEmptyArtifact(value any) bool {
	switch typed := value.(type) {
	case nil:
		return true
	case string:
		return strings.TrimSpace(typed) == ""
	case []any:
		return len(typed) == 0
	case []map[string]any:
		return len(typed) == 0
	case map[string]any:
		return len(typed) == 0
	default:
		return false
	}
}

func rawNetworkEntriesFromArtifact(artifact any, limit int) []rawNetworkEntry {
	payload := networkPayloadFromArtifact(artifact)
	values := []rawNetworkEntry{}
	if text, ok := payload.(string); ok {
		re := regexp.MustCompile(`https?://[^\s"'<>]+`)
		for _, targetURL := range re.FindAllString(text, -1) {
			values = append(values, rawNetworkEntry{entry: map[string]any{"url": targetURL, "method": "GET"}, source: "network_text"})
			if len(values) >= limit {
				return values
			}
		}
		return values
	}
	collectNetworkEntries(payload, &values, "network_artifact", limit)
	return values
}

func networkPayloadFromArtifact(artifact any) any {
	switch typed := artifact.(type) {
	case nil:
		return nil
	case string:
		text := strings.TrimSpace(typed)
		if text == "" {
			return nil
		}
		var payload any
		if err := json.Unmarshal([]byte(text), &payload); err == nil {
			return payload
		}
		return text
	case []byte:
		return networkPayloadFromArtifact(string(typed))
	default:
		return typed
	}
}

func collectNetworkEntries(payload any, values *[]rawNetworkEntry, source string, limit int) {
	if len(*values) >= limit || payload == nil {
		return
	}
	switch typed := payload.(type) {
	case []map[string]any:
		for _, item := range typed {
			collectNetworkEntries(item, values, source, limit)
			if len(*values) >= limit {
				return
			}
		}
	case []any:
		for _, item := range typed {
			collectNetworkEntries(item, values, source, limit)
			if len(*values) >= limit {
				return
			}
		}
	case map[string]any:
		if looksLikeNetworkEntry(typed) {
			*values = append(*values, rawNetworkEntry{entry: typed, source: source})
			return
		}
		if logMap := mapValue(typed["log"]); len(logMap) > 0 {
			if entries, ok := logMap["entries"].([]any); ok {
				for _, item := range entries {
					if entry := mapValue(item); len(entry) > 0 {
						*values = append(*values, rawNetworkEntry{entry: entry, source: "har"})
					}
					if len(*values) >= limit {
						return
					}
				}
			}
		}
		for key, nestedSource := range map[string]string{
			"network_events":  "network_events",
			"networkEntries":  "network_entries",
			"network_entries": "network_entries",
			"requests":        "requests",
			"entries":         "entries",
			"events":          "events",
		} {
			if nested, ok := typed[key].([]any); ok {
				for _, item := range nested {
					if entry := mapValue(item); len(entry) > 0 {
						*values = append(*values, rawNetworkEntry{entry: entry, source: nestedSource})
					}
					if len(*values) >= limit {
						return
					}
				}
			}
		}
		if extract := mapValue(typed["extract"]); len(extract) > 0 {
			for _, value := range extract {
				collectNetworkEntries(value, values, "listen_network", limit)
				if len(*values) >= limit {
					return
				}
			}
		}
		if fetched := mapValue(typed["fetched"]); stringValue(fetched["final_url"]) != "" {
			*values = append(*values, rawNetworkEntry{
				entry: map[string]any{
					"url":    fetched["final_url"],
					"method": "GET",
					"status": fetched["status"],
				},
				source: "trace",
			})
		}
	}
}

func looksLikeNetworkEntry(value map[string]any) bool {
	if stringValue(value["url"]) != "" || stringValue(value["name"]) != "" || stringValue(value["request_url"]) != "" {
		return true
	}
	request := mapValue(value["request"])
	return stringValue(request["url"]) != ""
}

func normalizeNetworkEntry(raw map[string]any, source string) map[string]any {
	request := mapValue(raw["request"])
	response := mapValue(raw["response"])
	targetURL := firstString(raw["url"], raw["name"], raw["request_url"], request["url"])
	if targetURL == "" {
		return map[string]any{}
	}
	requestHeaders := headerMap(firstNonNil(raw["request_headers"], raw["requestHeaders"], request["headers"]))
	responseHeaders := headerMap(firstNonNil(raw["response_headers"], raw["responseHeaders"], response["headers"]))
	content := mapValue(response["content"])
	contentType := firstString(raw["content_type"], raw["mimeType"], content["mimeType"], headerLookup(responseHeaders, "content-type"))
	method := strings.ToUpper(firstString(raw["method"], request["method"], "GET"))
	return map[string]any{
		"url":              targetURL,
		"method":           method,
		"status":           intValue(firstNonNil(raw["status"], response["status"])),
		"resource_type":    firstString(raw["resource_type"], raw["resourceType"], raw["type"]),
		"content_type":     contentType,
		"source":           source,
		"request_headers":  requestHeaders,
		"response_headers": responseHeaders,
		"post_data":        postDataFromEntry(raw, request),
	}
}

func isReplayableNetworkEntry(entry map[string]any) bool {
	targetURL := stringValue(entry["url"])
	method := strings.ToUpper(fallbackString(entry["method"], "GET"))
	if method == "OPTIONS" || !(strings.HasPrefix(targetURL, "http://") || strings.HasPrefix(targetURL, "https://")) {
		return false
	}
	parsed, err := url.Parse(targetURL)
	path := strings.ToLower(targetURL)
	if err == nil {
		path = strings.ToLower(parsed.Path)
	}
	for _, suffix := range []string{".css", ".js", ".mjs", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".webm", ".m3u8", ".ts", ".map"} {
		if strings.HasSuffix(path, suffix) {
			return false
		}
	}
	contentType := strings.ToLower(stringValue(entry["content_type"]))
	resourceType := strings.ToLower(stringValue(entry["resource_type"]))
	loweredURL := strings.ToLower(targetURL)
	return method != "GET" && method != "HEAD" ||
		strings.Contains(contentType, "json") ||
		strings.Contains(contentType, "graphql") ||
		strings.Contains(contentType, "event-stream") ||
		resourceType == "fetch" ||
		resourceType == "xhr" ||
		resourceType == "eventsource" ||
		containsAny(loweredURL, []string{"api", "graphql", "comment", "comments", "review", "reviews", "detail", "item", "items", "sku", "price", "search", "product", "goods", "inventory"})
}

func safeReplayHeaders(headers any, baseURL string) map[string]any {
	values := map[string]any{}
	for key, value := range headerMap(headers) {
		lowered := strings.ToLower(strings.TrimSpace(key))
		if lowered == "" || lowered == "authorization" || lowered == "cookie" || lowered == "proxy-authorization" || lowered == "set-cookie" {
			continue
		}
		values[key] = value
	}
	hasReferer := false
	for key := range values {
		if strings.EqualFold(key, "referer") {
			hasReferer = true
			break
		}
	}
	if baseURL != "" && !hasReferer {
		values["Referer"] = baseURL
	}
	return values
}

func mapValue(value any) map[string]any {
	switch typed := value.(type) {
	case map[string]any:
		return typed
	case map[string]string:
		converted := map[string]any{}
		for key, value := range typed {
			converted[key] = value
		}
		return converted
	default:
		return map[string]any{}
	}
}

func headerMap(value any) map[string]string {
	headers := map[string]string{}
	switch typed := value.(type) {
	case map[string]any:
		for key, raw := range typed {
			if text := stringValue(raw); text != "" {
				headers[key] = text
			}
		}
	case map[string]string:
		for key, raw := range typed {
			if text := strings.TrimSpace(raw); text != "" {
				headers[key] = text
			}
		}
	case []any:
		for _, item := range typed {
			entry := mapValue(item)
			name := firstString(entry["name"], entry["key"])
			if text := stringValue(entry["value"]); name != "" && text != "" {
				headers[name] = text
			}
		}
	case []map[string]any:
		for _, entry := range typed {
			name := firstString(entry["name"], entry["key"])
			if text := stringValue(entry["value"]); name != "" && text != "" {
				headers[name] = text
			}
		}
	}
	return headers
}

func headerLookup(headers map[string]string, key string) string {
	for header, value := range headers {
		if strings.EqualFold(header, key) {
			return value
		}
	}
	return ""
}

func postDataFromEntry(raw map[string]any, request map[string]any) string {
	for _, value := range []any{raw["post_data"], raw["postData"], raw["body"], request["postData"], request["body"]} {
		if entry := mapValue(value); len(entry) > 0 {
			if text := stringValue(entry["text"]); text != "" {
				return text
			}
		}
		if text := stringValue(value); text != "" {
			return text
		}
	}
	return ""
}

func firstNonNil(values ...any) any {
	for _, value := range values {
		if value != nil {
			return value
		}
	}
	return nil
}

func firstString(values ...any) string {
	for _, value := range values {
		if text := stringValue(value); text != "" {
			return text
		}
	}
	return ""
}

func stringValue(value any) string {
	switch typed := value.(type) {
	case nil:
		return ""
	case string:
		return strings.TrimSpace(typed)
	case fmt.Stringer:
		return strings.TrimSpace(typed.String())
	case int, int8, int16, int32, int64, uint, uint8, uint16, uint32, uint64, float32, float64, bool:
		return strings.TrimSpace(fmt.Sprint(typed))
	default:
		return ""
	}
}

func intValue(value any) any {
	switch typed := value.(type) {
	case int:
		return typed
	case int64:
		return int(typed)
	case float64:
		return int(typed)
	case string:
		if parsed, err := strconv.Atoi(strings.TrimSpace(typed)); err == nil {
			return parsed
		}
	}
	return nil
}

func containsAny(value string, needles []string) bool {
	for _, needle := range needles {
		if strings.Contains(value, needle) {
			return true
		}
	}
	return false
}

func walkAPICandidates(payload any, values *[]string, seen map[string]bool, limit int) {
	if len(*values) >= limit {
		return
	}
	switch node := payload.(type) {
	case map[string]any:
		for _, value := range node {
			if candidate := apiCandidateFromValue(value); candidate != "" && !seen[candidate] {
				seen[candidate] = true
				*values = append(*values, candidate)
			}
			if len(*values) >= limit {
				return
			}
			walkAPICandidates(value, values, seen, limit)
			if len(*values) >= limit {
				return
			}
		}
	case []any:
		for _, value := range node {
			if candidate := apiCandidateFromValue(value); candidate != "" && !seen[candidate] {
				seen[candidate] = true
				*values = append(*values, candidate)
			}
			if len(*values) >= limit {
				return
			}
			walkAPICandidates(value, values, seen, limit)
			if len(*values) >= limit {
				return
			}
		}
	}
}

func apiCandidateFromValue(value any) string {
	text, ok := value.(string)
	if !ok {
		return ""
	}
	candidate := strings.TrimSpace(text)
	lowered := strings.ToLower(candidate)
	keywords := []string{"api", "comment", "comments", "review", "reviews", "detail", "item", "items", "sku", "price", "search"}
	matched := false
	for _, keyword := range keywords {
		if strings.Contains(lowered, keyword) {
			matched = true
			break
		}
	}
	if !matched {
		return ""
	}
	if strings.HasPrefix(candidate, "http://") || strings.HasPrefix(candidate, "https://") || strings.HasPrefix(candidate, "/") {
		return candidate
	}
	for _, prefix := range []string{"api/", "comment", "review", "detail", "item/", "items/", "search", "price"} {
		if strings.HasPrefix(lowered, prefix) {
			return candidate
		}
	}
	return ""
}

func normalizeAPICandidates(baseURL string, candidates []string, limit int) []string {
	values := []string{}
	seen := map[string]bool{}
	for _, rawCandidate := range candidates {
		candidate := strings.TrimSpace(rawCandidate)
		if candidate == "" {
			continue
		}
		absolute := candidate
		if !strings.HasPrefix(candidate, "http://") && !strings.HasPrefix(candidate, "https://") {
			resolved := normalizeLinks(baseURL, []string{candidate})
			if len(resolved) == 0 {
				continue
			}
			absolute = resolved[0]
		}
		if !seen[absolute] {
			seen[absolute] = true
			values = append(values, absolute)
		}
		if len(values) >= limit {
			break
		}
	}
	return values
}

func buildAPIJobTemplates(baseURL string, siteFamily string, apiCandidates []string, itemIDs []string, limit int) []map[string]any {
	family := strings.TrimSpace(siteFamily)
	if family == "" {
		family = "generic"
	}
	values := []string{}
	if family == "jd" {
		cleanItemIDs := []string{}
		for _, itemID := range itemIDs {
			itemID = strings.TrimSpace(itemID)
			if itemID != "" {
				cleanItemIDs = append(cleanItemIDs, itemID)
			}
		}
		if len(cleanItemIDs) > 0 {
			take := cleanItemIDs
			if len(take) > 3 {
				take = take[:3]
			}
			values = append(values, buildJDPriceAPIURL(take))
			values = append(values, buildJDReviewAPIURL(cleanItemIDs[0]))
		}
	}
	values = append(values, normalizeAPICandidates(baseURL, apiCandidates, limit*2)...)

	templates := []map[string]any{}
	seen := map[string]bool{}
	for _, targetURL := range values {
		if seen[targetURL] {
			continue
		}
		seen[targetURL] = true
		templates = append(templates, map[string]any{
			"name":    fmt.Sprintf("%s-api-%d", family, len(templates)+1),
			"runtime": "http",
			"target": map[string]any{
				"url":    targetURL,
				"method": "GET",
				"headers": map[string]any{
					"Referer": baseURL,
				},
			},
			"output": map[string]any{
				"format": "json",
			},
			"metadata": map[string]any{
				"site_family": family,
				"source_url":  baseURL,
			},
		})
		if len(templates) >= limit {
			break
		}
	}
	return templates
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

func extractBootstrapProducts(text string, limit int) []map[string]any {
	patterns := []string{
		`(?is)<script[^>]+type=["']application/ld\+json["'][^>]*>(.*?)</script>`,
		`(?is)<script[^>]+type=["']application/json["'][^>]*>(.*?)</script>`,
		`(?is)__NEXT_DATA__\s*=\s*(\{.*?\})\s*;</script>`,
		`(?is)__NUXT__\s*=\s*(\{.*?\})\s*;`,
		`(?is)__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;`,
		`(?is)__PRELOADED_STATE__\s*=\s*(\{.*?\})\s*;`,
		`(?is)__APOLLO_STATE__\s*=\s*(\{.*?\})\s*;`,
	}
	values := []map[string]any{}
	seen := map[string]bool{}
	for _, pattern := range patterns {
		re := regexp.MustCompile(pattern)
		for _, match := range re.FindAllStringSubmatch(text, -1) {
			if len(match) < 2 {
				continue
			}
			var payload any
			if err := json.Unmarshal([]byte(match[1]), &payload); err != nil {
				continue
			}
			walkBootstrapProducts(payload, &values, seen, limit)
			if len(values) >= limit {
				return values[:limit]
			}
		}
	}
	return values
}

func rawEmbeddedJSONPayloads(text string) []string {
	patterns := []string{
		`(?is)<script[^>]+type=["']application/ld\+json["'][^>]*>(.*?)</script>`,
		`(?is)<script[^>]+type=["']application/json["'][^>]*>(.*?)</script>`,
		`(?is)__NEXT_DATA__\s*=\s*(\{.*?\})\s*;</script>`,
		`(?is)__NUXT__\s*=\s*(\{.*?\})\s*;`,
		`(?is)__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;`,
		`(?is)__PRELOADED_STATE__\s*=\s*(\{.*?\})\s*;`,
		`(?is)__APOLLO_STATE__\s*=\s*(\{.*?\})\s*;`,
	}
	values := []string{}
	for _, pattern := range patterns {
		re := regexp.MustCompile(pattern)
		for _, match := range re.FindAllStringSubmatch(text, -1) {
			if len(match) > 1 {
				values = append(values, strings.TrimSpace(match[1]))
			}
		}
	}
	return values
}

func walkBootstrapProducts(payload any, values *[]map[string]any, seen map[string]bool, limit int) {
	if len(*values) >= limit {
		return
	}
	switch node := payload.(type) {
	case map[string]any:
		if product := normalizeBootstrapProduct(node); product != nil {
			fingerprint := strings.Join([]string{
				strings.TrimSpace(fmt.Sprint(product["sku"])),
				strings.TrimSpace(fmt.Sprint(product["url"])),
				strings.TrimSpace(fmt.Sprint(product["name"])),
				strings.TrimSpace(fmt.Sprint(product["price"])),
			}, "|")
			if !seen[fingerprint] {
				seen[fingerprint] = true
				*values = append(*values, product)
				if len(*values) >= limit {
					return
				}
			}
		}
		for _, value := range node {
			walkBootstrapProducts(value, values, seen, limit)
			if len(*values) >= limit {
				return
			}
		}
	case []any:
		for _, value := range node {
			walkBootstrapProducts(value, values, seen, limit)
			if len(*values) >= limit {
				return
			}
		}
	}
}

func normalizeBootstrapProduct(node map[string]any) map[string]any {
	name := bootstrapString(firstPresent(node, "name", "title", "itemName", "productName", "goodsName", "noteTitle", "note_title"))
	sku := bootstrapString(firstPresent(node, "sku", "skuId", "itemId", "item_id", "productId", "product_id", "goodsId", "goods_id", "noteId", "note_id", "asin", "id"))
	url := bootstrapString(firstPresent(node, "url", "detailUrl", "itemUrl", "shareUrl", "jumpUrl", "link"))
	image := bootstrapImage(firstPresent(node, "image", "imageUrl", "imageURL", "pic", "picUrl", "cover", "coverUrl", "mainImage", "img"))
	price := bootstrapString(
		firstPresent(node, "price", "salePrice", "currentPrice", "finalPrice", "minPrice", "maxPrice", "promotionPrice", "groupPrice", "jdPrice", "priceToPay", "displayPrice", "priceAmount"),
	)
	if price == "" {
		price = bootstrapString(nestedFirst(node, []string{"offers", "price"}, []string{"offers", "lowPrice"}, []string{"priceInfo", "price"}, []string{"currentSku", "price"}, []string{"product", "price"}))
	}
	currency := bootstrapString(firstPresent(node, "currency", "priceCurrency"))
	if currency == "" {
		currency = bootstrapString(nestedFirst(node, []string{"offers", "priceCurrency"}, []string{"priceInfo", "currency"}))
	}
	brand := bootstrapString(firstPresent(node, "brand", "brandName"))
	if brand == "" {
		brand = bootstrapString(nestedFirst(node, []string{"brand", "name"}, []string{"brandInfo", "name"}))
	}
	category := bootstrapString(firstPresent(node, "category", "categoryName"))
	rating := bootstrapString(firstPresent(node, "rating", "score", "ratingValue", "averageRating"))
	if rating == "" {
		rating = bootstrapString(nestedFirst(node, []string{"aggregateRating", "ratingValue"}, []string{"ratings", "average"}))
	}
	reviewCount := bootstrapString(firstPresent(node, "reviewCount", "commentCount", "comments", "ratingsTotal", "totalReviewCount", "soldCount", "sales", "interactCount"))
	if reviewCount == "" {
		reviewCount = bootstrapString(nestedFirst(node, []string{"aggregateRating", "reviewCount"}, []string{"aggregateRating", "ratingCount"}))
	}
	shop := bootstrapString(firstPresent(node, "shopName", "seller", "sellerNick", "storeName", "merchantName", "vendor", "authorName", "mall_name"))

	score := 0
	if name != "" || sku != "" {
		score++
	}
	if price != "" {
		score++
	}
	if image != "" || url != "" {
		score++
	}
	if shop != "" || rating != "" || reviewCount != "" {
		score++
	}
	if score < 2 {
		return nil
	}

	return map[string]any{
		"name":         name,
		"sku":          sku,
		"brand":        brand,
		"category":     category,
		"url":          url,
		"image":        image,
		"price":        price,
		"currency":     currency,
		"rating":       rating,
		"review_count": reviewCount,
		"shop":         shop,
	}
}

func firstPresent(node map[string]any, keys ...string) any {
	for _, key := range keys {
		if value, ok := node[key]; ok && value != nil {
			switch typed := value.(type) {
			case string:
				if strings.TrimSpace(typed) != "" {
					return typed
				}
			case []any:
				if len(typed) > 0 {
					return typed
				}
			case map[string]any:
				if len(typed) > 0 {
					return typed
				}
			default:
				return value
			}
		}
	}
	return nil
}

func nestedFirst(node map[string]any, paths ...[]string) any {
	for _, path := range paths {
		var current any = node
		valid := true
		for _, key := range path {
			next, ok := current.(map[string]any)
			if !ok {
				valid = false
				break
			}
			current = next[key]
		}
		if valid {
			if text := bootstrapString(current); text != "" {
				return text
			}
		}
	}
	return nil
}

func bootstrapString(value any) string {
	switch typed := value.(type) {
	case string:
		return strings.TrimSpace(typed)
	case float64:
		return strings.TrimSpace(strconv.FormatFloat(typed, 'f', -1, 64))
	case int:
		return strconv.Itoa(typed)
	case int64:
		return strconv.FormatInt(typed, 10)
	case json.Number:
		return typed.String()
	default:
		return strings.TrimSpace(fmt.Sprint(value))
	}
}

func bootstrapImage(value any) string {
	switch typed := value.(type) {
	case []any:
		if len(typed) > 0 {
			return bootstrapString(typed[0])
		}
		return ""
	default:
		return bootstrapString(value)
	}
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

// Enhanced product-page extraction helpers.

type SKUVariant struct {
	Name   string   `json:"name"`
	Values []string `json:"values"`
	SKUID  string   `json:"sku_id,omitempty"`
}

func ExtractSKUVariants(html string) []SKUVariant {
	variants := []SKUVariant{}
	seen := map[string]bool{}
	for _, payload := range rawEmbeddedJSONPayloads(html) {
		var data any
		if err := json.Unmarshal([]byte(payload), &data); err != nil {
			continue
		}
		walkForVariants(data, &variants, seen, 0, 6)
		if len(variants) >= 20 {
			return variants[:20]
		}
	}
	for _, pattern := range []string{
		`"(color|colour|size|storage|style|version)"\s*:\s*"([^"]+)"`,
		`data-(?:sku|variant|spec)[^=]*=["']([^"']+)["']`,
	} {
		re := regexp.MustCompile(`(?i)` + pattern)
		for _, match := range re.FindAllStringSubmatch(html, -1) {
			if len(match) < 2 {
				continue
			}
			name, value := "variant", match[1]
			if len(match) > 2 {
				name, value = match[1], match[2]
			}
			key := strings.ToLower(name + ":" + value)
			if value != "" && !seen[key] {
				seen[key] = true
				variants = append(variants, SKUVariant{Name: name, Values: []string{value}})
			}
			if len(variants) >= 20 {
				return variants[:20]
			}
		}
	}
	return variants
}

func walkForVariants(node any, variants *[]SKUVariant, seen map[string]bool, depth int, maxDepth int) {
	if depth > maxDepth || len(*variants) >= 20 {
		return
	}
	switch value := node.(type) {
	case map[string]any:
		for key, child := range value {
			lowered := strings.ToLower(key)
			if lowered == "skus" || lowered == "variants" || lowered == "specs" ||
				lowered == "sale_attrs" || lowered == "attr_list" || lowered == "spec_items" ||
				lowered == "variant_list" || lowered == "skulist" || lowered == "product_options" ||
				lowered == "attributes" {
				if rows, ok := child.([]any); ok {
					for _, row := range rows {
						if m, ok := row.(map[string]any); ok {
							variant := normalizeVariant(m)
							key := strings.ToLower(variant.Name + ":" + strings.Join(variant.Values, "|") + ":" + variant.SKUID)
							if key != "::" && !seen[key] {
								seen[key] = true
								*variants = append(*variants, variant)
							}
							if len(*variants) >= 20 {
								return
							}
						}
					}
				}
			}
			walkForVariants(child, variants, seen, depth+1, maxDepth)
		}
	case []any:
		for _, child := range value {
			walkForVariants(child, variants, seen, depth+1, maxDepth)
			if len(*variants) >= 20 {
				return
			}
		}
	}
}

func normalizeVariant(row map[string]any) SKUVariant {
	name := bootstrapString(firstPresent(row, "name", "attr_name", "attrName", "spec_name", "specName", "label"))
	skuID := bootstrapString(firstPresent(row, "sku_id", "skuId", "id", "variantId"))
	values := []string{}
	for _, key := range []string{"values", "options", "list", "value_list", "attr_values", "spec_values"} {
		if rows, ok := row[key].([]any); ok {
			for _, raw := range rows {
				switch v := raw.(type) {
				case map[string]any:
					text := bootstrapString(firstPresent(v, "name", "value", "text", "label"))
					if text != "" {
						values = append(values, text)
					}
				default:
					text := bootstrapString(v)
					if text != "" {
						values = append(values, text)
					}
				}
				if len(values) >= 15 {
					break
				}
			}
			break
		}
	}
	if len(values) == 0 {
		value := bootstrapString(firstPresent(row, "value", "text", "label"))
		if value != "" {
			values = append(values, value)
		}
	}
	return SKUVariant{Name: name, Values: values, SKUID: skuID}
}

type GalleryImage struct {
	URL  string `json:"url"`
	Alt  string `json:"alt"`
	Kind string `json:"kind"`
}

func ExtractImageGallery(pageURL string, imgSrcs []string) []GalleryImage {
	gallery := []GalleryImage{}
	seen := map[string]bool{}
	skipNeedles := []string{"1x1", "spacer", "pixel", "tracker", "icon", "logo", "banner", "arrow", "blank"}
	for _, raw := range imgSrcs {
		src := strings.TrimSpace(raw)
		if src == "" {
			continue
		}
		lowered := strings.ToLower(src)
		skip := false
		for _, needle := range skipNeedles {
			if strings.Contains(lowered, needle) {
				skip = true
				break
			}
		}
		if skip {
			continue
		}
		absolute := resolveURL(pageURL, src)
		if absolute == "" || seen[absolute] {
			continue
		}
		seen[absolute] = true
		kind := "gallery"
		if len(gallery) == 0 {
			kind = "main"
		}
		gallery = append(gallery, GalleryImage{URL: absolute, Kind: kind})
		if len(gallery) >= 30 {
			break
		}
	}
	return gallery
}

func resolveURL(base, ref string) string {
	if strings.HasPrefix(ref, "//") {
		return "https:" + ref
	}
	if strings.HasPrefix(ref, "http://") || strings.HasPrefix(ref, "https://") {
		return ref
	}
	baseURL, err := url.Parse(base)
	if err != nil {
		return ref
	}
	refURL, err := url.Parse(ref)
	if err != nil {
		return ref
	}
	return baseURL.ResolveReference(refURL).String()
}

type ParamEntry struct {
	Key   string `json:"key"`
	Value string `json:"value"`
	Group string `json:"group,omitempty"`
}

func ExtractParameterTable(html string) []ParamEntry {
	params := []ParamEntry{}
	for _, pattern := range []string{
		`(?is)<tr[^>]*>\s*<t[dh][^>]*>(.*?)</t[dh]>\s*<t[dh][^>]*>(.*?)</t[dh]>`,
		`(?is)<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>`,
	} {
		re := regexp.MustCompile(pattern)
		for _, match := range re.FindAllStringSubmatch(html, -1) {
			if len(match) < 3 {
				continue
			}
			key := cleanHTMLText(match[1])
			value := cleanHTMLText(match[2])
			if key != "" && value != "" && len(key) <= 80 {
				params = append(params, ParamEntry{Key: key, Value: value})
			}
			if len(params) >= 50 {
				return params[:50]
			}
		}
		if len(params) > 0 {
			return params
		}
	}
	for _, payload := range rawEmbeddedJSONPayloads(html) {
		var data any
		if err := json.Unmarshal([]byte(payload), &data); err != nil {
			continue
		}
		walkForParams(data, &params, 0, 5)
		if len(params) >= 50 {
			return params[:50]
		}
	}
	return params
}

func walkForParams(node any, params *[]ParamEntry, depth int, maxDepth int) {
	if depth > maxDepth || len(*params) >= 50 {
		return
	}
	switch value := node.(type) {
	case map[string]any:
		key := bootstrapString(firstPresent(value, "key", "name", "attrName", "attr_name", "specName", "spec_name", "label"))
		val := bootstrapString(firstPresent(value, "value", "text", "attrValue", "attr_value", "specValue", "spec_value"))
		if key != "" && val != "" && len(key) <= 80 {
			*params = append(*params, ParamEntry{Key: key, Value: val})
		}
		for _, child := range value {
			walkForParams(child, params, depth+1, maxDepth)
			if len(*params) >= 50 {
				return
			}
		}
	case []any:
		for _, child := range value {
			walkForParams(child, params, depth+1, maxDepth)
			if len(*params) >= 50 {
				return
			}
		}
	}
}

type PromotionSignal struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

func DetectCouponsPromotions(html string) []PromotionSignal {
	signals := []PromotionSignal{}
	patterns := map[string]string{
		"coupon":   `(?i)(coupon|优惠券|领券|满减|券后|折扣券)[^<]{0,80}`,
		"discount": `(?i)(discount|sale|promo|促销|折扣|直降|限时)[^<]{0,80}`,
		"shipping": `(?i)(free shipping|包邮|免邮)[^<]{0,80}`,
	}
	seen := map[string]bool{}
	for kind, pattern := range patterns {
		re := regexp.MustCompile(pattern)
		for _, raw := range re.FindAllString(html, -1) {
			text := cleanHTMLText(raw)
			key := kind + ":" + text
			if text != "" && !seen[key] {
				seen[key] = true
				signals = append(signals, PromotionSignal{Type: kind, Text: excerpt(text, 120)})
			}
			if len(signals) >= 20 {
				return signals
			}
		}
	}
	return signals
}

func cleanHTMLText(text string) string {
	withoutTags := regexp.MustCompile(`(?is)<[^>]+>`).ReplaceAllString(text, " ")
	replacements := map[string]string{
		"&nbsp;": " ",
		"&amp;":  "&",
		"&lt;":   "<",
		"&gt;":   ">",
		"&quot;": `"`,
		"&#39;":  "'",
	}
	for old, replacement := range replacements {
		withoutTags = strings.ReplaceAll(withoutTags, old, replacement)
	}
	return strings.Join(strings.Fields(withoutTags), " ")
}

type StockStatus struct {
	Status     string `json:"status"`
	Available  bool   `json:"available"`
	Confidence string `json:"confidence"`
}

func ExtractStockStatus(html string) StockStatus {
	lowered := strings.ToLower(html)
	outSignals := []string{"out of stock", "sold out", "缺货", "无货", "售罄", "已下架"}
	inSignals := []string{"in stock", "available", "add to cart", "buy now", "加入购物车", "立即购买", "有货", "现货"}
	for _, signal := range outSignals {
		if strings.Contains(lowered, strings.ToLower(signal)) {
			return StockStatus{Status: "out_of_stock", Available: false, Confidence: "high"}
		}
	}
	for _, signal := range inSignals {
		if strings.Contains(lowered, strings.ToLower(signal)) {
			return StockStatus{Status: "in_stock", Available: true, Confidence: "medium"}
		}
	}
	return StockStatus{Status: "unknown", Available: false, Confidence: "low"}
}
