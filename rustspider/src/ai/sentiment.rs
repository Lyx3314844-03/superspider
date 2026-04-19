use scraper::Html;

#[derive(Debug, Clone, PartialEq)]
pub struct SentimentResult {
    pub sentiment: String,
    pub score: f64,
    pub positive_count: usize,
    pub negative_count: usize,
    pub positive_words: Vec<String>,
    pub negative_words: Vec<String>,
}

pub struct SentimentAnalyzer {
    positive_words: &'static [&'static str],
    negative_words: &'static [&'static str],
}

impl Default for SentimentAnalyzer {
    fn default() -> Self {
        Self {
            positive_words: &[
                "好",
                "优秀",
                "出色",
                "完美",
                "棒",
                "赞",
                "喜欢",
                "爱",
                "推荐",
                "值得",
                "满意",
                "精彩",
                "good",
                "great",
                "excellent",
                "amazing",
                "wonderful",
                "love",
                "like",
                "best",
                "perfect",
                "awesome",
            ],
            negative_words: &[
                "差",
                "糟糕",
                "烂",
                "坏",
                "失望",
                "不满",
                "讨厌",
                "恨",
                "垃圾",
                "失败",
                "错误",
                "问题",
                "故障",
                "bad",
                "terrible",
                "awful",
                "horrible",
                "worst",
                "hate",
                "dislike",
                "disappointed",
                "poor",
            ],
        }
    }
}

impl SentimentAnalyzer {
    pub fn analyze_html(&self, html: &str) -> SentimentResult {
        let text = Html::parse_document(html)
            .root_element()
            .text()
            .collect::<Vec<_>>()
            .join(" ");
        self.analyze_text(&text)
    }

    pub fn analyze_text(&self, text: &str) -> SentimentResult {
        let normalized = text.to_lowercase();
        let positive_words = find_words(&normalized, self.positive_words);
        let negative_words = find_words(&normalized, self.negative_words);
        let total = positive_words.len() + negative_words.len();
        let score = if total == 0 {
            0.5
        } else {
            positive_words.len() as f64 / total as f64
        };
        let sentiment = if score > 0.6 {
            "positive"
        } else if score < 0.4 {
            "negative"
        } else {
            "neutral"
        };
        SentimentResult {
            sentiment: sentiment.to_string(),
            score: ((score * 100.0) + 0.5).floor() / 100.0,
            positive_count: positive_words.len(),
            negative_count: negative_words.len(),
            positive_words,
            negative_words,
        }
    }
}

fn find_words(text: &str, words: &[&str]) -> Vec<String> {
    let mut found = Vec::new();
    for word in words {
        if text.contains(&word.to_lowercase()) && !found.iter().any(|item| item == word) {
            found.push((*word).to_string());
        }
    }
    found
}
