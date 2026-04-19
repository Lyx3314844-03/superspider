use regex::Regex;
use scraper::{Html, Selector};
use std::collections::BTreeMap;

pub type EntityExtractionResult = BTreeMap<String, Vec<String>>;

#[derive(Default)]
pub struct EntityExtractor;

impl EntityExtractor {
    pub fn extract(&self, html: &str) -> EntityExtractionResult {
        let document = Html::parse_document(html);
        let text = document.root_element().text().collect::<Vec<_>>().join(" ");
        let mut result = BTreeMap::new();
        let patterns = BTreeMap::from([
            (
                "email",
                Regex::new(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b").unwrap(),
            ),
            ("phone", Regex::new(r"(?:\+?\d[\d\s()./\-]{6,}\d)").unwrap()),
            (
                "url",
                Regex::new(r#"https?://[^\s<>"{}|\\^`\[\]]+"#).unwrap(),
            ),
            (
                "date",
                Regex::new(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b")
                    .unwrap(),
            ),
            (
                "time",
                Regex::new(r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?\b").unwrap(),
            ),
            ("money", Regex::new(r"[\$€£￥¥]\s*\d+[,.]?\d*").unwrap()),
            ("percentage", Regex::new(r"\d+\.?\d*\s*%").unwrap()),
        ]);
        for (entity_type, pattern) in patterns {
            let values = unique(
                pattern
                    .find_iter(&text)
                    .map(|capture| capture.as_str().to_string())
                    .collect(),
            );
            if !values.is_empty() {
                result.insert(entity_type.to_string(), values);
            }
        }

        let persons = unique(extract_texts(
            &document,
            "meta[name='author'], .author, .byline, [itemprop='author']",
            true,
        ));
        if !persons.is_empty() {
            result.insert("persons".to_string(), persons);
        }
        let organizations = unique(extract_texts(
            &document,
            "meta[name='application-name'], meta[name='copyright'], .organization, .org",
            true,
        ));
        if !organizations.is_empty() {
            result.insert("organizations".to_string(), organizations);
        }
        let locations = unique(extract_texts(
            &document,
            "[itemprop='location'], .location, .address",
            false,
        ));
        if !locations.is_empty() {
            result.insert("locations".to_string(), locations);
        }
        let products = unique(extract_texts(&document, ".product-name, .product-title, [itemprop='name'], meta[property='product:name'], h1.product-title", true));
        if !products.is_empty() {
            result.insert("products".to_string(), products);
        }
        result
    }
}

fn extract_texts(document: &Html, selector: &str, include_meta_content: bool) -> Vec<String> {
    let selector = Selector::parse(selector).expect("selector");
    document
        .select(&selector)
        .filter_map(|node| {
            if include_meta_content {
                if let Some(content) = node.value().attr("content") {
                    let trimmed = content.trim();
                    if !trimmed.is_empty() {
                        return Some(trimmed.to_string());
                    }
                }
            }
            let text = node.text().collect::<Vec<_>>().join(" ");
            let trimmed = text.trim();
            if trimmed.is_empty() || trimmed.len() >= 200 {
                None
            } else {
                Some(trimmed.to_string())
            }
        })
        .collect()
}

fn unique(values: Vec<String>) -> Vec<String> {
    let mut result = Vec::new();
    for value in values {
        let trimmed = value.trim().to_string();
        if trimmed.is_empty() || result.iter().any(|item| item == &trimmed) {
            continue;
        }
        result.push(trimmed);
    }
    result
}
