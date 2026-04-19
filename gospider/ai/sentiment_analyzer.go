package ai

import (
	"strings"

	"github.com/PuerkitoBio/goquery"
)

type SentimentResult struct {
	Sentiment     string   `json:"sentiment"`
	Score         float64  `json:"score"`
	PositiveCount int      `json:"positive_count"`
	NegativeCount int      `json:"negative_count"`
	PositiveWords []string `json:"positive_words"`
	NegativeWords []string `json:"negative_words"`
}

type SentimentAnalyzer struct {
	positiveWords map[string]struct{}
	negativeWords map[string]struct{}
}

func NewSentimentAnalyzer() *SentimentAnalyzer {
	return &SentimentAnalyzer{
		positiveWords: toWordSet([]string{
			"好", "优秀", "出色", "完美", "棒", "赞", "喜欢", "爱", "推荐", "值得", "满意", "精彩",
			"good", "great", "excellent", "amazing", "wonderful", "love", "like", "best", "perfect", "awesome",
		}),
		negativeWords: toWordSet([]string{
			"差", "糟糕", "烂", "坏", "失望", "不满", "讨厌", "恨", "垃圾", "失败", "错误", "问题", "故障",
			"bad", "terrible", "awful", "horrible", "worst", "hate", "dislike", "disappointed", "poor",
		}),
	}
}

func (a *SentimentAnalyzer) AnalyzeHTML(html string) SentimentResult {
	text := extractPlainText(html)
	return a.AnalyzeText(text)
}

func (a *SentimentAnalyzer) AnalyzeText(text string) SentimentResult {
	normalized := strings.ToLower(text)
	positiveWords := findContainedWords(normalized, a.positiveWords)
	negativeWords := findContainedWords(normalized, a.negativeWords)
	total := len(positiveWords) + len(negativeWords)

	result := SentimentResult{
		Sentiment:     "neutral",
		Score:         0.5,
		PositiveCount: len(positiveWords),
		NegativeCount: len(negativeWords),
		PositiveWords: positiveWords,
		NegativeWords: negativeWords,
	}
	if total == 0 {
		return result
	}

	score := float64(len(positiveWords)) / float64(total)
	result.Score = round2(score)
	switch {
	case score > 0.6:
		result.Sentiment = "positive"
	case score < 0.4:
		result.Sentiment = "negative"
	}
	return result
}

func AnalyzeSentiment(html string) SentimentResult {
	return NewSentimentAnalyzer().AnalyzeHTML(html)
}

func extractPlainText(html string) string {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return html
	}
	return strings.TrimSpace(doc.Text())
}

func toWordSet(words []string) map[string]struct{} {
	set := make(map[string]struct{}, len(words))
	for _, word := range words {
		set[strings.ToLower(word)] = struct{}{}
	}
	return set
}

func findContainedWords(text string, wordSet map[string]struct{}) []string {
	found := make([]string, 0)
	seen := map[string]struct{}{}
	for word := range wordSet {
		if _, ok := seen[word]; ok {
			continue
		}
		if strings.Contains(text, word) {
			seen[word] = struct{}{}
			found = append(found, word)
		}
	}
	return found
}

func round2(value float64) float64 {
	return float64(int(value*100+0.5)) / 100
}
