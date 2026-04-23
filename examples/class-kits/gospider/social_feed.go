package classkit

import scrapyapi "gospider/scrapy"

func NewSocialFeedSpider() *scrapyapi.Spider {
	return scrapyapi.NewSpider("social-feed", func(response *scrapyapi.Response) ([]any, error) {
		return []any{
			scrapyapi.NewItem().
				Set("kind", "social_feed").
				Set("title", response.CSS("title").Get()).
				Set("url", response.URL),
		}, nil
	}).
		AddStartURL("https://example.com/feed").
		WithStartMeta("runner", "browser")
}

