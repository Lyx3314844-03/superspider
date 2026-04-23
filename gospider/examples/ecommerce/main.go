package main

import (
	"fmt"
	"os"

	scrapy "gospider/scrapy"
)

func buildSpider(mode string, siteFamily string) (*scrapy.Spider, string) {
	switch mode {
	case "detail":
		return newEcommerceDetailSpider(siteFamily), "detail"
	case "review":
		return newEcommerceReviewSpider(siteFamily), "review"
	default:
		return newEcommerceCatalogSpider(siteFamily), "catalog"
	}
}

func main() {
	mode := "catalog"
	siteFamily := defaultSiteFamily
	if len(os.Args) > 1 {
		mode = os.Args[1]
	}
	if len(os.Args) > 2 {
		siteFamily = os.Args[2]
	}

	spider, normalizedMode := buildSpider(mode, siteFamily)
	items, err := scrapy.NewCrawlerProcess(spider).Run()
	if err != nil {
		panic(err)
	}

	outputPath := fmt.Sprintf("artifacts/exports/gospider-%s-%s.json", siteFamily, normalizedMode)
	exporter := scrapy.NewFeedExporter("json", outputPath)
	for _, item := range items {
		exporter.ExportItem(item)
	}
	if err := exporter.Close(); err != nil {
		panic(err)
	}

	fmt.Printf("exported %d items to %s\n", len(items), outputPath)
}
