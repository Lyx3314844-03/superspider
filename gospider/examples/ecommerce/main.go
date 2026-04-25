package main

import (
	"fmt"
	"os"

	scrapy "gospider/scrapy"
)

type EcommerceCrawler struct {
	SiteFamily string
	OutputDir  string
}

func NewEcommerceCrawler(siteFamily string) *EcommerceCrawler {
	return &EcommerceCrawler{
		SiteFamily: siteFamily,
		OutputDir:  "artifacts/exports",
	}
}

func (crawler *EcommerceCrawler) BuildSpider(mode string) (*scrapy.Spider, string) {
	return buildSpider(mode, crawler.SiteFamily)
}

func (crawler *EcommerceCrawler) Run(mode string) (int, string, error) {
	spider, normalizedMode := crawler.BuildSpider(mode)
	items, err := scrapy.NewCrawlerProcess(spider).Run()
	if err != nil {
		return 0, "", err
	}

	outputPath := fmt.Sprintf("%s/gospider-%s-%s.json", crawler.OutputDir, crawler.SiteFamily, normalizedMode)
	exporter := scrapy.NewFeedExporter("json", outputPath)
	for _, item := range items {
		exporter.ExportItem(item)
	}
	if err := exporter.Close(); err != nil {
		return 0, "", err
	}
	return len(items), outputPath, nil
}

func (crawler *EcommerceCrawler) RunBrowser(mode string) (int, string, error) {
	browserCrawler := NewSeleniumEcommerceCrawler(crawler.SiteFamily)
	payload, err := browserCrawler.Crawl(mode)
	if err != nil {
		return 0, "", err
	}
	productCount := len(payload.JSONLDProducts) + len(payload.BootstrapProducts)
	return productCount, payload.Artifacts["json"], nil
}

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
	if mode == "browser" || mode == "selenium" {
		browserMode := "catalog"
		if len(os.Args) > 3 {
			browserMode = os.Args[3]
		}
		count, outputPath, err := NewEcommerceCrawler(siteFamily).RunBrowser(browserMode)
		if err != nil {
			panic(err)
		}
		fmt.Printf("exported %d browser products to %s\n", count, outputPath)
		return
	}

	count, outputPath, err := NewEcommerceCrawler(siteFamily).Run(mode)
	if err != nil {
		panic(err)
	}
	fmt.Printf("exported %d items to %s\n", count, outputPath)
}
