//! 京东 iPhone 17 价格爬虫 - RustSpider 版本
//!
//! 编译: cargo build --bin jd_iphone17
//! 运行: cargo run --bin jd_iphone17 -- [--pages 5] [--delay 3]

use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::fs;
use std::io::Write;
use std::time::Duration;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Product {
    product_id: String,
    name: String,
    price: f64,
    original_price: f64,
    currency: String,
    url: String,
    image_url: String,
    shop_name: String,
    shop_type: String,
    comment_count: i64,
    crawl_time: String,
}

struct JDiPhone17Spider {
    client: reqwest::blocking::Client,
    products: Vec<Product>,
    seen_ids: HashSet<String>,
    max_pages: usize,
    delay_secs: u64,
}

impl JDiPhone17Spider {
    fn new(max_pages: usize, delay_secs: u64, proxy_url: Option<&str>) -> Self {
        let mut default_headers = reqwest::header::HeaderMap::new();
        default_headers.insert(
            reqwest::header::USER_AGENT,
            reqwest::header::HeaderValue::from_static(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ),
        );
        let mut client_builder = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(30))
            .default_headers(default_headers);

        if let Some(proxy) = proxy_url {
            if let Ok(p) = reqwest::Proxy::all(proxy) {
                client_builder = client_builder.proxy(p);
                println!("代理: {}", proxy);
            }
        }

        Self {
            client: client_builder.build().unwrap(),
            products: Vec::new(),
            seen_ids: HashSet::new(),
            max_pages,
            delay_secs,
        }
    }

    fn run(&mut self) {
        println!("============================================================");
        println!("RustSpider - 京东 iPhone 17 价格爬虫");
        println!("============================================================");
        println!("爬取页数: {}", self.max_pages);
        println!("请求延迟: {}s", self.delay_secs);
        println!("============================================================");

        let keywords = vec!["iPhone 17", "苹果17"];
        for keyword in &keywords {
            println!("\n[搜索] 关键词: {}", keyword);
            self.search_keyword(keyword);
        }

        println!("\n爬取完成! 共获取 {} 个商品", self.products.len());
    }

    fn search_keyword(&mut self, keyword: &str) {
        for page in 1..=self.max_pages {
            println!("  [页面 {}/{}]", page, self.max_pages);

            let search_url = self.build_search_url(keyword, page);
            let html = match self.fetch_page(&search_url) {
                Some(h) => h,
                None => {
                    println!("  请求失败，停止翻页");
                    break;
                }
            };

            let products = self.parse_products(&html);
            println!("  找到 {} 个商品", products.len());

            if products.is_empty() {
                println!("  未找到商品，停止翻页");
                break;
            }

            self.fetch_prices(products);

            if page < self.max_pages {
                std::thread::sleep(Duration::from_secs(self.delay_secs));
            }
        }
    }

    fn build_search_url(&self, keyword: &str, page: usize) -> String {
        let skip = (page - 1) * 30;
        let encoded = url::form_urlencoded::byte_serialize(keyword.as_bytes()).collect::<String>();
        format!(
            "https://search.jd.com/Search?keyword={}&enc=utf-8&wq={}&s={}&page={}",
            encoded, encoded, skip, page
        )
    }

    fn fetch_page(&self, url: &str) -> Option<String> {
        let resp = self
            .client
            .get(url)
            .header(
                "Accept",
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            )
            .header("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
            .header("Referer", "https://www.jd.com/")
            .send()
            .ok()?;

        resp.text().ok()
    }

    fn fetch_json(&self, url: &str) -> Option<String> {
        let resp = self
            .client
            .get(url)
            .header("Referer", "https://search.jd.com/")
            .send()
            .ok()?;

        resp.text().ok()
    }

    fn parse_products(&mut self, html: &str) -> Vec<Product> {
        let mut products = Vec::new();

        // 使用正则提取 data-sku
        let sku_re = regex::Regex::new(r#"data-sku="(\d+)""#).unwrap();
        let now = chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string();

        for cap in sku_re.captures_iter(html) {
            let sku_id = cap.get(1).unwrap().as_str().to_string();
            if !self.seen_ids.insert(sku_id.clone()) {
                continue;
            }

            // 尝试提取商品名称
            let name = self.extract_name(html, &sku_id);

            // 尝试提取图片
            let image_url = self.extract_image(html, &sku_id);

            products.push(Product {
                product_id: sku_id,
                name: if name.is_empty() {
                    format!("Apple iPhone 17 (SKU: {})", &cap.get(1).unwrap().as_str())
                } else {
                    name
                },
                price: 0.0,
                original_price: 0.0,
                currency: "¥".to_string(),
                url: format!("https://item.jd.com/{}.html", cap.get(1).unwrap().as_str()),
                image_url,
                shop_name: String::new(),
                shop_type: String::new(),
                comment_count: 0,
                crawl_time: now.clone(),
            });
        }

        products
    }

    fn extract_name(&self, html: &str, sku_id: &str) -> String {
        // 简单正则提取名称
        let pattern = format!(r#"data-sku="{}"[\s\S]*?<em[^>]*>(.*?)</em>"#, sku_id);
        if let Ok(re) = regex::Regex::new(&pattern) {
            if let Some(cap) = re.captures(html) {
                if let Some(m) = cap.get(1) {
                    let raw = m.as_str();
                    // 去除HTML标签
                    let clean = regex::Regex::new(r"<[^>]+>").unwrap();
                    return clean.replace_all(raw, "").trim().to_string();
                }
            }
        }
        String::new()
    }

    fn extract_image(&self, html: &str, sku_id: &str) -> String {
        let pattern = format!(r#"data-sku="{}"[\s\S]*?data-lazy-img="//([^"]+)""#, sku_id);
        if let Ok(re) = regex::Regex::new(&pattern) {
            if let Some(cap) = re.captures(html) {
                if let Some(m) = cap.get(1) {
                    return format!("https://{}", m.as_str());
                }
            }
        }
        String::new()
    }

    fn fetch_prices(&mut self, mut products: Vec<Product>) {
        if products.is_empty() {
            return;
        }

        let sku_ids: Vec<&str> = products.iter().map(|p| p.product_id.as_str()).collect();
        let ids_param = sku_ids.join(",");

        let api_url = format!(
            "https://p.3.cn/prices/mgets?skuIds={}&type=1&area=1_72_4137_0",
            ids_param
        );

        if let Some(json_text) = self.fetch_json(&api_url) {
            if let Ok(items) = serde_json::from_str::<Vec<serde_json::Value>>(&json_text) {
                let mut price_map: std::collections::HashMap<String, f64> =
                    std::collections::HashMap::new();
                let mut oprice_map: std::collections::HashMap<String, f64> =
                    std::collections::HashMap::new();

                for item in &items {
                    if let Some(id) = item.get("id").and_then(|v| v.as_str()) {
                        if let Some(p) = item.get("p").and_then(|v| v.as_f64()) {
                            price_map.insert(id.to_string(), p);
                        }
                        if let Some(op) = item.get("op").and_then(|v| v.as_f64()) {
                            oprice_map.insert(id.to_string(), op);
                        }
                    }
                }

                for product in &mut products {
                    if let Some(price) = price_map.get(&product.product_id) {
                        product.price = *price;
                    }
                    if let Some(oprice) = oprice_map.get(&product.product_id) {
                        product.original_price = *oprice;
                    }
                }
            }
        }

        for product in &products {
            println!(
                "    [价格] {}... ¥{}",
                truncate_str(&product.name, 30),
                product.price
            );
        }

        self.products.extend(products);
    }

    fn save_json(&self, filename: &str) -> std::io::Result<()> {
        let output = serde_json::json!({
            "framework": "RustSpider (Rust)",
            "total": self.products.len(),
            "crawl_time": chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
            "products": self.products,
        });

        let json = serde_json::to_string_pretty(&output)?;
        fs::write(filename, json)?;
        println!("JSON 已保存: {}", filename);
        Ok(())
    }

    fn save_csv(&self, filename: &str) -> std::io::Result<()> {
        let mut file = fs::File::create(filename)?;
        // UTF-8 BOM
        file.write_all(&[0xEF, 0xBB, 0xBF])?;
        writeln!(
            file,
            "商品ID,商品名称,价格,原价,货币,商品链接,图片链接,店铺,店铺类型,评论数,爬取时间"
        )?;

        for p in &self.products {
            writeln!(
                file,
                "{},{:.2},{:.2},{},{},{},{},{},{},{},{}",
                p.product_id,
                p.price,
                p.original_price,
                p.currency,
                p.url,
                p.image_url,
                p.shop_name,
                p.shop_type,
                p.comment_count,
                p.crawl_time,
                escape_csv(&p.name),
            )?;
        }

        println!("CSV 已保存: {}", filename);
        Ok(())
    }

    fn print_stats(&self) {
        println!("\n============================================================");
        println!("RustSpider 爬取统计");
        println!("============================================================");
        println!("商品总数: {}", self.products.len());

        let prices: Vec<f64> = self
            .products
            .iter()
            .filter_map(|p| if p.price > 0.0 { Some(p.price) } else { None })
            .collect();

        if !prices.is_empty() {
            let min = prices.iter().cloned().fold(f64::INFINITY, f64::min);
            let max = prices.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
            let avg: f64 = prices.iter().sum::<f64>() / prices.len() as f64;
            println!("价格区间: ¥{:.2} - ¥{:.2}", min, max);
            println!("平均价格: ¥{:.2}", avg);
        }
        println!("============================================================");
    }
}

fn truncate_str(s: &str, max_len: usize) -> String {
    let chars: Vec<char> = s.chars().collect();
    if chars.len() > max_len {
        format!("{}...", chars.iter().take(max_len).collect::<String>())
    } else {
        s.to_string()
    }
}

fn escape_csv(s: &str) -> String {
    if s.contains(',') || s.contains('"') || s.contains('\n') {
        format!("\"{}\"", s.replace('"', "\"\""))
    } else {
        s.to_string()
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut max_pages = 5usize;
    let mut delay_secs = 3u64;
    let mut proxy_url: Option<String> = None;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--pages" => {
                if i + 1 < args.len() {
                    max_pages = args[i + 1].parse().unwrap_or(5);
                    i += 1;
                }
            }
            "--delay" => {
                if i + 1 < args.len() {
                    delay_secs = args[i + 1].parse().unwrap_or(3);
                    i += 1;
                }
            }
            "--proxy" => {
                if i + 1 < args.len() {
                    proxy_url = Some(args[i + 1].clone());
                    i += 1;
                }
            }
            _ => {}
        }
        i += 1;
    }

    let mut spider = JDiPhone17Spider::new(max_pages, delay_secs, proxy_url.as_deref());
    spider.run();

    // 保存结果
    let output_dir = std::path::Path::new("..").join("output");
    std::fs::create_dir_all(&output_dir).ok();

    let timestamp = chrono::Local::now().format("%Y%m%d_%H%M%S");
    let json_path = output_dir
        .join(format!("rustspider_jd_iphone17_{}.json", timestamp))
        .to_string_lossy()
        .to_string();
    let csv_path = output_dir
        .join(format!("rustspider_jd_iphone17_{}.csv", timestamp))
        .to_string_lossy()
        .to_string();

    spider.save_json(&json_path).ok();
    spider.save_csv(&csv_path).ok();

    spider.print_stats();
}
