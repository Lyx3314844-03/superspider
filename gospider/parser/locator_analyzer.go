package parser

import (
	"fmt"
	"sort"
	"strings"

	"github.com/PuerkitoBio/goquery"
	"golang.org/x/net/html"
)

type LocatorTarget struct {
	Tag         string
	Text        string
	Role        string
	Name        string
	Placeholder string
	Attr        string
	Value       string
}

type LocatorCandidate struct {
	Kind   string
	Expr   string
	Score  int
	Reason string
}

type LocatorPlan struct {
	Candidates []LocatorCandidate
}

type LocatorAnalyzer struct{}

func NewLocatorAnalyzer() *LocatorAnalyzer {
	return &LocatorAnalyzer{}
}

func (a *LocatorAnalyzer) Analyze(htmlText string, target LocatorTarget) (*LocatorPlan, error) {
	parser := NewHTMLParser(htmlText)
	if parser == nil || parser.doc == nil {
		return nil, fmt.Errorf("html parser is not initialized")
	}
	seen := map[string]LocatorCandidate{}
	parser.doc.Find("*").Each(func(_ int, selection *goquery.Selection) {
		node := selection.Get(0)
		if node == nil {
			return
		}
		score := locatorMatchScore(selection, node, target)
		if score <= 0 {
			return
		}
		for _, candidate := range locatorCandidatesFor(parser.doc, selection, node, score) {
			key := candidate.Kind + "\x00" + candidate.Expr
			if current, ok := seen[key]; !ok || candidate.Score > current.Score {
				seen[key] = candidate
			}
		}
	})
	candidates := make([]LocatorCandidate, 0, len(seen))
	for _, candidate := range seen {
		candidates = append(candidates, candidate)
	}
	sort.Slice(candidates, func(i, j int) bool {
		if candidates[i].Score != candidates[j].Score {
			return candidates[i].Score > candidates[j].Score
		}
		if candidates[i].Kind != candidates[j].Kind {
			return candidates[i].Kind < candidates[j].Kind
		}
		return candidates[i].Expr < candidates[j].Expr
	})
	return &LocatorPlan{Candidates: candidates}, nil
}

func locatorMatchScore(selection *goquery.Selection, node *html.Node, target LocatorTarget) int {
	score := 0
	tag := strings.ToLower(goquery.NodeName(selection))
	if target.Tag != "" && strings.ToLower(target.Tag) != tag {
		return 0
	}
	if target.Tag != "" {
		score += 2
	}
	text := strings.TrimSpace(selection.Text())
	if target.Text != "" {
		if text == target.Text {
			score += 6
		} else if strings.Contains(strings.ToLower(text), strings.ToLower(target.Text)) {
			score += 3
		}
	}
	for _, item := range []struct {
		attr   string
		value  string
		weight int
	}{
		{"role", target.Role, 4},
		{"name", target.Name, 4},
		{"placeholder", target.Placeholder, 4},
	} {
		if item.value != "" && strings.Contains(strings.ToLower(attrValue(node, item.attr)), strings.ToLower(item.value)) {
			score += item.weight
		}
	}
	if target.Name != "" {
		for _, attr := range []string{"id", "aria-label", "data-testid", "data-test"} {
			if strings.Contains(strings.ToLower(attrValue(node, attr)), strings.ToLower(target.Name)) {
				score += 3
			}
		}
	}
	if target.Attr != "" && target.Value != "" && attrValue(node, target.Attr) == target.Value {
		score += 6
	}
	return score
}

func locatorCandidatesFor(doc *goquery.Document, selection *goquery.Selection, node *html.Node, score int) []LocatorCandidate {
	tag := goquery.NodeName(selection)
	candidates := []LocatorCandidate{}
	for _, attr := range []string{"id", "data-testid", "data-test", "name", "aria-label", "placeholder", "role"} {
		value := strings.TrimSpace(attrValue(node, attr))
		if value == "" {
			continue
		}
		css := fmt.Sprintf("%s[%s='%s']", tag, attr, cssQuote(value))
		if attr == "id" {
			css = "#" + cssIdent(value)
		}
		xpath := fmt.Sprintf("//%s[@%s=%s]", tag, attr, xpathLiteral(value))
		bonus := 3
		if doc.Find(css).Length() == 1 {
			bonus = 8
		}
		candidates = append(candidates,
			LocatorCandidate{Kind: "css", Expr: css, Score: score + bonus, Reason: attr + " attribute"},
			LocatorCandidate{Kind: "xpath", Expr: xpath, Score: score + bonus - 1, Reason: attr + " attribute"},
		)
	}
	text := strings.TrimSpace(selection.Text())
	if text != "" {
		if len(text) > 80 {
			text = text[:80]
		}
		candidates = append(candidates, LocatorCandidate{
			Kind: "xpath", Expr: fmt.Sprintf("//%s[contains(normalize-space(.), %s)]", tag, xpathLiteral(text)),
			Score: score + 2, Reason: "visible text",
		})
	}
	if cssPath := fullCSSPath(node); cssPath != "" {
		candidates = append(candidates, LocatorCandidate{Kind: "css", Expr: cssPath, Score: score + 1, Reason: "structural css path"})
	}
	if xpath := fullXPath(node); xpath != "" {
		candidates = append(candidates, LocatorCandidate{Kind: "xpath", Expr: xpath, Score: score + 1, Reason: "structural xpath path"})
	}
	return candidates
}

func attrValue(node *html.Node, name string) string {
	for _, attr := range node.Attr {
		if attr.Key == name {
			return attr.Val
		}
	}
	return ""
}

func cssIdent(value string) string {
	var builder strings.Builder
	for _, ch := range value {
		if (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || (ch >= '0' && ch <= '9') || ch == '_' || ch == '-' {
			builder.WriteRune(ch)
		} else {
			builder.WriteString(fmt.Sprintf("\\%x ", ch))
		}
	}
	return builder.String()
}

func cssQuote(value string) string {
	return strings.ReplaceAll(strings.ReplaceAll(value, `\`, `\\`), `'`, `\'`)
}

func xpathLiteral(value string) string {
	if !strings.Contains(value, `'`) {
		return "'" + value + "'"
	}
	if !strings.Contains(value, `"`) {
		return `"` + value + `"`
	}
	parts := strings.Split(value, `'`)
	wrapped := make([]string, 0, len(parts))
	for _, part := range parts {
		wrapped = append(wrapped, "'"+part+"'")
	}
	return "concat(" + strings.Join(wrapped, `, "'", `) + ")"
}

func fullCSSPath(node *html.Node) string {
	parts := []string{}
	for current := node; current != nil && current.Type == html.ElementNode; current = current.Parent {
		if id := attrValue(current, "id"); id != "" {
			parts = append(parts, current.Data+"#"+cssIdent(id))
			break
		}
		parts = append(parts, fmt.Sprintf("%s:nth-of-type(%d)", current.Data, siblingIndex(current)))
	}
	reverseStrings(parts)
	return strings.Join(parts, " > ")
}

func fullXPath(node *html.Node) string {
	parts := []string{}
	for current := node; current != nil && current.Type == html.ElementNode; current = current.Parent {
		if id := attrValue(current, "id"); id != "" {
			parts = append(parts, fmt.Sprintf("%s[@id=%s]", current.Data, xpathLiteral(id)))
			break
		}
		parts = append(parts, fmt.Sprintf("%s[%d]", current.Data, siblingIndex(current)))
	}
	reverseStrings(parts)
	if len(parts) == 0 {
		return ""
	}
	return "/" + strings.Join(parts, "/")
}

func siblingIndex(node *html.Node) int {
	index := 1
	for sibling := node.PrevSibling; sibling != nil; sibling = sibling.PrevSibling {
		if sibling.Type == html.ElementNode && sibling.Data == node.Data {
			index++
		}
	}
	return index
}

func reverseStrings(values []string) {
	for left, right := 0, len(values)-1; left < right; left, right = left+1, right-1 {
		values[left], values[right] = values[right], values[left]
	}
}
