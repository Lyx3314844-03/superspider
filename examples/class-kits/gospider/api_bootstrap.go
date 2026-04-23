package classkit

import scrapyapi "gospider/scrapy"

func NewAPIBootstrapSpider() *scrapyapi.Spider {
	return scrapyapi.NewSpider("api-bootstrap", func(response *scrapyapi.Response) ([]any, error) {
		return []any{
			scrapyapi.NewItem().
				Set("kind", "api_bootstrap").
				Set("title", response.CSS("title").Get()).
				Set("url", response.URL).
				Set("bootstrap_excerpt", response.Text),
		}, nil
	}).AddStartURL("https://example.com/app/page")
}

