use std::collections::BTreeMap;

use regex::Regex;
use rustspider::scrapy::Response;
use serde_json::Value;
use url::Url;

pub const DEFAULT_SITE_FAMILY: &str = "jd";

#[derive(Clone)]
pub struct EcommerceProfile {
    pub catalog_url: &'static str,
    pub detail_url: &'static str,
    pub review_url: &'static str,
    pub runner: &'static str,
    pub detail_link_keywords: &'static [&'static str],
    pub next_link_keywords: &'static [&'static str],
    pub review_link_keywords: &'static [&'static str],
    pub price_patterns: &'static [&'static str],
    pub item_id_patterns: &'static [&'static str],
    pub shop_patterns: &'static [&'static str],
    pub review_count_patterns: &'static [&'static str],
    pub rating_patterns: &'static [&'static str],
}

pub fn profile_for_family(site_family: &str) -> EcommerceProfile {
    match site_family.to_ascii_lowercase().as_str() {
        "generic" => EcommerceProfile {
            catalog_url: "https://shop.example.com/search?q=demo",
            detail_url: "https://shop.example.com/product/demo-item",
            review_url: "https://shop.example.com/product/demo-item/reviews",
            runner: "browser",
            detail_link_keywords: &["/product", "/item", "/goods", "/sku", "detail", "productId", "itemId"],
            next_link_keywords: &["page=", "next", "pagination", "load-more"],
            review_link_keywords: &["review", "reviews", "comment", "comments", "rating"],
            price_patterns: &[
                r#"(?:price|salePrice|currentPrice|finalPrice|minPrice|maxPrice|offerPrice)["'=:\s]+([0-9]+(?:\.[0-9]{1,2})?)"#,
                r#"(?:￥|¥|\$|€|£)\s*([0-9]+(?:\.[0-9]{1,2})?)"#,
            ],
            item_id_patterns: &[r#"(?:skuId|sku|wareId|productId|itemId|goods_id|goodsId|asin)["'=:\s]+([A-Za-z0-9_-]+)"#],
            shop_patterns: &[r#"(?:shopName|seller|sellerNick|storeName|merchantName|vendor|brand)["'=:\s]+([^"'\n<,}]+)"#],
            review_count_patterns: &[r#"(?:reviewCount|commentCount|comments|ratingsTotal|totalReviewCount)["'=:\s]+([0-9]+)"#],
            rating_patterns: &[r#"(?:rating|score|ratingValue|averageRating)["'=:\s]+([0-9]+(?:\.[0-9])?)"#],
        },
        "taobao" => EcommerceProfile {
            catalog_url: "https://s.taobao.com/search?q=iphone",
            detail_url: "https://item.taobao.com/item.htm?id=100000000000",
            review_url: "https://rate.taobao.com/detailCommon.htm?id=100000000000",
            runner: "browser",
            detail_link_keywords: &["item.taobao.com", "item.htm", "id=", "detail"],
            next_link_keywords: &["page=", "next"],
            review_link_keywords: &["review", "rate.taobao.com", "comment"],
            price_patterns: &[
                r#"(?:price|promotionPrice|minPrice)["'=:\s]+([0-9]+(?:\.[0-9]{1,2})?)"#,
                r#"(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)"#,
            ],
            item_id_patterns: &[r#"(?:itemId|item_id|id)["'=:\s]+([A-Za-z0-9_-]+)"#],
            shop_patterns: &[r#"(?:shopName|sellerNick|nick)["'=:\s]+([^"'\n<,}]+)"#],
            review_count_patterns: &[r#"(?:reviewCount|commentCount|rateTotal)["'=:\s]+([0-9]+)"#],
            rating_patterns: &[r#"(?:score|rating)["'=:\s]+([0-9]+(?:\.[0-9])?)"#],
        },
        "tmall" => EcommerceProfile {
            catalog_url: "https://list.tmall.com/search_product.htm?q=iphone",
            detail_url: "https://detail.tmall.com/item.htm?id=100000000000",
            review_url: "https://rate.tmall.com/list_detail_rate.htm?itemId=100000000000",
            runner: "browser",
            detail_link_keywords: &["detail.tmall.com", "item.htm", "id=", "detail"],
            next_link_keywords: &["page=", "next"],
            review_link_keywords: &["review", "rate.tmall.com", "comment"],
            price_patterns: &[
                r#"(?:price|promotionPrice|minPrice)["'=:\s]+([0-9]+(?:\.[0-9]{1,2})?)"#,
                r#"(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)"#,
            ],
            item_id_patterns: &[r#"(?:itemId|item_id|id)["'=:\s]+([A-Za-z0-9_-]+)"#],
            shop_patterns: &[r#"(?:shopName|sellerNick|shop)["'=:\s]+([^"'\n<,}]+)"#],
            review_count_patterns: &[r#"(?:reviewCount|commentCount|rateTotal)["'=:\s]+([0-9]+)"#],
            rating_patterns: &[r#"(?:score|rating)["'=:\s]+([0-9]+(?:\.[0-9])?)"#],
        },
        "pinduoduo" => EcommerceProfile {
            catalog_url: "https://mobile.yangkeduo.com/search_result.html?search_key=iphone",
            detail_url: "https://mobile.yangkeduo.com/goods.html?goods_id=100000000000",
            review_url: "https://mobile.yangkeduo.com/proxy/api/reviews/100000000000",
            runner: "browser",
            detail_link_keywords: &["goods.html", "goods_id=", "product", "detail"],
            next_link_keywords: &["page=", "next"],
            review_link_keywords: &["review", "comment"],
            price_patterns: &[
                r#"(?:minPrice|price|groupPrice)["'=:\s]+([0-9]+(?:\.[0-9]{1,2})?)"#,
                r#"(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)"#,
            ],
            item_id_patterns: &[r#"(?:goods_id|goodsId|skuId)["'=:\s]+([A-Za-z0-9_-]+)"#],
            shop_patterns: &[r#"(?:mall_name|storeName|shopName)["'=:\s]+([^"'\n<,}]+)"#],
            review_count_patterns: &[r#"(?:reviewCount|commentCount)["'=:\s]+([0-9]+)"#],
            rating_patterns: &[r#"(?:score|rating)["'=:\s]+([0-9]+(?:\.[0-9])?)"#],
        },
        "amazon" => EcommerceProfile {
            catalog_url: "https://www.amazon.com/s?k=iphone",
            detail_url: "https://www.amazon.com/dp/B0EXAMPLE00",
            review_url: "https://www.amazon.com/product-reviews/B0EXAMPLE00",
            runner: "browser",
            detail_link_keywords: &["/dp/", "/gp/product/", "/product/", "asin"],
            next_link_keywords: &["page=", "next"],
            review_link_keywords: &["review", "product-reviews"],
            price_patterns: &[
                r#"(?:priceToPay|displayPrice|priceAmount)["'=:\s]+([0-9]+(?:\.[0-9]{1,2})?)"#,
                r#"\$\s*([0-9]+(?:\.[0-9]{1,2})?)"#,
            ],
            item_id_patterns: &[r#"(?:asin|parentAsin|sku)["'=:\s]+([A-Za-z0-9_-]+)"#],
            shop_patterns: &[r#"(?:seller|merchantName|bylineInfo)["'=:\s]+([^"'\n<,}]+)"#],
            review_count_patterns: &[r#"(?:reviewCount|totalReviewCount)["'=:\s]+([0-9]+)"#],
            rating_patterns: &[r#"(?:averageRating|rating)["'=:\s]+([0-9]+(?:\.[0-9])?)"#],
        },
        _ => EcommerceProfile {
            catalog_url: "https://search.jd.com/Search?keyword=iphone",
            detail_url: "https://item.jd.com/100000000000.html",
            review_url:
                "https://club.jd.com/comment/productPageComments.action?productId=100000000000&score=0&sortType=5&page=0&pageSize=10&isShadowSku=0&fold=1",
            runner: "browser",
            detail_link_keywords: &["item.jd.com", "sku=", "wareId=", "item.htm", "detail"],
            next_link_keywords: &["page=", "pn-next", "next"],
            review_link_keywords: &["comment", "review", "club.jd.com"],
            price_patterns: &[
                r#""p"\s*:\s*"([0-9]+(?:\.[0-9]{1,2})?)""#,
                r#"(?:price|jdPrice|promotionPrice)["'=:\s]+([0-9]+(?:\.[0-9]{1,2})?)"#,
                r#"(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)"#,
            ],
            item_id_patterns: &[r#"(?:skuId|sku|wareId|productId)["'=:\s]+([A-Za-z0-9_-]+)"#],
            shop_patterns: &[r#"(?:shopName|venderName|storeName)["'=:\s]+([^"'\n<,}]+)"#],
            review_count_patterns: &[
                r#"(?:commentCount|comment_num|reviewCount)["'=:\s]+([0-9]+)"#,
            ],
            rating_patterns: &[r#"(?:score|rating)["'=:\s]+([0-9]+(?:\.[0-9])?)"#],
        },
    }
}

pub fn first_match(text: &str, patterns: &[&str]) -> String {
    for pattern in patterns {
        if let Ok(regex) = Regex::new(&format!("(?i){pattern}")) {
            if let Some(capture) = regex.captures(text) {
                if let Some(value) = capture.get(1) {
                    return value.as_str().trim().to_string();
                }
            }
        }
    }
    String::new()
}

pub fn collect_matches(text: &str, patterns: &[&str], limit: usize) -> Vec<String> {
    let mut values = Vec::new();
    for pattern in patterns {
        if let Ok(regex) = Regex::new(&format!("(?i){pattern}")) {
            for capture in regex.captures_iter(text) {
                if let Some(value) = capture.get(1) {
                    let candidate = value.as_str().trim().to_string();
                    if !candidate.is_empty() && !values.contains(&candidate) {
                        values.push(candidate);
                    }
                    if values.len() >= limit {
                        return values;
                    }
                }
            }
        }
    }
    values
}

pub fn normalize_links(base_url: &str, links: Vec<String>) -> Vec<String> {
    let mut values = Vec::new();
    let base = Url::parse(base_url).ok();
    for link in links {
        let candidate = link.trim();
        if candidate.is_empty() {
            continue;
        }
        let absolute = match (base.as_ref(), Url::parse(candidate).ok()) {
            (_, Some(url)) => url.to_string(),
            (Some(base_url), None) => base_url
                .join(candidate)
                .ok()
                .map(|url| url.to_string())
                .unwrap_or_default(),
            (None, None) => String::new(),
        };
        if absolute.starts_with("http://") || absolute.starts_with("https://") {
            if !values.contains(&absolute) {
                values.push(absolute);
            }
        }
    }
    values
}

pub fn collect_product_links(
    base_url: &str,
    links: Vec<String>,
    profile: &EcommerceProfile,
    limit: usize,
) -> Vec<String> {
    let mut values = Vec::new();
    for link in normalize_links(base_url, links) {
        let lowered = link.to_ascii_lowercase();
        if profile
            .detail_link_keywords
            .iter()
            .any(|keyword| lowered.contains(&keyword.to_ascii_lowercase()))
        {
            values.push(link);
        }
        if values.len() >= limit {
            break;
        }
    }
    values
}

pub fn collect_image_links(base_url: &str, links: Vec<String>, limit: usize) -> Vec<String> {
    let mut values = Vec::new();
    for link in normalize_links(base_url, links) {
        let lowered = link.to_ascii_lowercase();
        if lowered.contains("image")
            || lowered.ends_with(".jpg")
            || lowered.ends_with(".jpeg")
            || lowered.ends_with(".png")
            || lowered.ends_with(".webp")
            || lowered.ends_with(".gif")
        {
            values.push(link);
        }
        if values.len() >= limit {
            break;
        }
    }
    values
}

pub fn first_link_with_keywords(base_url: &str, links: Vec<String>, keywords: &[&str]) -> String {
    for link in normalize_links(base_url, links) {
        let lowered = link.to_ascii_lowercase();
        if keywords
            .iter()
            .any(|keyword| lowered.contains(&keyword.to_ascii_lowercase()))
        {
            return link;
        }
    }
    String::new()
}

pub fn best_title(response: &Response) -> String {
    response
        .css("title")
        .get()
        .or_else(|| response.css("h1").get())
        .unwrap_or_default()
}

pub fn site_family_from_response(response: &Response) -> String {
    if let Some(request) = &response.request {
        if let Some(Value::String(raw)) = request.meta.get("site_family") {
            if !raw.is_empty() {
                return raw.to_string();
            }
        }
    }
    let lowered = response.url.to_ascii_lowercase();
    if lowered.contains("taobao.com") {
        return "taobao".to_string();
    }
    if lowered.contains("tmall.com") {
        return "tmall".to_string();
    }
    if lowered.contains("yangkeduo.com") || lowered.contains("pinduoduo.com") {
        return "pinduoduo".to_string();
    }
    if lowered.contains("amazon.com") {
        return "amazon".to_string();
    }
    "generic".to_string()
}

pub fn text_excerpt(text: &str, limit: usize) -> String {
    let normalized = text.split_whitespace().collect::<Vec<_>>().join(" ");
    normalized.chars().take(limit).collect()
}

pub fn build_jd_price_api_url(sku_ids: &[String]) -> String {
    format!(
        "https://p.3.cn/prices/mgets?skuIds={}&type=1&area=1_72_4137_0",
        sku_ids.join(",")
    )
}

pub fn extract_jd_item_id(url_text: &str, html: &str) -> String {
    if let Ok(regex) = Regex::new(r"/(\d+)\.html") {
        if let Some(capture) = regex.captures(url_text) {
            if let Some(value) = capture.get(1) {
                return value.as_str().to_string();
            }
        }
    }
    first_match(
        html,
        &[
            r#"(?:skuId|sku|wareId|productId)["'=:\s]+([A-Za-z0-9_-]+)"#,
            r#""sku"\s*:\s*"(\d+)""#,
        ],
    )
}

pub fn extract_jd_catalog_products(html: &str) -> Vec<BTreeMap<String, Value>> {
    let sku_regex = Regex::new(r#"data-sku="(\d+)""#).unwrap();
    let mut values = Vec::new();
    let mut seen = Vec::<String>::new();

    for capture in sku_regex.captures_iter(html) {
        let Some(sku_match) = capture.get(1) else {
            continue;
        };
        let sku_id = sku_match.as_str().to_string();
        if seen.contains(&sku_id) {
            continue;
        }
        seen.push(sku_id.clone());

        let name_regex = Regex::new(&format!(
            r#"(?is)data-sku="{}"[\s\S]*?<em[^>]*>(.*?)</em>"#,
            regex::escape(&sku_id)
        ))
        .unwrap();
        let image_regex = Regex::new(&format!(
            r#"(?is)data-sku="{}"[\s\S]*?(?:data-lazy-img|src)="//([^"]+)""#,
            regex::escape(&sku_id)
        ))
        .unwrap();
        let comment_regex = Regex::new(&format!(
            r#"(?is)data-sku="{}"[\s\S]*?(?:comment-count|J_comment).*?(\d+)"#,
            regex::escape(&sku_id)
        ))
        .unwrap();

        let name = name_regex
            .captures(html)
            .and_then(|cap| cap.get(1))
            .map(|value| {
                Regex::new(r"<[^>]+>")
                    .unwrap()
                    .replace_all(value.as_str(), "")
                    .trim()
                    .to_string()
            })
            .filter(|value| !value.is_empty())
            .unwrap_or_else(|| format!("JD Product {sku_id}"));

        let image_url = image_regex
            .captures(html)
            .and_then(|cap| cap.get(1))
            .map(|value| format!("https://{}", value.as_str()))
            .unwrap_or_default();

        let comment_count = comment_regex
            .captures(html)
            .and_then(|cap| cap.get(1))
            .and_then(|value| value.as_str().parse::<u64>().ok())
            .unwrap_or(0);

        let mut item = BTreeMap::new();
        item.insert("product_id".to_string(), Value::String(sku_id.clone()));
        item.insert("name".to_string(), Value::String(name));
        item.insert(
            "url".to_string(),
            Value::String(format!("https://item.jd.com/{sku_id}.html")),
        );
        item.insert("image_url".to_string(), Value::String(image_url));
        item.insert(
            "comment_count".to_string(),
            Value::Number(comment_count.into()),
        );
        values.push(item);
    }

    values
}

pub fn collect_video_links(base_url: &str, links: Vec<String>, limit: usize) -> Vec<String> {
    let mut values = Vec::new();
    for link in normalize_links(base_url, links) {
        let lowered = link.to_ascii_lowercase();
        if lowered.contains("video")
            || lowered.ends_with(".mp4")
            || lowered.ends_with(".m3u8")
            || lowered.ends_with(".webm")
            || lowered.ends_with(".mov")
        {
            values.push(link);
        }
        if values.len() >= limit {
            break;
        }
    }
    values
}

pub fn extract_embedded_json_blocks(text: &str, limit: usize, max_chars: usize) -> Vec<String> {
    let patterns = [
        r#"(?is)<script[^>]+type=["']application/ld\+json["'][^>]*>(.*?)</script>"#,
        r#"(?is)__NEXT_DATA__\s*=\s*(\{.*?\})\s*;</script>"#,
        r#"(?is)__NUXT__\s*=\s*(\{.*?\})\s*;"#,
        r#"(?is)__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;"#,
        r#"(?is)__PRELOADED_STATE__\s*=\s*(\{.*?\})\s*;"#,
    ];
    let mut values = Vec::new();
    for pattern in patterns {
        if let Ok(regex) = Regex::new(pattern) {
            for capture in regex.captures_iter(text) {
                if let Some(value) = capture.get(1) {
                    let excerpt = text_excerpt(value.as_str(), max_chars);
                    if !excerpt.is_empty() && !values.contains(&excerpt) {
                        values.push(excerpt);
                    }
                    if values.len() >= limit {
                        return values;
                    }
                }
            }
        }
    }
    values
}

pub fn extract_api_candidates(text: &str, limit: usize) -> Vec<String> {
    let patterns = [
        r#"https?://[^"'\s<>]+"#,
        r#"/(?:api|comment|comments|review|reviews|detail|item|items|sku|price|search)[^"'\s<>]+"#,
    ];
    let keywords = [
        "api", "comment", "review", "detail", "item", "sku", "price", "search",
    ];
    let mut values = Vec::new();
    for pattern in patterns {
        if let Ok(regex) = Regex::new(&format!("(?i){pattern}")) {
            for matched in regex.find_iter(text) {
                let candidate = matched.as_str().trim().to_string();
                let lowered = candidate.to_ascii_lowercase();
                if !keywords.iter().any(|keyword| lowered.contains(keyword)) {
                    continue;
                }
                if !values.contains(&candidate) {
                    values.push(candidate);
                }
                if values.len() >= limit {
                    return values;
                }
            }
        }
    }
    values
}

pub fn extract_json_ld_products(text: &str, limit: usize) -> Vec<BTreeMap<String, Value>> {
    let pattern =
        Regex::new(r#"(?is)<script[^>]+type=["']application/ld\+json["'][^>]*>(.*?)</script>"#)
            .unwrap();
    let mut values = Vec::new();
    for capture in pattern.captures_iter(text) {
        let Some(block) = capture.get(1) else {
            continue;
        };
        if let Ok(payload) = serde_json::from_str::<Value>(block.as_str()) {
            walk_json_ld_products(&payload, &mut values, limit);
            if values.len() >= limit {
                return values;
            }
        }
    }
    values
}

fn walk_json_ld_products(payload: &Value, values: &mut Vec<BTreeMap<String, Value>>, limit: usize) {
    if values.len() >= limit {
        return;
    }
    match payload {
        Value::Object(map) => {
            let is_product = match map.get("@type") {
                Some(Value::String(kind)) => kind.eq_ignore_ascii_case("Product"),
                Some(Value::Array(kinds)) => kinds.iter().any(|value| {
                    value
                        .as_str()
                        .is_some_and(|kind| kind.eq_ignore_ascii_case("Product"))
                }),
                _ => false,
            };
            if is_product {
                let mut item = BTreeMap::new();
                item.insert(
                    "name".to_string(),
                    map.get("name")
                        .cloned()
                        .unwrap_or_else(|| Value::String(String::new())),
                );
                item.insert(
                    "sku".to_string(),
                    map.get("sku")
                        .cloned()
                        .unwrap_or_else(|| Value::String(String::new())),
                );
                item.insert(
                    "brand".to_string(),
                    map.get("brand")
                        .and_then(|brand| {
                            brand.get("name").cloned().or_else(|| Some(brand.clone()))
                        })
                        .unwrap_or_else(|| Value::String(String::new())),
                );
                item.insert(
                    "category".to_string(),
                    map.get("category")
                        .cloned()
                        .unwrap_or_else(|| Value::String(String::new())),
                );
                item.insert(
                    "url".to_string(),
                    map.get("url")
                        .cloned()
                        .unwrap_or_else(|| Value::String(String::new())),
                );
                item.insert(
                    "image".to_string(),
                    match map.get("image") {
                        Some(Value::Array(images)) => images
                            .first()
                            .cloned()
                            .unwrap_or_else(|| Value::String(String::new())),
                        Some(value) => value.clone(),
                        None => Value::String(String::new()),
                    },
                );
                item.insert(
                    "price".to_string(),
                    map.get("offers")
                        .and_then(|offers| offers.get("price"))
                        .cloned()
                        .unwrap_or_else(|| Value::String(String::new())),
                );
                item.insert(
                    "currency".to_string(),
                    map.get("offers")
                        .and_then(|offers| offers.get("priceCurrency"))
                        .cloned()
                        .unwrap_or_else(|| Value::String(String::new())),
                );
                item.insert(
                    "rating".to_string(),
                    map.get("aggregateRating")
                        .and_then(|rating| rating.get("ratingValue"))
                        .cloned()
                        .unwrap_or_else(|| Value::String(String::new())),
                );
                item.insert(
                    "review_count".to_string(),
                    map.get("aggregateRating")
                        .and_then(|rating| rating.get("reviewCount"))
                        .cloned()
                        .unwrap_or_else(|| Value::String(String::new())),
                );
                values.push(item);
                if values.len() >= limit {
                    return;
                }
            }
            for value in map.values() {
                walk_json_ld_products(value, values, limit);
                if values.len() >= limit {
                    return;
                }
            }
        }
        Value::Array(items) => {
            for item in items {
                walk_json_ld_products(item, values, limit);
                if values.len() >= limit {
                    return;
                }
            }
        }
        _ => {}
    }
}
