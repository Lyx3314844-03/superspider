package main

import (
	"fmt"
	"io"
	"net/http"

	"gospider/core"
	"gospider/parser"
	"gospider/queue"
)

func main() {
	config := core.DefaultSpiderConfig()
	config.Name = "ExampleSpider"
	config.Concurrency = 3

	spider := core.NewSpider(config)
	spider.SetOnResponse(func(req *queue.Request, resp *http.Response) error {
		body, err := io.ReadAll(resp.Body)
		if err != nil {
			return err
		}

		htmlParser := parser.NewHTMLParser(string(body))
		title := htmlParser.Title()
		links := htmlParser.Links()

		fmt.Printf("URL: %s\n", req.URL)
		fmt.Printf("Title: %s\n", title)
		fmt.Printf("Links: %d\n", len(links))
		return nil
	})

	if err := spider.AddRequests([]string{"https://www.example.com"}); err != nil {
		panic(err)
	}

	if err := spider.Run(); err != nil {
		panic(err)
	}
}
