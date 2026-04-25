#![allow(dead_code)]

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
        "jd" => EcommerceProfile {
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
        "xiaohongshu" => EcommerceProfile {
            catalog_url: "https://www.xiaohongshu.com/search_result?keyword=iphone",
            detail_url: "https://www.xiaohongshu.com/explore/660000000000000000000000",
            review_url: "https://edith.xiaohongshu.com/api/sns/web/v2/comment/page",
            runner: "browser",
            detail_link_keywords: &["/explore/", "/discovery/item/", "note_id=", "goods_id=", "item/"],
            next_link_keywords: &["page=", "cursor=", "note_id=", "load-more"],
            review_link_keywords: &["comment", "comments", "edith.xiaohongshu.com", "note_id="],
            price_patterns: &[
                r#"(?:price|salePrice|currentPrice|minPrice|maxPrice)["'=:\s]+([0-9]+(?:\.[0-9]{1,2})?)"#,
                r#"(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)"#,
            ],
            item_id_patterns: &[r#"(?:noteId|note_id|itemId|item_id|goodsId|goods_id|skuId|sku)["'=:\s]+([A-Za-z0-9_-]+)"#],
            shop_patterns: &[r#"(?:shopName|seller|sellerNick|storeName|merchantName|brand)["'=:\s]+([^"'\n<,}]+)"#],
            review_count_patterns: &[r#"(?:commentCount|comments|reviewCount|interactCount)["'=:\s]+([0-9]+)"#],
            rating_patterns: &[r#"(?:rating|score|ratingValue|averageRating)["'=:\s]+([0-9]+(?:\.[0-9])?)"#],
        },
        "douyin-shop" => EcommerceProfile {
            catalog_url: "https://www.douyin.com/search/iphone?type=commodity",
            detail_url: "https://haohuo.jinritemai.com/views/product/item2?id=100000000000",
            review_url: "https://www.jinritemai.com/ecommerce/trade/comment/list?id=100000000000",
            runner: "browser",
            detail_link_keywords: &["/product/", "/item", "item2", "product_id=", "detail", "commodity"],
            next_link_keywords: &["page=", "cursor=", "offset=", "load-more"],
            review_link_keywords: &["comment", "comments", "review", "jinritemai.com"],
            price_patterns: &[
                r#"(?:price|salePrice|currentPrice|minPrice|maxPrice|promotionPrice)["'=:\s]+([0-9]+(?:\.[0-9]{1,2})?)"#,
                r#"(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)"#,
            ],
            item_id_patterns: &[r#"(?:productId|product_id|itemId|item_id|goodsId|goods_id|skuId|sku)["'=:\s]+([A-Za-z0-9_-]+)"#],
            shop_patterns: &[r#"(?:shopName|seller|sellerNick|storeName|merchantName|authorName|brand)["'=:\s]+([^"'\n<,}]+)"#],
            review_count_patterns: &[r#"(?:commentCount|comments|reviewCount|soldCount|sales)["'=:\s]+([0-9]+)"#],
            rating_patterns: &[r#"(?:rating|score|ratingValue|averageRating)["'=:\s]+([0-9]+(?:\.[0-9])?)"#],
        },
        _ => profile_for_family("generic"),
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
    if lowered.contains("jd.com") || lowered.contains("3.cn") {
        return "jd".to_string();
    }
    if lowered.contains("taobao.com") {
        return "taobao".to_string();
    }
    if lowered.contains("tmall.com") {
        return "tmall".to_string();
    }
    if lowered.contains("yangkeduo.com") || lowered.contains("pinduoduo.com") {
        return "pinduoduo".to_string();
    }
    if lowered.contains("xiaohongshu.com") || lowered.contains("xhslink.com") {
        return "xiaohongshu".to_string();
    }
    if lowered.contains("douyin.com") || lowered.contains("jinritemai.com") {
        return "douyin-shop".to_string();
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
        r#"(?is)<script[^>]+type=["']application/json["'][^>]*>(.*?)</script>"#,
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
    for raw_payload in raw_embedded_json_payloads(text) {
        if let Ok(payload) = serde_json::from_str::<Value>(&raw_payload) {
            walk_api_candidates(&payload, &mut values, limit);
            if values.len() >= limit {
                return values;
            }
        }
    }
    values
}

pub fn normalize_network_entries(artifact: &Value, limit: usize) -> Vec<BTreeMap<String, Value>> {
    let raw_entries = raw_network_entries(artifact, limit.saturating_mul(4));
    let mut values = Vec::new();
    let mut seen = Vec::<String>::new();
    for (raw_entry, source) in raw_entries {
        let Some(entry) = normalize_network_entry(&raw_entry, &source) else {
            continue;
        };
        let fingerprint = format!(
            "{}|{}|{}",
            value_as_string(entry.get("method")),
            value_as_string(entry.get("url")),
            value_as_string(entry.get("post_data"))
        );
        if seen.contains(&fingerprint) {
            continue;
        }
        seen.push(fingerprint);
        values.push(entry);
        if values.len() >= limit {
            break;
        }
    }
    values
}

pub fn normalize_network_entries_text(text: &str, limit: usize) -> Vec<BTreeMap<String, Value>> {
    let artifact =
        serde_json::from_str::<Value>(text).unwrap_or_else(|_| Value::String(text.to_string()));
    normalize_network_entries(&artifact, limit)
}

pub fn extract_network_api_candidates(artifact: &Value, limit: usize) -> Vec<String> {
    let mut values = Vec::new();
    for entry in normalize_network_entries(artifact, limit.saturating_mul(4)) {
        if !is_replayable_network_entry(&entry) {
            continue;
        }
        let url = value_as_string(entry.get("url"));
        if !url.is_empty() && !values.contains(&url) {
            values.push(url);
        }
        if values.len() >= limit {
            break;
        }
    }
    values
}

pub fn build_network_replay_job_templates(
    base_url: &str,
    site_family: &str,
    network_artifact: &Value,
    limit: usize,
) -> Vec<BTreeMap<String, Value>> {
    let family = if site_family.trim().is_empty() {
        "generic".to_string()
    } else {
        site_family.trim().to_string()
    };
    let mut templates = Vec::new();
    let mut seen = Vec::<String>::new();
    for entry in normalize_network_entries(network_artifact, limit.saturating_mul(4)) {
        if !is_replayable_network_entry(&entry) {
            continue;
        }
        let method = value_as_string(entry.get("method")).to_ascii_uppercase();
        let url = value_as_string(entry.get("url"));
        let post_data = value_as_string(entry.get("post_data"));
        let fingerprint = format!("{method}|{url}|{post_data}");
        if url.is_empty() || seen.contains(&fingerprint) {
            continue;
        }
        seen.push(fingerprint);

        let mut target = serde_json::Map::from_iter([
            ("url".to_string(), Value::String(url)),
            ("method".to_string(), Value::String(method.clone())),
            (
                "headers".to_string(),
                Value::Object(safe_replay_headers(entry.get("request_headers"), base_url)),
            ),
        ]);
        if method != "GET" && method != "HEAD" && !post_data.is_empty() {
            target.insert("body".to_string(), Value::String(post_data));
        }

        templates.push(BTreeMap::from([
            (
                "name".to_string(),
                Value::String(format!("{}-network-api-{}", family, templates.len() + 1)),
            ),
            ("runtime".to_string(), Value::String("http".to_string())),
            ("target".to_string(), Value::Object(target)),
            (
                "output".to_string(),
                Value::Object(serde_json::Map::from_iter([(
                    "format".to_string(),
                    Value::String("json".to_string()),
                )])),
            ),
            (
                "metadata".to_string(),
                Value::Object(serde_json::Map::from_iter([
                    ("site_family".to_string(), Value::String(family.clone())),
                    (
                        "source_url".to_string(),
                        Value::String(base_url.to_string()),
                    ),
                    (
                        "source".to_string(),
                        entry
                            .get("source")
                            .cloned()
                            .unwrap_or_else(|| Value::String("network_artifact".to_string())),
                    ),
                    (
                        "status".to_string(),
                        entry.get("status").cloned().unwrap_or(Value::Null),
                    ),
                    (
                        "resource_type".to_string(),
                        entry
                            .get("resource_type")
                            .cloned()
                            .unwrap_or_else(|| Value::String(String::new())),
                    ),
                    (
                        "content_type".to_string(),
                        entry
                            .get("content_type")
                            .cloned()
                            .unwrap_or_else(|| Value::String(String::new())),
                    ),
                ])),
            ),
        ]));
        if templates.len() >= limit {
            break;
        }
    }
    templates
}

pub fn merge_api_job_templates(
    limit: usize,
    groups: Vec<Vec<BTreeMap<String, Value>>>,
) -> Vec<BTreeMap<String, Value>> {
    let mut values = Vec::new();
    let mut seen = Vec::<String>::new();
    for group in groups {
        for template in group {
            let target = template.get("target").and_then(|value| value.as_object());
            let method = target
                .and_then(|map| map.get("method"))
                .and_then(|value| value.as_str())
                .unwrap_or("GET")
                .to_ascii_uppercase();
            let url = target
                .and_then(|map| map.get("url"))
                .and_then(|value| value.as_str())
                .unwrap_or_default()
                .to_string();
            let body = target
                .and_then(|map| map.get("body"))
                .and_then(|value| value.as_str())
                .unwrap_or_default()
                .to_string();
            let fingerprint = format!("{method}|{url}|{body}");
            if url.is_empty() || seen.contains(&fingerprint) {
                continue;
            }
            seen.push(fingerprint);
            values.push(template);
            if values.len() >= limit {
                return values;
            }
        }
    }
    values
}

pub fn append_unique_strings(limit: usize, groups: Vec<Vec<String>>) -> Vec<String> {
    let mut values = Vec::new();
    for group in groups {
        for raw in group {
            let value = raw.trim().to_string();
            if value.is_empty() || values.contains(&value) {
                continue;
            }
            values.push(value);
            if values.len() >= limit {
                return values;
            }
        }
    }
    values
}

pub fn network_artifact_from_response(response: &Response) -> Value {
    let Some(request) = &response.request else {
        return Value::Null;
    };
    if let Some(value) = first_artifact_value_btree(&request.meta) {
        return value.clone();
    }
    if let Some(browser) = request
        .meta
        .get("browser")
        .and_then(|value| value.as_object())
    {
        if let Some(value) = first_artifact_value_json(browser) {
            return value.clone();
        }
    }
    Value::Null
}

fn first_artifact_value_btree<'a>(map: &'a BTreeMap<String, Value>) -> Option<&'a Value> {
    for key in [
        "network_artifact",
        "network_entries",
        "network_events",
        "listen_network",
        "network",
        "har",
        "trace",
    ] {
        if let Some(value) = map.get(key) {
            if artifact_has_content(value) {
                return Some(value);
            }
        }
    }
    None
}

fn first_artifact_value_json<'a>(map: &'a serde_json::Map<String, Value>) -> Option<&'a Value> {
    for key in [
        "network_artifact",
        "network_entries",
        "network_events",
        "listen_network",
        "network",
        "har",
        "trace",
    ] {
        if let Some(value) = map.get(key) {
            if artifact_has_content(value) {
                return Some(value);
            }
        }
    }
    None
}

fn artifact_has_content(value: &Value) -> bool {
    match value {
        Value::Null => false,
        Value::String(text) => !text.trim().is_empty(),
        Value::Array(items) => !items.is_empty(),
        Value::Object(items) => !items.is_empty(),
        _ => true,
    }
}

fn raw_network_entries(artifact: &Value, limit: usize) -> Vec<(Value, String)> {
    let payload = network_payload_from_artifact(artifact);
    let mut values = Vec::new();
    if let Some(text) = payload.as_str() {
        if let Ok(regex) = Regex::new(r#"https?://[^\s"'<>]+"#) {
            for matched in regex.find_iter(text) {
                values.push((
                    Value::Object(serde_json::Map::from_iter([
                        (
                            "url".to_string(),
                            Value::String(matched.as_str().to_string()),
                        ),
                        ("method".to_string(), Value::String("GET".to_string())),
                    ])),
                    "network_text".to_string(),
                ));
                if values.len() >= limit {
                    return values;
                }
            }
        }
        return values;
    }
    collect_network_entries(&payload, &mut values, "network_artifact", limit);
    values
}

fn network_payload_from_artifact(artifact: &Value) -> Value {
    if let Some(text) = artifact.as_str() {
        let trimmed = text.trim();
        if trimmed.is_empty() {
            return Value::Null;
        }
        return serde_json::from_str::<Value>(trimmed)
            .unwrap_or_else(|_| Value::String(trimmed.to_string()));
    }
    artifact.clone()
}

fn collect_network_entries(
    payload: &Value,
    values: &mut Vec<(Value, String)>,
    source: &str,
    limit: usize,
) {
    if values.len() >= limit || payload.is_null() {
        return;
    }
    if let Some(items) = payload.as_array() {
        for item in items {
            collect_network_entries(item, values, source, limit);
            if values.len() >= limit {
                return;
            }
        }
        return;
    }
    let Some(map) = payload.as_object() else {
        return;
    };
    if looks_like_network_entry(map) {
        values.push((payload.clone(), source.to_string()));
        return;
    }
    if let Some(entries) = map
        .get("log")
        .and_then(|value| value.get("entries"))
        .and_then(|value| value.as_array())
    {
        for item in entries {
            if item.is_object() {
                values.push((item.clone(), "har".to_string()));
            }
            if values.len() >= limit {
                return;
            }
        }
    }
    for (key, nested_source) in [
        ("network_events", "network_events"),
        ("networkEntries", "network_entries"),
        ("network_entries", "network_entries"),
        ("requests", "requests"),
        ("entries", "entries"),
        ("events", "events"),
    ] {
        if let Some(items) = map.get(key).and_then(|value| value.as_array()) {
            for item in items {
                if item.is_object() {
                    values.push((item.clone(), nested_source.to_string()));
                }
                if values.len() >= limit {
                    return;
                }
            }
        }
    }
    if let Some(extract) = map.get("extract").and_then(|value| value.as_object()) {
        for value in extract.values() {
            if value.is_array() {
                collect_network_entries(value, values, "listen_network", limit);
                if values.len() >= limit {
                    return;
                }
            }
        }
    }
    if let Some(fetched) = map.get("fetched").and_then(|value| value.as_object()) {
        if let Some(final_url) = fetched.get("final_url") {
            values.push((
                Value::Object(serde_json::Map::from_iter([
                    ("url".to_string(), final_url.clone()),
                    ("method".to_string(), Value::String("GET".to_string())),
                    (
                        "status".to_string(),
                        fetched.get("status").cloned().unwrap_or(Value::Null),
                    ),
                ])),
                "trace".to_string(),
            ));
        }
    }
}

fn looks_like_network_entry(map: &serde_json::Map<String, Value>) -> bool {
    !first_value_string(map, &["url", "name", "request_url"]).is_empty()
        || map
            .get("request")
            .and_then(|value| value.get("url"))
            .and_then(|value| value.as_str())
            .is_some()
}

fn normalize_network_entry(raw: &Value, source: &str) -> Option<BTreeMap<String, Value>> {
    let map = raw.as_object()?;
    let empty = serde_json::Map::new();
    let request = map
        .get("request")
        .and_then(|value| value.as_object())
        .unwrap_or(&empty);
    let response = map
        .get("response")
        .and_then(|value| value.as_object())
        .unwrap_or(&empty);
    let url = first_non_empty([
        first_value_string(map, &["url", "name", "request_url"]),
        first_value_string(request, &["url"]),
    ]);
    if url.is_empty() {
        return None;
    }
    let method = first_non_empty([
        first_value_string(map, &["method"]),
        first_value_string(request, &["method"]),
        "GET".to_string(),
    ])
    .to_ascii_uppercase();
    let request_headers = headers_to_value(header_map(
        first_present_value(map, &["request_headers", "requestHeaders"])
            .or_else(|| request.get("headers")),
    ));
    let response_headers_map = header_map(
        first_present_value(map, &["response_headers", "responseHeaders"])
            .or_else(|| response.get("headers")),
    );
    let content_type = first_non_empty([
        first_value_string(map, &["content_type", "mimeType"]),
        response
            .get("content")
            .and_then(|value| value.get("mimeType"))
            .and_then(|value| value.as_str())
            .unwrap_or_default()
            .to_string(),
        header_lookup(&response_headers_map, "content-type"),
    ]);
    Some(BTreeMap::from([
        ("url".to_string(), Value::String(url)),
        ("method".to_string(), Value::String(method)),
        (
            "status".to_string(),
            first_present_value(map, &["status"])
                .or_else(|| response.get("status"))
                .and_then(value_to_i64)
                .map(|value| Value::Number(value.into()))
                .unwrap_or(Value::Null),
        ),
        (
            "resource_type".to_string(),
            Value::String(first_value_string(
                map,
                &["resource_type", "resourceType", "type"],
            )),
        ),
        ("content_type".to_string(), Value::String(content_type)),
        ("source".to_string(), Value::String(source.to_string())),
        ("request_headers".to_string(), request_headers),
        (
            "response_headers".to_string(),
            headers_to_value(response_headers_map),
        ),
        (
            "post_data".to_string(),
            Value::String(post_data_from_entry(map, request)),
        ),
    ]))
}

fn is_replayable_network_entry(entry: &BTreeMap<String, Value>) -> bool {
    let url = value_as_string(entry.get("url"));
    let method = value_as_string(entry.get("method")).to_ascii_uppercase();
    if method == "OPTIONS" || !(url.starts_with("http://") || url.starts_with("https://")) {
        return false;
    }
    let path = Url::parse(&url)
        .ok()
        .map(|value| value.path().to_ascii_lowercase())
        .unwrap_or_else(|| url.to_ascii_lowercase());
    let static_suffixes = [
        ".css", ".js", ".mjs", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".woff",
        ".woff2", ".ttf", ".eot", ".mp4", ".webm", ".m3u8", ".ts", ".map",
    ];
    if static_suffixes.iter().any(|suffix| path.ends_with(suffix)) {
        return false;
    }
    let content_type = value_as_string(entry.get("content_type")).to_ascii_lowercase();
    let resource_type = value_as_string(entry.get("resource_type")).to_ascii_lowercase();
    let lowered_url = url.to_ascii_lowercase();
    let keywords = [
        "api",
        "graphql",
        "comment",
        "comments",
        "review",
        "reviews",
        "detail",
        "item",
        "items",
        "sku",
        "price",
        "search",
        "product",
        "goods",
        "inventory",
    ];
    method != "GET" && method != "HEAD"
        || content_type.contains("json")
        || content_type.contains("graphql")
        || content_type.contains("event-stream")
        || matches!(resource_type.as_str(), "fetch" | "xhr" | "eventsource")
        || keywords.iter().any(|keyword| lowered_url.contains(keyword))
}

fn safe_replay_headers(headers: Option<&Value>, base_url: &str) -> serde_json::Map<String, Value> {
    let mut values = serde_json::Map::new();
    for (key, value) in header_map(headers).into_iter() {
        let lowered = key.to_ascii_lowercase();
        if matches!(
            lowered.as_str(),
            "authorization" | "cookie" | "proxy-authorization" | "set-cookie"
        ) {
            continue;
        }
        values.insert(key, Value::String(value));
    }
    if !base_url.is_empty() && !values.keys().any(|key| key.eq_ignore_ascii_case("referer")) {
        values.insert("Referer".to_string(), Value::String(base_url.to_string()));
    }
    values
}

fn header_map(value: Option<&Value>) -> BTreeMap<String, String> {
    let mut values = BTreeMap::new();
    let Some(value) = value else {
        return values;
    };
    if let Some(map) = value.as_object() {
        for (key, raw) in map {
            let text = value_as_string(Some(raw));
            if !text.is_empty() {
                values.insert(key.to_string(), text);
            }
        }
        return values;
    }
    if let Some(items) = value.as_array() {
        for item in items {
            let Some(map) = item.as_object() else {
                continue;
            };
            let name = first_value_string(map, &["name", "key"]);
            let text = first_value_string(map, &["value"]);
            if !name.is_empty() && !text.is_empty() {
                values.insert(name, text);
            }
        }
    }
    values
}

fn headers_to_value(headers: BTreeMap<String, String>) -> Value {
    Value::Object(serde_json::Map::from_iter(
        headers
            .into_iter()
            .map(|(key, value)| (key, Value::String(value))),
    ))
}

fn header_lookup(headers: &BTreeMap<String, String>, key: &str) -> String {
    headers
        .iter()
        .find(|(header, _)| header.eq_ignore_ascii_case(key))
        .map(|(_, value)| value.clone())
        .unwrap_or_default()
}

fn post_data_from_entry(
    map: &serde_json::Map<String, Value>,
    request: &serde_json::Map<String, Value>,
) -> String {
    for value in [
        first_present_value(map, &["post_data", "postData", "body"]),
        first_present_value(request, &["postData", "body"]),
    ]
    .into_iter()
    .flatten()
    {
        if let Some(text) = value.get("text").and_then(|value| value.as_str()) {
            if !text.trim().is_empty() {
                return text.trim().to_string();
            }
        }
        let text = value_as_string(Some(value));
        if !text.is_empty() {
            return text;
        }
    }
    String::new()
}

fn first_present_value<'a>(
    map: &'a serde_json::Map<String, Value>,
    keys: &[&str],
) -> Option<&'a Value> {
    keys.iter().find_map(|key| map.get(*key))
}

fn first_value_string(map: &serde_json::Map<String, Value>, keys: &[&str]) -> String {
    first_present_value(map, keys)
        .map(|value| value_as_string(Some(value)))
        .unwrap_or_default()
}

fn first_non_empty(values: impl IntoIterator<Item = String>) -> String {
    values
        .into_iter()
        .find(|value| !value.trim().is_empty())
        .unwrap_or_default()
}

fn value_to_i64(value: &Value) -> Option<i64> {
    value
        .as_i64()
        .or_else(|| value.as_u64().and_then(|value| i64::try_from(value).ok()))
        .or_else(|| {
            value
                .as_str()
                .and_then(|value| value.trim().parse::<i64>().ok())
        })
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

pub fn extract_bootstrap_products(text: &str, limit: usize) -> Vec<BTreeMap<String, Value>> {
    let mut values = Vec::new();
    let mut seen = Vec::<String>::new();
    for raw_payload in raw_embedded_json_payloads(text) {
        if let Ok(payload) = serde_json::from_str::<Value>(&raw_payload) {
            walk_bootstrap_products(&payload, &mut values, &mut seen, limit);
            if values.len() >= limit {
                return values;
            }
        }
    }
    values
}

fn raw_embedded_json_payloads(text: &str) -> Vec<String> {
    let patterns = [
        r#"(?is)<script[^>]+type=["']application/ld\+json["'][^>]*>(.*?)</script>"#,
        r#"(?is)<script[^>]+type=["']application/json["'][^>]*>(.*?)</script>"#,
        r#"(?is)__NEXT_DATA__\s*=\s*(\{.*?\})\s*;</script>"#,
        r#"(?is)__NUXT__\s*=\s*(\{.*?\})\s*;"#,
        r#"(?is)__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;"#,
        r#"(?is)__PRELOADED_STATE__\s*=\s*(\{.*?\})\s*;"#,
        r#"(?is)__APOLLO_STATE__\s*=\s*(\{.*?\})\s*;"#,
    ];
    let mut values = Vec::new();
    for pattern in patterns {
        if let Ok(regex) = Regex::new(pattern) {
            for capture in regex.captures_iter(text) {
                if let Some(block) = capture.get(1) {
                    values.push(block.as_str().trim().to_string());
                }
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

fn walk_bootstrap_products(
    payload: &Value,
    values: &mut Vec<BTreeMap<String, Value>>,
    seen: &mut Vec<String>,
    limit: usize,
) {
    if values.len() >= limit {
        return;
    }
    match payload {
        Value::Object(map) => {
            if let Some(product) = normalize_bootstrap_product(map) {
                let fingerprint = [
                    value_as_string(product.get("sku")),
                    value_as_string(product.get("url")),
                    value_as_string(product.get("name")),
                    value_as_string(product.get("price")),
                ]
                .join("|");
                if !seen.contains(&fingerprint) {
                    seen.push(fingerprint);
                    values.push(product);
                    if values.len() >= limit {
                        return;
                    }
                }
            }
            for value in map.values() {
                walk_bootstrap_products(value, values, seen, limit);
                if values.len() >= limit {
                    return;
                }
            }
        }
        Value::Array(items) => {
            for item in items {
                walk_bootstrap_products(item, values, seen, limit);
                if values.len() >= limit {
                    return;
                }
            }
        }
        _ => {}
    }
}

fn walk_api_candidates(payload: &Value, values: &mut Vec<String>, limit: usize) {
    if values.len() >= limit {
        return;
    }
    match payload {
        Value::Object(map) => {
            for value in map.values() {
                if let Some(candidate) = api_candidate_from_value(value) {
                    if !values.contains(&candidate) {
                        values.push(candidate);
                    }
                }
                if values.len() >= limit {
                    return;
                }
                walk_api_candidates(value, values, limit);
                if values.len() >= limit {
                    return;
                }
            }
        }
        Value::Array(items) => {
            for item in items {
                if let Some(candidate) = api_candidate_from_value(item) {
                    if !values.contains(&candidate) {
                        values.push(candidate);
                    }
                }
                if values.len() >= limit {
                    return;
                }
                walk_api_candidates(item, values, limit);
                if values.len() >= limit {
                    return;
                }
            }
        }
        _ => {}
    }
}

fn api_candidate_from_value(value: &Value) -> Option<String> {
    let Value::String(candidate) = value else {
        return None;
    };
    let candidate = candidate.trim().to_string();
    let lowered = candidate.to_ascii_lowercase();
    let keywords = [
        "api", "comment", "comments", "review", "reviews", "detail", "item", "items", "sku",
        "price", "search",
    ];
    if !keywords.iter().any(|keyword| lowered.contains(keyword)) {
        return None;
    }
    if candidate.starts_with("http://")
        || candidate.starts_with("https://")
        || candidate.starts_with('/')
    {
        return Some(candidate);
    }
    for prefix in [
        "api/", "comment", "review", "detail", "item/", "items/", "search", "price",
    ] {
        if lowered.starts_with(prefix) {
            return Some(candidate);
        }
    }
    None
}

pub fn normalize_api_candidates(
    base_url: &str,
    candidates: &[String],
    limit: usize,
) -> Vec<String> {
    let mut values = Vec::new();
    for raw_candidate in candidates {
        let candidate = raw_candidate.trim();
        if candidate.is_empty() {
            continue;
        }
        let absolute = if candidate.starts_with("http://") || candidate.starts_with("https://") {
            candidate.to_string()
        } else {
            normalize_links(base_url, vec![candidate.to_string()])
                .into_iter()
                .next()
                .unwrap_or_default()
        };
        if absolute.is_empty() || values.contains(&absolute) {
            continue;
        }
        values.push(absolute);
        if values.len() >= limit {
            break;
        }
    }
    values
}

pub fn build_api_job_templates(
    base_url: &str,
    site_family: &str,
    api_candidates: &[String],
    item_ids: &[String],
    limit: usize,
) -> Vec<BTreeMap<String, Value>> {
    let family = if site_family.trim().is_empty() {
        "generic".to_string()
    } else {
        site_family.trim().to_string()
    };

    let mut urls = Vec::new();
    if family == "jd" {
        let clean_item_ids = item_ids
            .iter()
            .map(|item_id| item_id.trim().to_string())
            .filter(|item_id| !item_id.is_empty())
            .collect::<Vec<_>>();
        if !clean_item_ids.is_empty() {
            let take = clean_item_ids.iter().take(3).cloned().collect::<Vec<_>>();
            urls.push(build_jd_price_api_url(&take));
            urls.push(format!(
                "https://club.jd.com/comment/productPageComments.action?productId={}&score=0&sortType=5&page=0&pageSize=10&isShadowSku=0&fold=1",
                clean_item_ids[0]
            ));
        }
    }
    urls.extend(normalize_api_candidates(
        base_url,
        api_candidates,
        limit * 2,
    ));

    let mut templates = Vec::new();
    let mut seen_urls = Vec::<String>::new();
    for url in urls {
        if seen_urls.contains(&url) {
            continue;
        }
        seen_urls.push(url.clone());
        templates.push(BTreeMap::from([
            (
                "name".to_string(),
                Value::String(format!("{}-api-{}", family, templates.len() + 1)),
            ),
            ("runtime".to_string(), Value::String("http".to_string())),
            (
                "target".to_string(),
                Value::Object(serde_json::Map::from_iter([
                    ("url".to_string(), Value::String(url)),
                    ("method".to_string(), Value::String("GET".to_string())),
                    (
                        "headers".to_string(),
                        Value::Object(serde_json::Map::from_iter([(
                            "Referer".to_string(),
                            Value::String(base_url.to_string()),
                        )])),
                    ),
                ])),
            ),
            (
                "output".to_string(),
                Value::Object(serde_json::Map::from_iter([(
                    "format".to_string(),
                    Value::String("json".to_string()),
                )])),
            ),
            (
                "metadata".to_string(),
                Value::Object(serde_json::Map::from_iter([
                    ("site_family".to_string(), Value::String(family.clone())),
                    (
                        "source_url".to_string(),
                        Value::String(base_url.to_string()),
                    ),
                ])),
            ),
        ]));
        if templates.len() >= limit {
            break;
        }
    }
    templates
}

fn normalize_bootstrap_product(
    map: &serde_json::Map<String, Value>,
) -> Option<BTreeMap<String, Value>> {
    let name = first_value(
        map,
        &[
            "name",
            "title",
            "itemName",
            "productName",
            "goodsName",
            "noteTitle",
            "note_title",
        ],
    );
    let sku = first_value(
        map,
        &[
            "sku",
            "skuId",
            "itemId",
            "item_id",
            "productId",
            "product_id",
            "goodsId",
            "goods_id",
            "noteId",
            "note_id",
            "asin",
            "id",
        ],
    );
    let url = first_value(
        map,
        &["url", "detailUrl", "itemUrl", "shareUrl", "jumpUrl", "link"],
    );
    let image = image_bootstrap_value(first_present(
        map,
        &[
            "image",
            "imageUrl",
            "imageURL",
            "pic",
            "picUrl",
            "cover",
            "coverUrl",
            "mainImage",
            "img",
        ],
    ));
    let price = value_or_nested(
        map,
        &[
            "price",
            "salePrice",
            "currentPrice",
            "finalPrice",
            "minPrice",
            "maxPrice",
            "promotionPrice",
            "groupPrice",
            "jdPrice",
            "priceToPay",
            "displayPrice",
            "priceAmount",
        ],
        &[
            &["offers", "price"],
            &["offers", "lowPrice"],
            &["priceInfo", "price"],
            &["currentSku", "price"],
            &["product", "price"],
        ],
    );
    let currency = value_or_nested(
        map,
        &["currency", "priceCurrency"],
        &[&["offers", "priceCurrency"], &["priceInfo", "currency"]],
    );
    let brand = value_or_nested(
        map,
        &["brand", "brandName"],
        &[&["brand", "name"], &["brandInfo", "name"]],
    );
    let category = first_value(map, &["category", "categoryName"]);
    let rating = value_or_nested(
        map,
        &["rating", "score", "ratingValue", "averageRating"],
        &[&["aggregateRating", "ratingValue"], &["ratings", "average"]],
    );
    let review_count = value_or_nested(
        map,
        &[
            "reviewCount",
            "commentCount",
            "comments",
            "ratingsTotal",
            "totalReviewCount",
            "soldCount",
            "sales",
            "interactCount",
        ],
        &[
            &["aggregateRating", "reviewCount"],
            &["aggregateRating", "ratingCount"],
        ],
    );
    let shop = first_value(
        map,
        &[
            "shopName",
            "seller",
            "sellerNick",
            "storeName",
            "merchantName",
            "vendor",
            "authorName",
            "mall_name",
        ],
    );

    let mut score = 0;
    if !name.is_empty() || !sku.is_empty() {
        score += 1;
    }
    if !price.is_empty() {
        score += 1;
    }
    if !image.is_empty() || !url.is_empty() {
        score += 1;
    }
    if !shop.is_empty() || !rating.is_empty() || !review_count.is_empty() {
        score += 1;
    }
    if score < 2 {
        return None;
    }

    Some(BTreeMap::from([
        ("name".to_string(), Value::String(name)),
        ("sku".to_string(), Value::String(sku)),
        ("brand".to_string(), Value::String(brand)),
        ("category".to_string(), Value::String(category)),
        ("url".to_string(), Value::String(url)),
        ("image".to_string(), Value::String(image)),
        ("price".to_string(), Value::String(price)),
        ("currency".to_string(), Value::String(currency)),
        ("rating".to_string(), Value::String(rating)),
        ("review_count".to_string(), Value::String(review_count)),
        ("shop".to_string(), Value::String(shop)),
    ]))
}

fn first_present<'a>(map: &'a serde_json::Map<String, Value>, keys: &[&str]) -> Option<&'a Value> {
    for key in keys {
        if let Some(value) = map.get(*key) {
            if !value_is_empty(value) {
                return Some(value);
            }
        }
    }
    None
}

fn first_value(map: &serde_json::Map<String, Value>, keys: &[&str]) -> String {
    first_present(map, keys)
        .map(value_to_string)
        .unwrap_or_default()
}

fn value_or_nested(
    map: &serde_json::Map<String, Value>,
    keys: &[&str],
    paths: &[&[&str]],
) -> String {
    let direct = first_value(map, keys);
    if !direct.is_empty() {
        return direct;
    }
    for path in paths {
        let mut current = Value::Object(map.clone());
        for key in *path {
            match &current {
                Value::Object(object) => {
                    current = object.get(*key).cloned().unwrap_or(Value::Null);
                }
                _ => {
                    current = Value::Null;
                    break;
                }
            }
        }
        let text = value_to_string(&current);
        if !text.is_empty() {
            return text;
        }
    }
    String::new()
}

fn image_bootstrap_value(value: Option<&Value>) -> String {
    match value {
        Some(Value::Array(images)) => images.first().map(value_to_string).unwrap_or_default(),
        Some(other) => value_to_string(other),
        None => String::new(),
    }
}

fn value_is_empty(value: &Value) -> bool {
    match value {
        Value::Null => true,
        Value::String(text) => text.trim().is_empty(),
        Value::Array(values) => values.is_empty(),
        Value::Object(values) => values.is_empty(),
        _ => false,
    }
}

fn value_as_string(value: Option<&Value>) -> String {
    value.map(value_to_string).unwrap_or_default()
}

fn value_to_string(value: &Value) -> String {
    match value {
        Value::Null => String::new(),
        Value::String(text) => text.trim().to_string(),
        Value::Number(number) => number.to_string(),
        Value::Bool(flag) => flag.to_string(),
        Value::Array(values) => values.first().map(value_to_string).unwrap_or_default(),
        Value::Object(_) => String::new(),
    }
}

// Enhanced product-page extraction helpers.

#[derive(Debug, Clone, serde::Serialize)]
pub struct SKUVariant {
    pub name: String,
    pub values: Vec<String>,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub sku_id: String,
}

pub fn extract_sku_variants(html: &str) -> Vec<SKUVariant> {
    let mut variants = Vec::new();
    let mut seen = std::collections::HashSet::new();
    for payload in raw_embedded_json_payloads(html) {
        if let Ok(value) = serde_json::from_str::<Value>(&payload) {
            walk_for_variants(&value, &mut variants, &mut seen, 0, 6);
            if variants.len() >= 20 {
                variants.truncate(20);
                return variants;
            }
        }
    }
    for pattern in [
        r#""(color|colour|size|storage|style|version)"\s*:\s*"([^"]+)""#,
        r#"data-(?:sku|variant|spec)[^=]*=["']([^"']+)["']"#,
    ] {
        if let Ok(regex) = Regex::new(pattern) {
            for capture in regex.captures_iter(html) {
                let (name, value) = if capture.len() > 2 {
                    (
                        capture.get(1).map(|m| m.as_str()).unwrap_or("variant"),
                        capture.get(2).map(|m| m.as_str()).unwrap_or(""),
                    )
                } else {
                    ("variant", capture.get(1).map(|m| m.as_str()).unwrap_or(""))
                };
                let key = format!("{}:{}", name.to_ascii_lowercase(), value);
                if !value.is_empty() && seen.insert(key) {
                    variants.push(SKUVariant {
                        name: name.to_string(),
                        values: vec![value.to_string()],
                        sku_id: String::new(),
                    });
                }
                if variants.len() >= 20 {
                    variants.truncate(20);
                    return variants;
                }
            }
        }
    }
    variants
}

fn walk_for_variants(
    node: &Value,
    variants: &mut Vec<SKUVariant>,
    seen: &mut std::collections::HashSet<String>,
    depth: usize,
    max_depth: usize,
) {
    if depth > max_depth || variants.len() >= 20 {
        return;
    }
    match node {
        Value::Object(map) => {
            let variant_keys = [
                "skus",
                "variants",
                "specs",
                "sale_attrs",
                "attr_list",
                "spec_items",
                "variant_list",
                "skulist",
                "product_options",
                "attributes",
            ];
            for key in variant_keys {
                if let Some(Value::Array(rows)) = map.get(key) {
                    for row in rows {
                        if let Value::Object(object) = row {
                            let variant = normalize_variant(object);
                            let fingerprint = format!(
                                "{}:{}:{}",
                                variant.name,
                                variant.values.join("|"),
                                variant.sku_id
                            );
                            if fingerprint != "::" && seen.insert(fingerprint) {
                                variants.push(variant);
                            }
                            if variants.len() >= 20 {
                                return;
                            }
                        }
                    }
                }
            }
            for child in map.values() {
                walk_for_variants(child, variants, seen, depth + 1, max_depth);
                if variants.len() >= 20 {
                    return;
                }
            }
        }
        Value::Array(rows) => {
            for child in rows {
                walk_for_variants(child, variants, seen, depth + 1, max_depth);
                if variants.len() >= 20 {
                    return;
                }
            }
        }
        _ => {}
    }
}

fn normalize_variant(row: &serde_json::Map<String, Value>) -> SKUVariant {
    let name = value_as_string(first_present(
        row,
        &[
            "name",
            "attr_name",
            "attrName",
            "spec_name",
            "specName",
            "label",
        ],
    ));
    let sku_id = value_as_string(first_present(row, &["sku_id", "skuId", "id", "variantId"]));
    let mut values = Vec::new();
    for key in [
        "values",
        "options",
        "list",
        "value_list",
        "attr_values",
        "spec_values",
    ] {
        if let Some(Value::Array(rows)) = row.get(key) {
            for raw in rows.iter().take(15) {
                let text = match raw {
                    Value::Object(object) => {
                        value_as_string(first_present(object, &["name", "value", "text", "label"]))
                    }
                    other => value_to_string(other),
                };
                if !text.is_empty() {
                    values.push(text);
                }
            }
            break;
        }
    }
    if values.is_empty() {
        let text = value_as_string(first_present(row, &["value", "text", "label"]));
        if !text.is_empty() {
            values.push(text);
        }
    }
    SKUVariant {
        name,
        values,
        sku_id,
    }
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct GalleryImage {
    pub url: String,
    pub alt: String,
    pub kind: String,
}

pub fn extract_image_gallery(page_url: &str, img_srcs: &[String]) -> Vec<GalleryImage> {
    let mut gallery = Vec::new();
    let mut seen = std::collections::HashSet::new();
    let skip_needles = [
        "1x1", "spacer", "pixel", "tracker", "icon", "logo", "banner", "arrow", "blank",
    ];
    for src in img_srcs {
        let trimmed = src.trim();
        if trimmed.is_empty() {
            continue;
        }
        let lowered = trimmed.to_ascii_lowercase();
        if skip_needles.iter().any(|needle| lowered.contains(needle)) {
            continue;
        }
        let absolute = resolve_image_url(page_url, trimmed);
        if absolute.is_empty() || !seen.insert(absolute.clone()) {
            continue;
        }
        let kind = if gallery.is_empty() {
            "main"
        } else {
            "gallery"
        };
        gallery.push(GalleryImage {
            url: absolute,
            alt: String::new(),
            kind: kind.to_string(),
        });
        if gallery.len() >= 30 {
            break;
        }
    }
    gallery
}

fn resolve_image_url(base: &str, reference: &str) -> String {
    if reference.starts_with("//") {
        return format!("https:{reference}");
    }
    if reference.starts_with("http://") || reference.starts_with("https://") {
        return reference.to_string();
    }
    Url::parse(base)
        .ok()
        .and_then(|url| url.join(reference).ok())
        .map(|url| url.to_string())
        .unwrap_or_else(|| reference.to_string())
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct ParamEntry {
    pub key: String,
    pub value: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub group: String,
}

pub fn extract_parameter_table(html: &str) -> Vec<ParamEntry> {
    let mut params = Vec::new();
    for pattern in [
        r"(?is)<tr[^>]*>\s*<t[dh][^>]*>(.*?)</t[dh]>\s*<t[dh][^>]*>(.*?)</t[dh]>",
        r"(?is)<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>",
    ] {
        if let Ok(regex) = Regex::new(pattern) {
            for capture in regex.captures_iter(html) {
                let key = clean_html_text(capture.get(1).map(|m| m.as_str()).unwrap_or(""));
                let value = clean_html_text(capture.get(2).map(|m| m.as_str()).unwrap_or(""));
                if !key.is_empty() && !value.is_empty() && key.len() <= 80 {
                    params.push(ParamEntry {
                        key,
                        value,
                        group: String::new(),
                    });
                }
                if params.len() >= 50 {
                    return params;
                }
            }
        }
        if !params.is_empty() {
            return params;
        }
    }
    for payload in raw_embedded_json_payloads(html) {
        if let Ok(value) = serde_json::from_str::<Value>(&payload) {
            walk_for_params(&value, &mut params, 0, 5);
            if params.len() >= 50 {
                params.truncate(50);
                return params;
            }
        }
    }
    params
}

fn walk_for_params(node: &Value, params: &mut Vec<ParamEntry>, depth: usize, max_depth: usize) {
    if depth > max_depth || params.len() >= 50 {
        return;
    }
    match node {
        Value::Object(map) => {
            let key = value_as_string(first_present(
                map,
                &[
                    "key",
                    "name",
                    "attrName",
                    "attr_name",
                    "specName",
                    "spec_name",
                    "label",
                ],
            ));
            let value = value_as_string(first_present(
                map,
                &[
                    "value",
                    "text",
                    "attrValue",
                    "attr_value",
                    "specValue",
                    "spec_value",
                ],
            ));
            if !key.is_empty() && !value.is_empty() && key.len() <= 80 {
                params.push(ParamEntry {
                    key,
                    value,
                    group: String::new(),
                });
            }
            for child in map.values() {
                walk_for_params(child, params, depth + 1, max_depth);
                if params.len() >= 50 {
                    return;
                }
            }
        }
        Value::Array(rows) => {
            for child in rows {
                walk_for_params(child, params, depth + 1, max_depth);
                if params.len() >= 50 {
                    return;
                }
            }
        }
        _ => {}
    }
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct PromotionSignal {
    pub kind: String,
    pub text: String,
}

pub fn detect_coupons_promotions(html: &str) -> Vec<PromotionSignal> {
    let mut signals = Vec::new();
    let mut seen = std::collections::HashSet::new();
    for (kind, pattern) in [
        (
            "coupon",
            r"(?i)(coupon|优惠券|领券|满减|券后|折扣券)[^<]{0,80}",
        ),
        (
            "discount",
            r"(?i)(discount|sale|promo|促销|折扣|直降|限时)[^<]{0,80}",
        ),
        ("shipping", r"(?i)(free shipping|包邮|免邮)[^<]{0,80}"),
    ] {
        if let Ok(regex) = Regex::new(pattern) {
            for raw in regex.find_iter(html) {
                let text = clean_html_text(raw.as_str());
                let key = format!("{kind}:{text}");
                if !text.is_empty() && seen.insert(key) {
                    signals.push(PromotionSignal {
                        kind: kind.to_string(),
                        text: text_excerpt(&text, 120),
                    });
                }
                if signals.len() >= 20 {
                    return signals;
                }
            }
        }
    }
    signals
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct StockStatus {
    pub status: String,
    pub available: bool,
    pub confidence: String,
}

pub fn extract_stock_status(html: &str) -> StockStatus {
    let lowered = html.to_ascii_lowercase();
    for signal in ["out of stock", "sold out", "缺货", "无货", "售罄", "已下架"] {
        if lowered.contains(&signal.to_ascii_lowercase()) {
            return StockStatus {
                status: "out_of_stock".to_string(),
                available: false,
                confidence: "high".to_string(),
            };
        }
    }
    for signal in [
        "in stock",
        "available",
        "add to cart",
        "buy now",
        "加入购物车",
        "立即购买",
        "有货",
        "现货",
    ] {
        if lowered.contains(&signal.to_ascii_lowercase()) {
            return StockStatus {
                status: "in_stock".to_string(),
                available: true,
                confidence: "medium".to_string(),
            };
        }
    }
    StockStatus {
        status: "unknown".to_string(),
        available: false,
        confidence: "low".to_string(),
    }
}

fn clean_html_text(text: &str) -> String {
    let without_tags = Regex::new(r"(?is)<[^>]+>")
        .map(|regex| regex.replace_all(text, " ").to_string())
        .unwrap_or_else(|_| text.to_string());
    without_tags
        .replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", "\"")
        .replace("&#39;", "'")
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
}
