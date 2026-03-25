// Colly 示例代码
// Go 语言高性能优雅爬虫框架
// 安装: go get github.com/gocolly/colly/v2
package main

import (
	"fmt"
	"github.com/gocolly/colly/v2"
)

func main() {
	c := colly.NewCollector()

	c.OnHTML("title", func(e *colly.HTMLElement) {
		fmt.Println("标题:", e.Text)
	})

	c.OnRequest(func(r *colly.Request) {
		fmt.Println("访问:", r.URL)
	})

	c.Visit("https://example.com")
}
