package classkit

import scrapyapi "gospider/scrapy"

func NewSearchListingSpider() *scrapyapi.Spider {
	return scrapyapi.NewSpider("search-listing", func(response *scrapyapi.Response) ([]any, error) {
		return []any{
			scrapyapi.NewItem().
				Set("kind", "listing").
				Set("title", response.CSS("title").Get()).
				Set("url", response.URL),
		}, nil
	}).
		AddStartURL("https://example.com/search?q=demo").
		WithStartMeta("runner", "browser")
}

