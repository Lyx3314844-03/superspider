use std::collections::BTreeMap;
use std::env;
use std::sync::Arc;

use rustspider::scrapy::{CrawlerProcess, FeedExporter, Item, Output, Request, Spider};
use serde_json::{Map, Value};

mod profile;

use profile::{
    best_title, build_jd_price_api_url, collect_image_links, collect_matches,
    collect_product_links, collect_video_links, extract_api_candidates,
    extract_embedded_json_blocks, extract_jd_catalog_products, extract_jd_item_id,
    extract_json_ld_products, first_link_with_keywords, first_match, profile_for_family,
    site_family_from_response, text_excerpt, DEFAULT_SITE_FAMILY,
};

fn make_ecommerce_catalog_spider(site_family: &str) -> Spider {
    let profile = profile_for_family(site_family);
    Spider::new(
        "ecommerce-catalog",
        Arc::new(|response| {
            let family = site_family_from_response(response);
            let current = profile_for_family(&family);
            let links = response.xpath("//a/@href").get_all();
            let json_ld_products = extract_json_ld_products(&response.text, 5);
            let summary_item = Item::new()
                .set(
                    "kind",
                    if family == "jd" {
                        "jd_catalog_page"
                    } else {
                        "ecommerce_catalog_page"
                    },
                )
                .set("site_family", family.clone())
                .set("runner", current.runner)
                .set("title", best_title(response))
                .set("url", response.url.clone())
                .set(
                    "product_link_candidates",
                    collect_product_links(&response.url, links.clone(), &current, 20),
                )
                .set(
                    "next_page",
                    first_link_with_keywords(&response.url, links.clone(), current.next_link_keywords),
                )
                .set(
                    "sku_candidates",
                    collect_matches(&response.text, current.item_id_patterns, 10),
                )
                .set(
                    "price_excerpt",
                    first_match(&response.text, current.price_patterns),
                )
                .set(
                    "image_candidates",
                    collect_image_links(&response.url, response.xpath("//img/@src").get_all(), 10),
                )
                .set(
                    "video_candidates",
                    collect_video_links(
                        &response.url,
                        [
                            response.xpath("//video/@src").get_all(),
                            response.xpath("//source/@src").get_all(),
                        ]
                        .concat(),
                        10,
                    ),
                )
                .set("script_sources", response.xpath("//script/@src").get_all())
                .set("api_candidates", extract_api_candidates(&response.text, 20))
                .set(
                    "embedded_json_blocks",
                    extract_embedded_json_blocks(&response.text, 5, 2000),
                )
                .set("json_ld_products", json_ld_products.clone())
                .set("page_excerpt", text_excerpt(&response.text, 800))
                .set("note", "Public universal ecommerce catalog page extraction.");

            if family == "jd" {
                let products = extract_jd_catalog_products(&response.text);
                if !products.is_empty() {
                    let source_url = response.url.clone();
                    let captured_family = family.clone();
                    let captured_products = products.clone();
                    let request = Request::new(
                        build_jd_price_api_url(&collect_product_ids(&products)),
                        Some(Arc::new(move |price_response| {
                            let payload = serde_json::from_str::<Vec<Map<String, Value>>>(
                                &price_response.text,
                            )
                            .unwrap_or_default();
                            let mut price_map = BTreeMap::<String, Map<String, Value>>::new();
                            for row in payload {
                                if let Some(id) = row.get("id").and_then(|value| value.as_str()) {
                                    price_map.insert(id.to_string(), row.clone());
                                }
                            }

                            captured_products
                                .iter()
                                .map(|product| {
                                    let sku_id = product
                                        .get("product_id")
                                        .and_then(|value| value.as_str())
                                        .unwrap_or_default()
                                        .to_string();
                                    let price = price_map
                                        .get(&sku_id)
                                        .and_then(|value| value.get("p"))
                                        .cloned()
                                        .unwrap_or(Value::String(String::new()));
                                    let original_price = price_map
                                        .get(&sku_id)
                                        .and_then(|value| value.get("op"))
                                        .cloned()
                                        .unwrap_or(Value::String(String::new()));

                                    Output::Item(
                                        Item::new()
                                            .set("kind", "jd_catalog_product")
                                            .set("site_family", captured_family.clone())
                                            .set("source_url", source_url.clone())
                                            .set("product_id", product.get("product_id").cloned().unwrap_or(Value::Null))
                                            .set("name", product.get("name").cloned().unwrap_or(Value::Null))
                                            .set("url", product.get("url").cloned().unwrap_or(Value::Null))
                                            .set(
                                                "image_url",
                                                product.get("image_url").cloned().unwrap_or(Value::Null),
                                            )
                                            .set(
                                                "comment_count",
                                                product.get("comment_count").cloned().unwrap_or(Value::Null),
                                            )
                                            .set("price", price)
                                            .set("original_price", original_price),
                                    )
                                })
                                .collect::<Vec<_>>()
                        })),
                    )
                    .header(
                        "User-Agent",
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    )
                    .header("Referer", response.url.clone());
                    return vec![Output::Item(summary_item), Output::Request(request)];
                }
            }

            if family != "jd" && family != "generic" && !json_ld_products.is_empty() {
                let mut results = vec![Output::Item(summary_item)];
                for product in json_ld_products {
                    results.push(Output::Item(
                        Item::new()
                            .set("kind", format!("{family}_catalog_product"))
                            .set("site_family", family.clone())
                            .set("source_url", response.url.clone())
                            .set("product_id", product.get("sku").cloned().unwrap_or(Value::Null))
                            .set("name", product.get("name").cloned().unwrap_or(Value::Null))
                            .set("url", product.get("url").cloned().unwrap_or(Value::Null))
                            .set("image_url", product.get("image").cloned().unwrap_or(Value::Null))
                            .set("brand", product.get("brand").cloned().unwrap_or(Value::Null))
                            .set("category", product.get("category").cloned().unwrap_or(Value::Null))
                            .set("price", product.get("price").cloned().unwrap_or(Value::Null))
                            .set("currency", product.get("currency").cloned().unwrap_or(Value::Null))
                            .set("rating", product.get("rating").cloned().unwrap_or(Value::Null))
                            .set(
                                "review_count",
                                product.get("review_count").cloned().unwrap_or(Value::Null),
                            ),
                    ));
                }
                return results;
            }

            vec![Output::Item(summary_item)]
        }),
    )
    .add_start_url(profile.catalog_url)
    .with_start_meta("site_family", site_family)
    .with_start_meta("runner", profile.runner)
    .with_start_header(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    .with_start_header("Referer", "https://www.jd.com/")
}

fn make_ecommerce_detail_spider(site_family: &str) -> Spider {
    let profile = profile_for_family(site_family);
    Spider::new(
        "ecommerce-detail",
        Arc::new(|response| {
            let family = site_family_from_response(response);
            let current = profile_for_family(&family);
            let links = response.xpath("//a/@href").get_all();
            let json_ld_products = extract_json_ld_products(&response.text, 1);
            let universal_fields = BTreeMap::from([
                (
                    "embedded_json_blocks".to_string(),
                    serde_json::to_value(extract_embedded_json_blocks(&response.text, 5, 2000))
                        .unwrap_or(Value::Null),
                ),
                (
                    "api_candidates".to_string(),
                    serde_json::to_value(extract_api_candidates(&response.text, 20))
                        .unwrap_or(Value::Null),
                ),
                (
                    "script_sources".to_string(),
                    serde_json::to_value(response.xpath("//script/@src").get_all())
                        .unwrap_or(Value::Null),
                ),
                (
                    "video_candidates".to_string(),
                    serde_json::to_value(collect_video_links(
                        &response.url,
                        [
                            response.xpath("//video/@src").get_all(),
                            response.xpath("//source/@src").get_all(),
                        ]
                        .concat(),
                        10,
                    ))
                    .unwrap_or(Value::Null),
                ),
                (
                    "html_excerpt".to_string(),
                    Value::String(text_excerpt(&response.text, 800)),
                ),
                (
                    "json_ld_products".to_string(),
                    serde_json::to_value(json_ld_products.clone()).unwrap_or(Value::Null),
                ),
            ]);

            if family == "jd" {
                let item_id = extract_jd_item_id(&response.url, &response.text);
                let mut detail = BTreeMap::from([
                    ("kind".to_string(), Value::String("jd_detail_product".to_string())),
                    ("site_family".to_string(), Value::String(family.clone())),
                    ("title".to_string(), Value::String(best_title(response))),
                    ("url".to_string(), Value::String(response.url.clone())),
                    ("item_id".to_string(), Value::String(item_id.clone())),
                    (
                        "shop".to_string(),
                        Value::String(first_match(&response.text, current.shop_patterns)),
                    ),
                    (
                        "review_count".to_string(),
                        Value::String(first_match(&response.text, current.review_count_patterns)),
                    ),
                    (
                        "image_candidates".to_string(),
                        serde_json::to_value(collect_image_links(
                            &response.url,
                            response.xpath("//img/@src").get_all(),
                            10,
                        ))
                        .unwrap_or(Value::Null),
                    ),
                    (
                        "review_url".to_string(),
                        Value::String(first_link_with_keywords(
                            &response.url,
                            links,
                            current.review_link_keywords,
                        )),
                    ),
                    (
                        "html_excerpt".to_string(),
                        Value::String(text_excerpt(&response.text, 800)),
                    ),
                    (
                        "note".to_string(),
                        Value::String(
                            "Public universal ecommerce detail extraction with JD price fast path."
                                .to_string(),
                        ),
                    ),
                ]);
                detail.extend(universal_fields.clone());

                if !item_id.is_empty() {
                    let captured_detail = detail.clone();
                    let request = Request::new(
                        build_jd_price_api_url(&[item_id]),
                        Some(Arc::new(move |price_response| {
                            let payload = serde_json::from_str::<Vec<Map<String, Value>>>(
                                &price_response.text,
                            )
                            .unwrap_or_default();
                            let first = payload.first();
                            vec![Output::Item(item_from_detail_map(
                                &captured_detail,
                                first.and_then(|row| row.get("p")).cloned(),
                                first.and_then(|row| row.get("op")).cloned(),
                            ))]
                        })),
                    )
                    .header(
                        "User-Agent",
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    )
                    .header("Referer", response.url.clone());
                    return vec![Output::Request(request)];
                }

                return vec![Output::Item(item_from_detail_map(&detail, None, None))];
            }

            if family != "jd" && family != "generic" && !json_ld_products.is_empty() {
                let product = &json_ld_products[0];
                return vec![Output::Item(
                    Item::new()
                        .set("kind", format!("{family}_detail_product"))
                        .set("site_family", family)
                        .set(
                            "title",
                            fallback_value(
                                product.get("name").cloned(),
                                Value::String(best_title(response)),
                            ),
                        )
                        .set(
                            "url",
                            fallback_value(
                                product.get("url").cloned(),
                                Value::String(response.url.clone()),
                            ),
                        )
                        .set(
                            "item_id",
                            fallback_value(
                                product.get("sku").cloned(),
                                Value::String(first_match(&response.text, current.item_id_patterns)),
                            ),
                        )
                        .set(
                            "price",
                            fallback_value(
                                product.get("price").cloned(),
                                Value::String(first_match(&response.text, current.price_patterns)),
                            ),
                        )
                        .set("currency", product.get("currency").cloned().unwrap_or(Value::Null))
                        .set("brand", product.get("brand").cloned().unwrap_or(Value::Null))
                        .set("category", product.get("category").cloned().unwrap_or(Value::Null))
                        .set(
                            "rating",
                            fallback_value(
                                product.get("rating").cloned(),
                                Value::String(first_match(&response.text, current.rating_patterns)),
                            ),
                        )
                        .set(
                            "review_count",
                            fallback_value(
                                product.get("review_count").cloned(),
                                Value::String(first_match(
                                    &response.text,
                                    current.review_count_patterns,
                                )),
                            ),
                        )
                        .set("shop", first_match(&response.text, current.shop_patterns))
                        .set(
                            "review_url",
                            first_link_with_keywords(
                                &response.url,
                                links,
                                current.review_link_keywords,
                            ),
                        )
                        .set(
                            "embedded_json_blocks",
                            universal_fields
                                .get("embedded_json_blocks")
                                .cloned()
                                .unwrap_or(Value::Null),
                        )
                        .set(
                            "api_candidates",
                            universal_fields.get("api_candidates").cloned().unwrap_or(Value::Null),
                        )
                        .set(
                            "script_sources",
                            universal_fields.get("script_sources").cloned().unwrap_or(Value::Null),
                        )
                        .set(
                            "json_ld_products",
                            universal_fields
                                .get("json_ld_products")
                                .cloned()
                                .unwrap_or(Value::Null),
                        )
                        .set(
                            "video_candidates",
                            universal_fields.get("video_candidates").cloned().unwrap_or(Value::Null),
                        )
                        .set(
                            "html_excerpt",
                            universal_fields.get("html_excerpt").cloned().unwrap_or(Value::Null),
                        )
                        .set("note", "Public ecommerce detail fast path via JSON-LD product extraction."),
                )];
            }

            vec![Output::Item(
                Item::new()
                    .set("kind", "ecommerce_detail")
                    .set("site_family", family)
                    .set("title", best_title(response))
                    .set("url", response.url.clone())
                    .set("item_id", first_match(&response.text, current.item_id_patterns))
                    .set("price", first_match(&response.text, current.price_patterns))
                    .set("shop", first_match(&response.text, current.shop_patterns))
                    .set(
                        "review_count",
                        first_match(&response.text, current.review_count_patterns),
                    )
                    .set(
                        "image_candidates",
                        collect_image_links(
                            &response.url,
                            response.xpath("//img/@src").get_all(),
                            10,
                        ),
                    )
                    .set(
                        "review_url",
                        first_link_with_keywords(
                            &response.url,
                            links,
                            current.review_link_keywords,
                        ),
                    )
                    .set(
                        "embedded_json_blocks",
                        universal_fields
                            .get("embedded_json_blocks")
                            .cloned()
                            .unwrap_or(Value::Null),
                    )
                    .set(
                        "api_candidates",
                        universal_fields.get("api_candidates").cloned().unwrap_or(Value::Null),
                    )
                    .set(
                        "script_sources",
                        universal_fields.get("script_sources").cloned().unwrap_or(Value::Null),
                    )
                    .set(
                        "json_ld_products",
                        universal_fields
                            .get("json_ld_products")
                            .cloned()
                            .unwrap_or(Value::Null),
                    )
                    .set(
                        "video_candidates",
                        universal_fields.get("video_candidates").cloned().unwrap_or(Value::Null),
                    )
                    .set(
                        "html_excerpt",
                        universal_fields.get("html_excerpt").cloned().unwrap_or(Value::Null),
                    )
                    .set("note", "Public universal ecommerce detail extraction."),
            )]
        }),
    )
    .add_start_url(profile.detail_url)
    .with_start_meta("site_family", site_family)
    .with_start_meta("runner", profile.runner)
    .with_start_header(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    .with_start_header("Referer", "https://www.jd.com/")
}

fn make_ecommerce_review_spider(site_family: &str) -> Spider {
    let profile = profile_for_family(site_family);
    Spider::new(
        "ecommerce-review",
        Arc::new(|response| {
            let family = site_family_from_response(response);
            let current = profile_for_family(&family);
            let json_ld_products = extract_json_ld_products(&response.text, 1);
            let embedded_json_blocks = extract_embedded_json_blocks(&response.text, 5, 2000);
            let api_candidates = extract_api_candidates(&response.text, 20);
            let script_sources = response.xpath("//script/@src").get_all();
            let video_candidates = collect_video_links(
                &response.url,
                [
                    response.xpath("//video/@src").get_all(),
                    response.xpath("//source/@src").get_all(),
                ]
                .concat(),
                10,
            );
            let review_excerpt = text_excerpt(&response.text, 800);

            if family == "jd" {
                let payload = serde_json::from_str::<Map<String, Value>>(&response.text)
                    .unwrap_or_default();
                let comments_preview = payload
                    .get("comments")
                    .and_then(|value| value.as_array())
                    .map(|comments| {
                        comments
                            .iter()
                            .take(5)
                            .map(|comment| {
                                let content = comment
                                    .get("content")
                                    .and_then(|value| value.as_str())
                                    .unwrap_or_default();
                                serde_json::json!({
                                    "id": comment.get("id").cloned().unwrap_or(Value::Null),
                                    "score": comment.get("score").cloned().unwrap_or(Value::Null),
                                    "nickname": comment.get("nickname").cloned().unwrap_or(Value::Null),
                                    "content": text_excerpt(content, 120),
                                })
                            })
                            .collect::<Vec<_>>()
                    })
                    .unwrap_or_default();

                return vec![Output::Item(
                    Item::new()
                        .set("kind", "jd_review_summary")
                        .set("site_family", family)
                        .set("url", response.url.clone())
                        .set(
                            "item_id",
                            payload
                                .get("productId")
                                .and_then(|value| value.as_str())
                                .map(str::to_string)
                                .unwrap_or_else(|| extract_jd_item_id(&response.url, &response.text)),
                        )
                        .set("rating", first_match(&response.text, current.rating_patterns))
                        .set(
                            "review_count",
                            payload.get("maxPage").cloned().unwrap_or(Value::Null),
                        )
                        .set("max_page", payload.get("maxPage").cloned().unwrap_or(Value::Null))
                        .set("comments_preview", comments_preview)
                        .set("embedded_json_blocks", embedded_json_blocks.clone())
                        .set("api_candidates", api_candidates.clone())
                        .set("script_sources", script_sources.clone())
                        .set("json_ld_products", json_ld_products.clone())
                        .set("video_candidates", video_candidates.clone())
                        .set("excerpt", review_excerpt.clone())
                        .set(
                            "note",
                            "Public universal ecommerce review extraction with JD review fast path.",
                        ),
                )];
            }

            if family != "jd" && family != "generic" && !json_ld_products.is_empty() {
                let product = &json_ld_products[0];
                return vec![Output::Item(
                    Item::new()
                        .set("kind", format!("{family}_review_summary"))
                        .set("site_family", family)
                        .set("url", response.url.clone())
                        .set(
                            "item_id",
                            fallback_value(
                                product.get("sku").cloned(),
                                Value::String(first_match(&response.text, current.item_id_patterns)),
                            ),
                        )
                        .set(
                            "rating",
                            fallback_value(
                                product.get("rating").cloned(),
                                Value::String(first_match(&response.text, current.rating_patterns)),
                            ),
                        )
                        .set(
                            "review_count",
                            fallback_value(
                                product.get("review_count").cloned(),
                                Value::String(first_match(
                                    &response.text,
                                    current.review_count_patterns,
                                )),
                            ),
                        )
                        .set("brand", product.get("brand").cloned().unwrap_or(Value::Null))
                        .set("category", product.get("category").cloned().unwrap_or(Value::Null))
                        .set("embedded_json_blocks", embedded_json_blocks)
                        .set("api_candidates", api_candidates)
                        .set("script_sources", script_sources)
                        .set("json_ld_products", json_ld_products)
                        .set("video_candidates", video_candidates)
                        .set("excerpt", review_excerpt)
                        .set("note", "Public ecommerce review fast path via JSON-LD aggregate rating extraction."),
                )];
            }

            vec![Output::Item(
                Item::new()
                    .set("kind", "ecommerce_review")
                    .set("site_family", family)
                    .set("url", response.url.clone())
                    .set("item_id", first_match(&response.text, current.item_id_patterns))
                    .set("rating", first_match(&response.text, current.rating_patterns))
                    .set(
                        "review_count",
                        first_match(&response.text, current.review_count_patterns),
                    )
                    .set(
                        "review_id_candidates",
                        collect_matches(
                            &response.text,
                            &[r#"(?:commentId|reviewId|id)["'=:\s]+([A-Za-z0-9_-]+)"#],
                            10,
                        ),
                    )
                    .set("embedded_json_blocks", embedded_json_blocks)
                    .set("api_candidates", api_candidates)
                    .set("script_sources", script_sources)
                    .set("json_ld_products", json_ld_products)
                    .set("video_candidates", video_candidates)
                    .set("excerpt", review_excerpt)
                    .set("note", "Public universal ecommerce review extraction."),
            )]
        }),
    )
    .add_start_url(profile.review_url)
    .with_start_meta("site_family", site_family)
    .with_start_meta("runner", profile.runner)
    .with_start_header(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    .with_start_header("Referer", "https://item.jd.com/100000000000.html")
}

fn main() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    let mode = args.get(1).map(String::as_str).unwrap_or("catalog");
    let site_family = args
        .get(2)
        .map(String::as_str)
        .unwrap_or(DEFAULT_SITE_FAMILY);

    let (spider, normalized_mode) = match mode {
        "detail" => (make_ecommerce_detail_spider(site_family), "detail"),
        "review" => (make_ecommerce_review_spider(site_family), "review"),
        _ => (make_ecommerce_catalog_spider(site_family), "catalog"),
    };

    let items = CrawlerProcess::new(spider).run()?;
    let output_path = format!("artifacts/exports/rustspider-{site_family}-{normalized_mode}.json");
    let mut exporter = FeedExporter::new("json", output_path.clone());
    for item in items.iter().cloned() {
        exporter.export_item(item);
    }
    exporter.close()?;

    println!("exported {} items to {}", items.len(), output_path);
    Ok(())
}

fn collect_product_ids(products: &[BTreeMap<String, Value>]) -> Vec<String> {
    products
        .iter()
        .filter_map(|product| product.get("product_id").and_then(|value| value.as_str()))
        .map(str::to_string)
        .collect()
}

fn item_from_detail_map(
    detail: &BTreeMap<String, Value>,
    price: Option<Value>,
    original_price: Option<Value>,
) -> Item {
    Item::new()
        .set("kind", detail.get("kind").cloned().unwrap_or(Value::Null))
        .set(
            "site_family",
            detail.get("site_family").cloned().unwrap_or(Value::Null),
        )
        .set("title", detail.get("title").cloned().unwrap_or(Value::Null))
        .set("url", detail.get("url").cloned().unwrap_or(Value::Null))
        .set(
            "item_id",
            detail.get("item_id").cloned().unwrap_or(Value::Null),
        )
        .set("price", price.unwrap_or(Value::String(String::new())))
        .set(
            "original_price",
            original_price.unwrap_or(Value::String(String::new())),
        )
        .set("shop", detail.get("shop").cloned().unwrap_or(Value::Null))
        .set(
            "review_count",
            detail.get("review_count").cloned().unwrap_or(Value::Null),
        )
        .set(
            "image_candidates",
            detail
                .get("image_candidates")
                .cloned()
                .unwrap_or(Value::Null),
        )
        .set(
            "review_url",
            detail.get("review_url").cloned().unwrap_or(Value::Null),
        )
        .set(
            "html_excerpt",
            detail.get("html_excerpt").cloned().unwrap_or(Value::Null),
        )
        .set(
            "script_sources",
            detail.get("script_sources").cloned().unwrap_or(Value::Null),
        )
        .set(
            "json_ld_products",
            detail
                .get("json_ld_products")
                .cloned()
                .unwrap_or(Value::Null),
        )
        .set(
            "video_candidates",
            detail
                .get("video_candidates")
                .cloned()
                .unwrap_or(Value::Null),
        )
        .set("note", detail.get("note").cloned().unwrap_or(Value::Null))
}

fn fallback_value(value: Option<Value>, fallback: Value) -> Value {
    match value {
        Some(Value::String(text)) if text.trim().is_empty() => fallback,
        Some(Value::Null) | None => fallback,
        Some(other) => other,
    }
}
