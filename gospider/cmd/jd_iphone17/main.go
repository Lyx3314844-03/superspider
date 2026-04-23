package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
)

// Product 商品数据
type Product struct {
	ProductID     string  `json:"product_id"`
	Name          string  `json:"name"`
	Price         float64 `json:"price"`
	OriginalPrice float64 `json:"original_price"`
	Currency      string  `json:"currency"`
	URL           string  `json:"url"`
	ImageURL      string  `json:"image_url"`
	ShopName      string  `json:"shop_name"`
	ShopType      string  `json:"shop_type"`
	CommentCount  int     `json:"comment_count"`
	CrawlTime     string  `json:"crawl_time"`
}

// JDiPhone17Spider GoSpider - 京东 iPhone 17 价格爬虫
type JDiPhone17Spider struct {
	client    *http.Client
	products  []Product
	seenIDs   map[string]bool
	maxPages  int
	delaySec  float64
	userAgent string
}

// NewJDiPhone17Spider 创建爬虫实例
func NewJDiPhone17Spider(maxPages int, delaySec float64, proxyURL string) *JDiPhone17Spider {
	transport := &http.Transport{}
	if proxyURL != "" {
		proxy, err := url.Parse(proxyURL)
		if err == nil {
			transport.Proxy = http.ProxyURL(proxy)
			fmt.Printf("代理: %s\n", proxyURL)
		}
	}

	return &JDiPhone17Spider{
		client: &http.Client{
			Transport: transport,
			Timeout:   30 * time.Second,
		},
		products:  make([]Product, 0),
		seenIDs:   make(map[string]bool),
		maxPages:  maxPages,
		delaySec:  delaySec,
		userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	}
}

// Run 开始爬取
func (s *JDiPhone17Spider) Run() {
	fmt.Println("============================================================")
	fmt.Println("GoSpider - 京东 iPhone 17 价格爬虫")
	fmt.Println("============================================================")
	fmt.Printf("爬取页数: %d\n", s.maxPages)
	fmt.Printf("请求延迟: %.1fs\n", s.delaySec)
	fmt.Println("============================================================")

	keywords := []string{"iPhone 17", "苹果17"}
	for _, keyword := range keywords {
		fmt.Printf("\n[搜索] 关键词: %s\n", keyword)
		s.searchKeyword(keyword)
	}

	fmt.Printf("\n爬取完成! 共获取 %d 个商品\n", len(s.products))
}

// searchKeyword 搜索关键词
func (s *JDiPhone17Spider) searchKeyword(keyword string) {
	for page := 1; page <= s.maxPages; page++ {
		fmt.Printf("  [页面 %d/%d] ", page, s.maxPages)

		searchURL := s.buildSearchURL(keyword, page)
		html, err := s.fetchPage(searchURL)
		if err != nil {
			fmt.Printf("请求失败: %v\n", err)
			break
		}

		products := s.parseProducts(html)
		fmt.Printf("找到 %d 个商品\n", len(products))

		if len(products) == 0 {
			fmt.Println("  未找到商品，停止翻页")
			break
		}

		// 获取价格
		s.fetchProducts(products)

		// 延迟
		if page < s.maxPages {
			time.Sleep(time.Duration(s.delaySec*float64(time.Second)) + time.Duration(time.Now().UnixNano()%2)*time.Second)
		}
	}
}

// buildSearchURL 构建搜索URL
func (s *JDiPhone17Spider) buildSearchURL(keyword string, page int) string {
	skip := (page - 1) * 30
	return fmt.Sprintf("https://search.jd.com/Search?keyword=%s&enc=utf-8&wq=%s&s=%d&page=%d",
		url.QueryEscape(keyword), url.QueryEscape(keyword), skip, page)
}

// fetchPage 获取页面内容
func (s *JDiPhone17Spider) fetchPage(pageURL string) (string, error) {
	req, err := http.NewRequest("GET", pageURL, nil)
	if err != nil {
		return "", err
	}

	req.Header.Set("User-Agent", s.userAgent)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
	req.Header.Set("Referer", "https://www.jd.com/")

	resp, err := s.client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	return string(body), nil
}

// fetchJSON 获取JSON数据
func (s *JDiPhone17Spider) fetchJSON(apiURL string) ([]byte, error) {
	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("User-Agent", s.userAgent)
	req.Header.Set("Referer", "https://search.jd.com/")

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	return io.ReadAll(resp.Body)
}

// parseProducts 解析商品列表
func (s *JDiPhone17Spider) parseProducts(html string) []Product {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		log.Printf("解析HTML失败: %v", err)
		return nil
	}

	var products []Product

	// 使用正则提取 data-sku
	skuRegex := regexp.MustCompile(`data-sku="(\d+)"`)
	matches := skuRegex.FindAllStringSubmatch(html, -1)

	for _, match := range matches {
		skuID := match[1]
		if s.seenIDs[skuID] {
			continue
		}
		s.seenIDs[skuID] = true

		product := Product{
			ProductID: skuID,
			URL:       fmt.Sprintf("https://item.jd.com/%s.html", skuID),
			Currency:  "¥",
			CrawlTime: time.Now().Format("2006-01-02 15:04:05"),
		}

		// 提取商品名称
		sel := fmt.Sprintf(`li[data-sku="%s"]`, skuID)
		doc.Find(sel).Each(func(i int, sel *goquery.Selection) {
			name := sel.Find(".p-name a em").Text()
			if name == "" {
				name = sel.Find("em").First().Text()
			}
			product.Name = strings.TrimSpace(name)
			if product.Name == "" {
				product.Name = fmt.Sprintf("Apple iPhone 17 (SKU: %s)", skuID)
			}

			// 提取图片
			imgURL, _ := sel.Find(".p-img img").Attr("data-lazy-img")
			if imgURL == "" {
				imgURL, _ = sel.Find(".p-img img").Attr("src")
			}
			if strings.HasPrefix(imgURL, "//") {
				imgURL = "https:" + imgURL
			}
			product.ImageURL = imgURL
		})

		products = append(products, product)
	}

	return products
}

// fetchPrices 批量获取价格
func (s *JDiPhone17Spider) fetchProducts(products []Product) {
	if len(products) == 0 {
		return
	}

	// 收集SKU IDs
	skuIDs := make([]string, 0, len(products))
	for _, p := range products {
		skuIDs = append(skuIDs, p.ProductID)
	}

	// 批量获取价格 (每批50个)
	batchSize := 50
	for i := 0; i < len(skuIDs); i += batchSize {
		end := i + batchSize
		if end > len(skuIDs) {
			end = len(skuIDs)
		}
		batch := skuIDs[i:end]

		apiURL := fmt.Sprintf("https://p.3.cn/prices/mgets?skuIds=%s&type=1&area=1_72_4137_0",
			strings.Join(batch, ","))

		body, err := s.fetchJSON(apiURL)
		if err != nil {
			fmt.Printf("    获取价格失败: %v\n", err)
			continue
		}

		var priceItems []map[string]interface{}
		if err := json.Unmarshal(body, &priceItems); err != nil {
			fmt.Printf("    解析价格失败: %v\n", err)
			continue
		}

		// 构建价格映射
		priceMap := make(map[string]float64)
		opriceMap := make(map[string]float64)
		for _, item := range priceItems {
			if id, ok := item["id"].(string); ok {
				if p, ok := item["p"].(string); ok {
					priceMap[id], _ = strconv.ParseFloat(p, 64)
				}
				if op, ok := item["op"].(string); ok {
					opriceMap[id], _ = strconv.ParseFloat(op, 64)
				}
			}
		}

		// 更新价格
		for j := range products {
			if price, exists := priceMap[products[j].ProductID]; exists {
				products[j].Price = price
			}
			if oprice, exists := opriceMap[products[j].ProductID]; exists {
				products[j].OriginalPrice = oprice
			}
		}

		time.Sleep(500 * time.Millisecond)
	}

	// 去重并添加到结果
	for _, p := range products {
		if !s.seenIDs[p.ProductID+"_added"] {
			s.seenIDs[p.ProductID+"_added"] = true
			s.products = append(s.products, p)
			fmt.Printf("    [价格] %s... ¥%.2f\n", truncateString(p.Name, 30), p.Price)
		}
	}
}

// SaveAsJSON 保存为JSON
func (s *JDiPhone17Spider) SaveAsJSON(filename string) error {
	output := map[string]interface{}{
		"framework":  "GoSpider (Go)",
		"total":      len(s.products),
		"crawl_time": time.Now().Format("2006-01-02 15:04:05"),
		"products":   s.products,
	}

	data, err := json.MarshalIndent(output, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(filename, data, 0644)
}

// SaveAsCSV 保存为CSV
func (s *JDiPhone17Spider) SaveAsCSV(filename string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	// 写入UTF-8 BOM
	file.Write([]byte{0xEF, 0xBB, 0xBF})

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// 表头
	header := []string{"商品ID", "商品名称", "价格", "原价", "货币", "商品链接", "图片链接", "店铺", "店铺类型", "评论数", "爬取时间"}
	writer.Write(header)

	// 数据
	for _, p := range s.products {
		record := []string{
			p.ProductID,
			p.Name,
			fmt.Sprintf("%.2f", p.Price),
			fmt.Sprintf("%.2f", p.OriginalPrice),
			p.Currency,
			p.URL,
			p.ImageURL,
			p.ShopName,
			p.ShopType,
			strconv.Itoa(p.CommentCount),
			p.CrawlTime,
		}
		writer.Write(record)
	}

	return nil
}

// PrintStats 打印统计信息
func (s *JDiPhone17Spider) PrintStats() {
	fmt.Println("\n============================================================")
	fmt.Println("GoSpider 爬取统计")
	fmt.Println("============================================================")
	fmt.Printf("商品总数: %d\n", len(s.products))

	var minPrice, maxPrice, totalPrice float64
	count := 0
	for _, p := range s.products {
		if p.Price > 0 {
			if count == 0 || p.Price < minPrice {
				minPrice = p.Price
			}
			if p.Price > maxPrice {
				maxPrice = p.Price
			}
			totalPrice += p.Price
			count++
		}
	}

	if count > 0 {
		fmt.Printf("价格区间: ¥%.2f - ¥%.2f\n", minPrice, maxPrice)
		fmt.Printf("平均价格: ¥%.2f\n", totalPrice/float64(count))
	}
	fmt.Println("============================================================")
}

func truncateString(s string, maxLen int) string {
	runes := []rune(s)
	if len(runes) > maxLen {
		return string(runes[:maxLen]) + "..."
	}
	return s
}

func main() {
	// 配置参数
	maxPages := 5
	delaySec := 3.0
	proxyURL := "" // 如有代理可设置为 "http://127.0.0.1:7890"

	// 简单参数解析
	for i := 1; i < len(os.Args); i++ {
		switch os.Args[i] {
		case "--pages":
			if i+1 < len(os.Args) {
				maxPages, _ = strconv.Atoi(os.Args[i+1])
				i++
			}
		case "--delay":
			if i+1 < len(os.Args) {
				delaySec, _ = strconv.ParseFloat(os.Args[i+1], 64)
				i++
			}
		case "--proxy":
			if i+1 < len(os.Args) {
				proxyURL = os.Args[i+1]
				i++
			}
		}
	}

	spider := NewJDiPhone17Spider(maxPages, delaySec, proxyURL)
	spider.Run()

	// 保存结果
	outputDir := filepath.Join("..", "output")
	os.MkdirAll(outputDir, 0755)
	timestamp := time.Now().Format("20060102_150405")

	jsonPath := filepath.Join(outputDir, fmt.Sprintf("gospider_jd_iphone17_%s.json", timestamp))
	csvPath := filepath.Join(outputDir, fmt.Sprintf("gospider_jd_iphone17_%s.csv", timestamp))

	if err := spider.SaveAsJSON(jsonPath); err != nil {
		fmt.Printf("保存JSON失败: %v\n", err)
	} else {
		fmt.Printf("JSON 已保存: %s\n", jsonPath)
	}

	if err := spider.SaveAsCSV(csvPath); err != nil {
		fmt.Printf("保存CSV失败: %v\n", err)
	} else {
		fmt.Printf("CSV 已保存: %s\n", csvPath)
	}

	spider.PrintStats()
}
