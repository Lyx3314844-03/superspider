package com.javaspider.ai;

import org.jsoup.Jsoup;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

public final class SentimentAnalyzer {
    private static final Set<String> POSITIVE_WORDS = Set.of(
        "好", "优秀", "出色", "完美", "棒", "赞", "喜欢", "爱", "推荐", "值得", "满意", "精彩",
        "good", "great", "excellent", "amazing", "wonderful", "love", "like", "best", "perfect", "awesome"
    );
    private static final Set<String> NEGATIVE_WORDS = Set.of(
        "差", "糟糕", "烂", "坏", "失望", "不满", "讨厌", "恨", "垃圾", "失败", "错误", "问题", "故障",
        "bad", "terrible", "awful", "horrible", "worst", "hate", "dislike", "disappointed", "poor"
    );

    public SentimentResult analyze(String html) {
        return analyzeText(Jsoup.parse(html == null ? "" : html).text());
    }

    public SentimentResult analyzeText(String text) {
        String normalized = (text == null ? "" : text).toLowerCase(Locale.ROOT);
        List<String> positive = findContainedWords(normalized, POSITIVE_WORDS);
        List<String> negative = findContainedWords(normalized, NEGATIVE_WORDS);
        int total = positive.size() + negative.size();
        double score = total == 0 ? 0.5d : (double) positive.size() / total;
        String sentiment = "neutral";
        if (score > 0.6d) {
            sentiment = "positive";
        } else if (score < 0.4d) {
            sentiment = "negative";
        }
        return new SentimentResult(
            sentiment,
            Math.round(score * 100.0d) / 100.0d,
            positive.size(),
            negative.size(),
            positive,
            negative
        );
    }

    private List<String> findContainedWords(String text, Set<String> words) {
        Set<String> found = new LinkedHashSet<>();
        for (String word : words) {
            if (text.contains(word.toLowerCase(Locale.ROOT))) {
                found.add(word);
            }
        }
        return List.copyOf(found);
    }

    public record SentimentResult(
        String sentiment,
        double score,
        int positiveCount,
        int negativeCount,
        List<String> positiveWords,
        List<String> negativeWords
    ) {
        public Map<String, Object> toMap() {
            return Map.of(
                "sentiment", sentiment,
                "score", score,
                "positive_count", positiveCount,
                "negative_count", negativeCount,
                "positive_words", positiveWords,
                "negative_words", negativeWords
            );
        }
    }
}
