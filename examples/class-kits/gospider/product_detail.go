package classkit

import scrapyapi "gospider/scrapy"

func NewProductDetailSpider() *scrapyapi.Spider {
	return scrapyapi.NewSpider("product-detail", func(response *scrapyapi.Response) ([]any, error) {
		return []any{
			scrapyapi.NewItem().
				Set("kind", "detail").
				Set("title", response.CSS("title").Get()).
				Set("url", response.URL).
				Set("html_excerpt", response.Text),
		}, nil
	}).AddStartURL("https://example.com/item/123")
}

