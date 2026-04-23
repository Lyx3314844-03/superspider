package classkit

import scrapyapi "gospider/scrapy"

func NewEcommerceDetailSpider() *scrapyapi.Spider {
	profile := profileForFamily(defaultSiteFamily)
	return scrapyapi.NewSpider("ecommerce-detail", func(response *scrapyapi.Response) ([]any, error) {
		family := siteFamilyFromResponse(response.URL, nil)
		if response.Request != nil {
			family = siteFamilyFromResponse(response.URL, response.Request.Meta)
		}
		current := profileForFamily(family)
		title := bestTitle(response.CSS("title").Get(), response.CSS("h1").Get())
		links := response.XPath("//a/@href").GetAll()

		return []any{
			scrapyapi.NewItem().
				Set("kind", "ecommerce_detail").
				Set("site_family", family).
				Set("title", title).
				Set("url", response.URL).
				Set("item_id", firstRegexMatch(response.Text, current.ItemIDPatterns)).
				Set("price", firstRegexMatch(response.Text, current.PricePatterns)).
				Set("shop", firstRegexMatch(response.Text, current.ShopPatterns)).
				Set("review_count", firstRegexMatch(response.Text, current.ReviewCountPatterns)).
				Set("image_candidates", collectImageLinks(response.URL, response.XPath("//img/@src").GetAll(), 10)).
				Set("review_url", firstLinkWithKeywords(response.URL, links, current.ReviewLinkKeywords)).
				Set("html_excerpt", excerpt(response.Text, 800)).
				Set("note", "Template for public product detail pages. Extend with site-specific JSON/bootstrap extraction when available."),
		}, nil
	}).
		AddStartURL(profile.DetailURL).
		WithStartMeta("site_family", defaultSiteFamily).
		WithStartMeta("runner", profile.Runner)
}
