package classkit

import scrapyapi "gospider/scrapy"

func NewLoginSessionSpider() *scrapyapi.Spider {
	return scrapyapi.NewSpider("login-session", func(response *scrapyapi.Response) ([]any, error) {
		return []any{
			scrapyapi.NewItem().
				Set("kind", "login_session").
				Set("title", response.CSS("title").Get()).
				Set("url", response.URL),
		}, nil
	}).
		AddStartURL("https://example.com/login").
		WithStartMeta("runner", "browser")
}

