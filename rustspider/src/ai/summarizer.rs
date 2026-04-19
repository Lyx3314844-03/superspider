use regex::Regex;
use scraper::{Html, Selector};
use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq)]
pub struct SummaryResult {
    pub title: String,
    pub summary: String,
    pub method: String,
}

pub struct ContentSummarizer {
    max_sentences: usize,
}

impl Default for ContentSummarizer {
    fn default() -> Self {
        Self { max_sentences: 3 }
    }
}

impl ContentSummarizer {
    pub fn new(max_sentences: usize) -> Self {
        Self {
            max_sentences: max_sentences.max(1),
        }
    }

    pub fn summarize(&self, html: &str) -> SummaryResult {
        let document = Html::parse_document(html);
        let title = select_text(&document, "title")
            .or_else(|| select_text(&document, "h1"))
            .unwrap_or_default();
        if let Some(description) = select_meta(
            &document,
            r#"meta[name="description"], meta[property="og:description"]"#,
        ) {
            return SummaryResult {
                title,
                summary: description,
                method: "meta_description".to_string(),
            };
        }
        let text = extract_main_text(&document);
        let sentences = split_sentences(&text);
        if sentences.len() <= self.max_sentences {
            return SummaryResult {
                title,
                summary: sentences.join(" "),
                method: "extractive".to_string(),
            };
        }
        let frequencies = calculate_word_frequency(&text);
        let mut scored: Vec<(usize, f64, String)> = sentences
            .iter()
            .enumerate()
            .map(|(index, sentence)| {
                (
                    index,
                    score_sentence(sentence, &frequencies, index, sentences.len()),
                    sentence.clone(),
                )
            })
            .collect();
        scored.sort_by(|left, right| {
            right
                .1
                .partial_cmp(&left.1)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        scored.truncate(self.max_sentences);
        scored.sort_by_key(|item| item.0);
        SummaryResult {
            title,
            summary: scored
                .into_iter()
                .map(|(_, _, sentence)| sentence)
                .collect::<Vec<_>>()
                .join(" "),
            method: "extractive".to_string(),
        }
    }
}

fn select_text(document: &Html, selector: &str) -> Option<String> {
    let selector = Selector::parse(selector).ok()?;
    document
        .select(&selector)
        .next()
        .map(|node| node.text().collect::<Vec<_>>().join(" ").trim().to_string())
        .filter(|value| !value.is_empty())
}

fn select_meta(document: &Html, selector: &str) -> Option<String> {
    let selector = Selector::parse(selector).ok()?;
    document
        .select(&selector)
        .next()
        .and_then(|node| node.value().attr("content"))
        .map(str::trim)
        .map(ToOwned::to_owned)
        .filter(|value| !value.is_empty())
}

fn extract_main_text(document: &Html) -> String {
    for selector in [
        "article",
        ".content",
        ".main-content",
        ".article-content",
        ".post-content",
    ] {
        if let Some(text) = select_text(document, selector) {
            return text;
        }
    }
    document
        .root_element()
        .text()
        .collect::<Vec<_>>()
        .join(" ")
        .trim()
        .to_string()
}

fn split_sentences(text: &str) -> Vec<String> {
    let re = Regex::new(r"[。！？.!?]+").expect("sentence regex");
    re.split(text)
        .map(str::trim)
        .filter(|sentence| !sentence.is_empty())
        .map(ToOwned::to_owned)
        .collect()
}

fn calculate_word_frequency(text: &str) -> HashMap<String, usize> {
    let stop_words = [
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "的", "了", "是",
        "在", "我", "有", "和", "就", "不",
    ];
    let stop_words = stop_words
        .into_iter()
        .collect::<std::collections::HashSet<_>>();
    let re = Regex::new(r"\w+").expect("word regex");
    let mut frequencies = HashMap::new();
    for token in re.find_iter(&text.to_lowercase()) {
        let word = token.as_str();
        if word.len() <= 1 || stop_words.contains(word) {
            continue;
        }
        *frequencies.entry(word.to_string()).or_insert(0) += 1;
    }
    frequencies
}

fn score_sentence(
    sentence: &str,
    frequencies: &HashMap<String, usize>,
    index: usize,
    total: usize,
) -> f64 {
    let re = Regex::new(r"\w+").expect("word regex");
    let words: Vec<String> = re
        .find_iter(&sentence.to_lowercase())
        .map(|match_| match_.as_str().to_string())
        .filter(|word| word.len() > 1)
        .collect();
    if words.is_empty() {
        return 0.0;
    }
    let mut score = words
        .iter()
        .map(|word| *frequencies.get(word).unwrap_or(&0) as f64)
        .sum::<f64>();
    if index == 0 || index + 1 == total {
        score += 1.0;
    }
    if words.len() > 40 {
        score *= 0.8;
    }
    score / words.len() as f64
}
