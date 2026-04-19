package com.javaspider.ai;

import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Pattern;

public final class ContentSummarizer {
    private static final Pattern SENTENCE_SPLIT = Pattern.compile("[。！？.!?]+");
    private static final List<String> MAIN_SELECTORS = List.of(
        "article",
        ".content",
        ".main-content",
        ".article-content",
        ".post-content"
    );

    private final int maxSentences;

    public ContentSummarizer() {
        this(3);
    }

    public ContentSummarizer(int maxSentences) {
        this.maxSentences = Math.max(1, maxSentences);
    }

    public SummaryResult summarize(String html) {
        Document document = Jsoup.parse(html == null ? "" : html);
        String title = textOrContent(document.selectFirst("title"));
        if (title.isBlank()) {
            title = textOrContent(document.selectFirst("h1"));
        }
        String description = contentFor(document, "meta[name=description], meta[property=og:description]");
        if (!description.isBlank()) {
            return new SummaryResult(title, description, "meta_description");
        }

        String text = extractMainText(document);
        List<String> sentences = splitSentences(text);
        if (sentences.size() <= maxSentences) {
            return new SummaryResult(title, String.join(" ", sentences), "extractive");
        }

        Map<String, Integer> frequencies = calculateWordFrequency(text);
        List<ScoredSentence> scored = new ArrayList<>();
        for (int i = 0; i < sentences.size(); i++) {
            scored.add(new ScoredSentence(i, scoreSentence(sentences.get(i), frequencies, i, sentences.size()), sentences.get(i)));
        }
        scored.sort(Comparator.comparingDouble(ScoredSentence::score).reversed());
        scored = scored.subList(0, Math.min(maxSentences, scored.size()));
        scored.sort(Comparator.comparingInt(ScoredSentence::index));
        List<String> selected = scored.stream().map(ScoredSentence::sentence).toList();
        return new SummaryResult(title, String.join(" ", selected), "extractive");
    }

    private String extractMainText(Document document) {
        for (String selector : MAIN_SELECTORS) {
            Element element = document.selectFirst(selector);
            if (element != null) {
                String text = element.text().trim();
                if (!text.isBlank()) {
                    return text;
                }
            }
        }
        return document.text().trim();
    }

    private List<String> splitSentences(String text) {
        List<String> sentences = new ArrayList<>();
        for (String sentence : SENTENCE_SPLIT.split(text == null ? "" : text)) {
            String trimmed = sentence.trim();
            if (!trimmed.isBlank()) {
                sentences.add(trimmed);
            }
        }
        return sentences;
    }

    private Map<String, Integer> calculateWordFrequency(String text) {
        Map<String, Integer> frequencies = new LinkedHashMap<>();
        for (String token : (text == null ? "" : text).toLowerCase(Locale.ROOT).split("\\W+")) {
            if (token.length() <= 1 || STOP_WORDS.contains(token)) {
                continue;
            }
            frequencies.merge(token, 1, Integer::sum);
        }
        return frequencies;
    }

    private double scoreSentence(String sentence, Map<String, Integer> frequencies, int index, int total) {
        String[] words = sentence.toLowerCase(Locale.ROOT).split("\\W+");
        double score = 0.0d;
        int counted = 0;
        for (String word : words) {
            if (word.length() <= 1) {
                continue;
            }
            score += frequencies.getOrDefault(word, 0);
            counted++;
        }
        if (counted == 0) {
            return 0.0d;
        }
        if (index == 0 || index == total - 1) {
            score += 1.0d;
        }
        if (counted > 40) {
            score *= 0.8d;
        }
        return score / counted;
    }

    private String contentFor(Document document, String selector) {
        Element element = document.selectFirst(selector);
        return textOrContent(element);
    }

    private String textOrContent(Element element) {
        if (element == null) {
            return "";
        }
        String content = element.attr("content").trim();
        return content.isBlank() ? element.text().trim() : content;
    }

    private static final java.util.Set<String> STOP_WORDS = java.util.Set.of(
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "的", "了", "是", "在", "我", "有", "和", "就", "不"
    );

    private record ScoredSentence(int index, double score, String sentence) {
    }

    public record SummaryResult(String title, String summary, String method) {
        public Map<String, Object> toMap() {
            return Map.of("title", title, "summary", summary, "method", method);
        }
    }
}
