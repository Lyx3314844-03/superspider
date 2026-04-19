package ai

import (
	"regexp"
	"sort"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

type SummaryResult struct {
	Title   string `json:"title"`
	Summary string `json:"summary"`
	Method  string `json:"method"`
}

type ContentSummarizer struct {
	MaxSentences int
}

func NewContentSummarizer(maxSentences int) *ContentSummarizer {
	if maxSentences <= 0 {
		maxSentences = 3
	}
	return &ContentSummarizer{MaxSentences: maxSentences}
}

func (s *ContentSummarizer) Summarize(html string) SummaryResult {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return SummaryResult{Summary: strings.TrimSpace(html), Method: "fallback"}
	}
	title := strings.TrimSpace(doc.Find("title").First().Text())
	if title == "" {
		title = strings.TrimSpace(doc.Find("h1").First().Text())
	}
	description := strings.TrimSpace(firstMetaContent(doc, "meta[name='description'], meta[property='og:description']"))
	if description != "" {
		return SummaryResult{Title: title, Summary: description, Method: "meta_description"}
	}
	text := extractMainText(doc)
	sentences := splitSentences(text)
	if len(sentences) <= s.MaxSentences {
		return SummaryResult{Title: title, Summary: strings.Join(sentences, " "), Method: "extractive"}
	}
	wordFreq := calculateWordFrequency(text)
	scored := make([]scoredSentence, 0, len(sentences))
	for index, sentence := range sentences {
		scored = append(scored, scoredSentence{
			Index:    index,
			Score:    scoreSentence(sentence, wordFreq, index, len(sentences)),
			Sentence: sentence,
		})
	}
	sort.Slice(scored, func(i, j int) bool { return scored[i].Score > scored[j].Score })
	if len(scored) > s.MaxSentences {
		scored = scored[:s.MaxSentences]
	}
	sort.Slice(scored, func(i, j int) bool { return scored[i].Index < scored[j].Index })
	parts := make([]string, 0, len(scored))
	for _, item := range scored {
		parts = append(parts, item.Sentence)
	}
	return SummaryResult{Title: title, Summary: strings.Join(parts, " "), Method: "extractive"}
}

type scoredSentence struct {
	Index    int
	Score    float64
	Sentence string
}

func firstMetaContent(doc *goquery.Document, selector string) string {
	var value string
	doc.Find(selector).EachWithBreak(func(_ int, selection *goquery.Selection) bool {
		value = strings.TrimSpace(selection.AttrOr("content", ""))
		return value == ""
	})
	return value
}

func extractMainText(doc *goquery.Document) string {
	selectors := []string{"article", ".content", ".main-content", ".article-content", ".post-content"}
	for _, selector := range selectors {
		text := strings.TrimSpace(doc.Find(selector).First().Text())
		if text != "" {
			return text
		}
	}
	return strings.TrimSpace(doc.Text())
}

func splitSentences(text string) []string {
	re := regexp.MustCompile(`[。！？.!?]+`)
	raw := re.Split(text, -1)
	sentences := make([]string, 0, len(raw))
	for _, sentence := range raw {
		trimmed := strings.TrimSpace(sentence)
		if trimmed != "" {
			sentences = append(sentences, trimmed)
		}
	}
	return sentences
}

func calculateWordFrequency(text string) map[string]int {
	re := regexp.MustCompile(`\w+`)
	stopWords := map[string]struct{}{
		"the": {}, "a": {}, "an": {}, "and": {}, "or": {}, "but": {}, "in": {}, "on": {}, "at": {}, "to": {},
		"for": {}, "的": {}, "了": {}, "是": {}, "在": {}, "我": {}, "有": {}, "和": {}, "就": {}, "不": {},
	}
	freq := map[string]int{}
	for _, word := range re.FindAllString(strings.ToLower(text), -1) {
		if len(word) <= 1 {
			continue
		}
		if _, blocked := stopWords[word]; blocked {
			continue
		}
		freq[word]++
	}
	return freq
}

func scoreSentence(sentence string, freq map[string]int, index, total int) float64 {
	re := regexp.MustCompile(`\w+`)
	words := re.FindAllString(strings.ToLower(sentence), -1)
	if len(words) == 0 {
		return 0
	}
	score := 0.0
	for _, word := range words {
		score += float64(freq[word])
	}
	if index == 0 || index == total-1 {
		score += 1
	}
	lengthPenalty := 1.0
	if len(words) > 40 {
		lengthPenalty = 0.8
	}
	return score * lengthPenalty / float64(len(words))
}
