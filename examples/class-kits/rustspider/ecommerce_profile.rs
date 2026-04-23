use regex::Regex;
use rustspider::scrapy::Response;
use serde_json::Value;
use url::Url;

pub const DEFAULT_SITE_FAMILY: &str = "jd";

#[derive(Clone)]
pub struct EcommerceProfile {
    pub family: &'static str,
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
        "taobao" => EcommerceProfile {
            family: "taobao",
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
            family: "tmall",
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
            family: "pinduoduo",
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
            family: "amazon",
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
            family: "jd",
            catalog_url: "https://search.jd.com/Search?keyword=iphone",
            detail_url: "https://item.jd.com/100000000000.html",
            review_url:
                "https://club.jd.com/comment/productPageComments.action?productId=100000000000",
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
    DEFAULT_SITE_FAMILY.to_string()
}

pub fn text_excerpt(text: &str, limit: usize) -> String {
    let normalized = text.split_whitespace().collect::<Vec<_>>().join(" ");
    normalized.chars().take(limit).collect()
}
