package parser

import (
	"net/url"
	"sort"
	"strings"

	"github.com/PuerkitoBio/goquery"
	"golang.org/x/net/html"
)

type ElementSnapshot struct {
	Tag   string            `json:"tag"`
	CSS   string            `json:"css"`
	XPath string            `json:"xpath"`
	Text  string            `json:"text,omitempty"`
	Attrs map[string]string `json:"attrs,omitempty"`
}

type DevToolsNetworkArtifact struct {
	URL          string `json:"url"`
	Method       string `json:"method,omitempty"`
	Status       int    `json:"status,omitempty"`
	ResourceType string `json:"resource_type,omitempty"`
}

type ReverseRecommendation struct {
	Kind     string   `json:"kind"`
	Priority int      `json:"priority"`
	Reason   string   `json:"reason"`
	Evidence []string `json:"evidence"`
}

type DevToolsReport struct {
	Elements               []ElementSnapshot         `json:"elements"`
	ScriptSources          []string                  `json:"script_sources"`
	InlineScriptSamples    []string                  `json:"inline_script_samples"`
	NetworkCandidates      []DevToolsNetworkArtifact `json:"network_candidates"`
	ConsoleEvents          []map[string]string       `json:"console_events,omitempty"`
	ReverseRecommendations []ReverseRecommendation   `json:"reverse_recommendations"`
	Summary                map[string]interface{}    `json:"summary"`
}

func (r *DevToolsReport) BestReverseRoute() *ReverseRecommendation {
	if r == nil || len(r.ReverseRecommendations) == 0 {
		return nil
	}
	return &r.ReverseRecommendations[0]
}

type DevToolsAnalyzer struct{}

func NewDevToolsAnalyzer() *DevToolsAnalyzer {
	return &DevToolsAnalyzer{}
}

func (a *DevToolsAnalyzer) Analyze(htmlText string, network []DevToolsNetworkArtifact, console []map[string]string) (*DevToolsReport, error) {
	parser := NewHTMLParser(htmlText)
	if parser == nil || parser.doc == nil {
		return nil, nil
	}
	elements := make([]ElementSnapshot, 0)
	parser.doc.Find("*").Each(func(_ int, selection *goquery.Selection) {
		if node := selection.Get(0); node != nil {
			elements = append(elements, snapshotElement(selection, node))
		}
	})
	sources, inline := scriptArtifacts(parser.doc)
	networkCandidates := networkCandidates(network)
	recommendations := recommendReverseRoutes(htmlText, sources, inline, networkCandidates)
	return &DevToolsReport{
		Elements:               elements,
		ScriptSources:          sources,
		InlineScriptSamples:    inline,
		NetworkCandidates:      networkCandidates,
		ConsoleEvents:          console,
		ReverseRecommendations: recommendations,
		Summary: map[string]interface{}{
			"element_count":           len(elements),
			"script_count":            len(sources) + len(inline),
			"network_candidate_count": len(networkCandidates),
			"best_reverse_route":      bestReverseKind(recommendations),
		},
	}, nil
}

func snapshotElement(selection *goquery.Selection, node *html.Node) ElementSnapshot {
	attrs := map[string]string{}
	for _, attr := range []string{"id", "class", "name", "type", "href", "src", "role", "aria-label", "data-testid", "data-test", "placeholder", "action", "method"} {
		if value := strings.TrimSpace(attrValue(node, attr)); value != "" {
			attrs[attr] = value
		}
	}
	text := strings.TrimSpace(selection.Text())
	if len([]rune(text)) > 120 {
		text = string([]rune(text)[:120])
	}
	return ElementSnapshot{
		Tag:   goquery.NodeName(selection),
		CSS:   fullCSSPath(node),
		XPath: fullXPath(node),
		Text:  text,
		Attrs: attrs,
	}
}

func scriptArtifacts(doc *goquery.Document) ([]string, []string) {
	sources := []string{}
	inline := []string{}
	doc.Find("script").Each(func(_ int, selection *goquery.Selection) {
		if src, ok := selection.Attr("src"); ok && strings.TrimSpace(src) != "" {
			sources = append(sources, strings.TrimSpace(src))
			return
		}
		code := strings.TrimSpace(selection.Text())
		if code == "" {
			return
		}
		if len([]rune(code)) > 2000 {
			code = string([]rune(code)[:2000])
		}
		inline = append(inline, code)
	})
	return sources, inline
}

func networkCandidates(network []DevToolsNetworkArtifact) []DevToolsNetworkArtifact {
	result := []DevToolsNetworkArtifact{}
	seen := map[string]bool{}
	for _, entry := range network {
		if entry.URL == "" || seen[entry.URL] {
			continue
		}
		signal := strings.ToLower(entry.URL + " " + entry.ResourceType)
		if isReverseNetworkCandidate(signal, strings.ToLower(entry.ResourceType)) {
			seen[entry.URL] = true
			result = append(result, normalizeNetworkArtifact(entry))
		}
	}
	return result
}

func normalizeNetworkArtifact(entry DevToolsNetworkArtifact) DevToolsNetworkArtifact {
	if parsed, err := url.Parse(entry.URL); err == nil && parsed.Host != "" {
		entry.URL = parsed.String()
	}
	return entry
}

func isReverseNetworkCandidate(signal, resourceType string) bool {
	if resourceType == "script" || resourceType == "xhr" || resourceType == "fetch" || resourceType == "websocket" || resourceType == "document" {
		return true
	}
	for _, token := range []string{"api", "sign", "token", "encrypt", "decrypt", "jsonp", "webpack"} {
		if strings.Contains(signal, token) {
			return true
		}
	}
	return false
}

func recommendReverseRoutes(htmlText string, sources []string, inline []string, network []DevToolsNetworkArtifact) []ReverseRecommendation {
	parts := []string{htmlText}
	parts = append(parts, sources...)
	parts = append(parts, inline...)
	for _, entry := range network {
		parts = append(parts, entry.URL)
	}
	corpus := strings.ToLower(strings.Join(parts, "\n"))
	recommendations := []ReverseRecommendation{}
	for _, spec := range []struct {
		kind     string
		priority int
		reason   string
		markers  []string
	}{
		{"analyze_crypto", 100, "发现加密、签名或摘要相关标记，优先交给 Node.js crypto 逆向分析", []string{"cryptojs", "crypto.subtle", "aes", "rsa", "md5", "sha1", "sha256", "encrypt", "decrypt", "signature", "sign"}},
		{"analyze_webpack", 90, "发现 webpack 模块运行时，适合进入模块表和导出函数逆向", []string{"__webpack_require__", "webpackjsonp", "webpackchunk", "webpack://"}},
		{"simulate_browser", 80, "脚本依赖浏览器运行时对象，适合用 Node.js 浏览器环境模拟", []string{"localstorage", "sessionstorage", "navigator.", "document.", "window.", "canvas", "webdriver"}},
		{"analyze_ast", 60, "存在外链或内联脚本，适合进行 AST 结构分析和函数定位", []string{".js", "function", "=>", "eval(", "new function"}},
	} {
		evidence := matchedMarkers(corpus, spec.markers)
		if len(evidence) == 0 {
			continue
		}
		recommendations = append(recommendations, ReverseRecommendation{Kind: spec.kind, Priority: spec.priority, Reason: spec.reason, Evidence: evidence})
	}
	sort.Slice(recommendations, func(i, j int) bool {
		if recommendations[i].Priority != recommendations[j].Priority {
			return recommendations[i].Priority > recommendations[j].Priority
		}
		return recommendations[i].Kind < recommendations[j].Kind
	})
	return recommendations
}

func matchedMarkers(corpus string, markers []string) []string {
	result := []string{}
	for _, marker := range markers {
		if strings.Contains(corpus, strings.ToLower(marker)) {
			result = append(result, marker)
		}
		if len(result) >= 8 {
			break
		}
	}
	return result
}

func bestReverseKind(recommendations []ReverseRecommendation) string {
	if len(recommendations) == 0 {
		return ""
	}
	return recommendations[0].Kind
}
