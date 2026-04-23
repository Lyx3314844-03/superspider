package classkit

import scrapyapi "gospider/scrapy"

func NewInfiniteScrollSpider() *scrapyapi.Spider {
	return scrapyapi.NewSpider("infinite-scroll", func(response *scrapyapi.Response) ([]any, error) {
		return []any{
			scrapyapi.NewItem().
				Set("kind", "infinite_scroll").
				Set("title", response.CSS("title").Get()).
				Set("url", response.URL),
		}, nil
	}).
		AddStartURL("https://example.com/discover").
		WithStartMeta("runner", "browser")
}

