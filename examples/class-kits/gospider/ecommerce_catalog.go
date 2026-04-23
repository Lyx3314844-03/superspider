package classkit

import scrapyapi "gospider/scrapy"

func NewEcommerceCatalogSpider() *scrapyapi.Spider {
	profile := profileForFamily(defaultSiteFamily)
	return scrapyapi.NewSpider("ecommerce-catalog", func(response *scrapyapi.Response) ([]any, error) {
		family := siteFamilyFromResponse(response.URL, nil)
		if response.Request != nil {
			family = siteFamilyFromResponse(response.URL, response.Request.Meta)
		}
		current := profileForFamily(family)
		title := bestTitle(response.CSS("title").Get(), response.CSS("h1").Get())
		links := response.XPath("//a/@href").GetAll()

		return []any{
			scrapyapi.NewItem().
				Set("kind", "ecommerce_catalog").
				Set("site_family", family).
				Set("runner", current.Runner).
				Set("title", title).
				Set("url", response.URL).
				Set("product_link_candidates", collectProductLinks(response.URL, links, current, 20)).
				Set("next_page", firstLinkWithKeywords(response.URL, links, current.NextLinkKeywords)).
				Set("sku_candidates", collectRegexMatches(response.Text, current.ItemIDPatterns, 10)).
				Set("price_excerpt", firstRegexMatch(response.Text, current.PricePatterns)).
				Set("note", "Template for public category/search pages. Tune the site profile before production crawling."),
		}, nil
	}).
		AddStartURL(profile.CatalogURL).
		WithStartMeta("site_family", defaultSiteFamily).
		WithStartMeta("runner", profile.Runner)
}
