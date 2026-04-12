package main

import (
	"fmt"

	"gospider/scrapy"
)

func main() {
	spider := scrapy.NewSpider("starter", func(response *scrapy.Response) ([]any, error) {
		item := scrapy.NewItem().
			Set("title", response.CSS("title").Get()).
			Set("url", response.URL).
			Set("framework", "gospider")
		return []any{item}, nil
	}).AddStartURL("https://example.com")

	items, err := scrapy.NewCrawlerProcess(spider).Run()
	if err != nil {
		panic(err)
	}

	exporter := scrapy.NewFeedExporter("json", "artifacts/exports/gospider-starter-items.json")
	for _, item := range items {
		exporter.ExportItem(item)
	}
	if err := exporter.Close(); err != nil {
		panic(err)
	}

	fmt.Printf("exported %d items\n", len(items))
}
