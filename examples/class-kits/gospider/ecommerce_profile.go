package classkit

import (
	"net/url"
	"regexp"
	"strings"
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
			ReviewURL:           "https://club.jd.com/comment/productPageComments.action?productId=100000000000",
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

func bestTitle(responseTitle string, h1 string) string {
	if strings.TrimSpace(responseTitle) != "" {
		return strings.TrimSpace(responseTitle)
	}
	return strings.TrimSpace(h1)
}

func excerpt(text string, limit int) string {
	normalized := strings.Join(strings.Fields(text), " ")
	if len(normalized) <= limit {
		return normalized
	}
	return normalized[:limit]
}

func siteFamilyFromResponse(responseURL string, requestMeta map[string]any) string {
	if requestMeta != nil {
		if raw, ok := requestMeta["site_family"].(string); ok && raw != "" {
			return raw
		}
	}
	lowered := strings.ToLower(responseURL)
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
		return defaultSiteFamily
	}
}
