package classkit

import scrapyapi "gospider/scrapy"

func NewEcommerceReviewSpider() *scrapyapi.Spider {
	profile := profileForFamily(defaultSiteFamily)
	return scrapyapi.NewSpider("ecommerce-review", func(response *scrapyapi.Response) ([]any, error) {
		family := siteFamilyFromResponse(response.URL, nil)
		if response.Request != nil {
			family = siteFamilyFromResponse(response.URL, response.Request.Meta)
		}
		current := profileForFamily(family)

		return []any{
			scrapyapi.NewItem().
				Set("kind", "ecommerce_review").
				Set("site_family", family).
				Set("url", response.URL).
				Set("item_id", firstRegexMatch(response.Text, current.ItemIDPatterns)).
				Set("rating", firstRegexMatch(response.Text, current.RatingPatterns)).
				Set("review_count", firstRegexMatch(response.Text, current.ReviewCountPatterns)).
				Set("review_id_candidates", collectRegexMatches(response.Text, []string{`(?:commentId|reviewId|id)["'=:\s]+([A-Za-z0-9_-]+)`}, 10)).
				Set("excerpt", excerpt(response.Text, 800)).
				Set("note", "Template for public review pages or review APIs. Prefer stable JSON payloads over brittle DOM selectors."),
		}, nil
	}).
		AddStartURL(profile.ReviewURL).
		WithStartMeta("site_family", defaultSiteFamily).
		WithStartMeta("runner", profile.Runner)
}
