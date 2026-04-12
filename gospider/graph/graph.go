package graph

import (
	"strconv"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

type Node struct {
	ID         string            `json:"id"`
	Type       string            `json:"type"`
	Tag        string            `json:"tag"`
	Attributes map[string]string `json:"attributes,omitempty"`
	Text       string            `json:"text,omitempty"`
	Children   []string          `json:"children,omitempty"`
	Parent     string            `json:"parent,omitempty"`
}

type Edge struct {
	ID       string  `json:"id"`
	Source   string  `json:"source"`
	Target   string  `json:"target"`
	Relation string  `json:"relation"`
	Weight   float64 `json:"weight"`
}

type Builder struct {
	Nodes  map[string]Node `json:"nodes"`
	Edges  map[string]Edge `json:"edges"`
	RootID string          `json:"root_id"`
}

func NewBuilder() *Builder {
	return &Builder{
		Nodes: make(map[string]Node),
		Edges: make(map[string]Edge),
	}
}

func (b *Builder) BuildFromHTML(html string) error {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return err
	}

	b.Nodes = make(map[string]Node)
	b.Edges = make(map[string]Edge)
	b.RootID = "document"
	b.addNode(Node{
		ID:   b.RootID,
		Type: "document",
		Tag:  "html",
	})

	b.addTextNodes(doc, "title", "title", "title")
	b.addTextNodes(doc, "h1, h2, h3", "heading", "heading")
	b.addResourceNodes(doc, "a[href]", "link", "a", "href", "link")
	b.addResourceNodes(doc, "img[src]", "image", "img", "src", "image")
	return nil
}

func (b *Builder) Links() []Edge {
	edges := make([]Edge, 0)
	for _, edge := range b.Edges {
		if edge.Relation == "link" {
			edges = append(edges, edge)
		}
	}
	return edges
}

func (b *Builder) Images() []Edge {
	edges := make([]Edge, 0)
	for _, edge := range b.Edges {
		if edge.Relation == "image" {
			edges = append(edges, edge)
		}
	}
	return edges
}

func (b *Builder) Stats() map[string]int {
	stats := map[string]int{
		"total_nodes": len(b.Nodes),
		"total_edges": len(b.Edges),
	}
	for _, node := range b.Nodes {
		stats["type_"+node.Type]++
	}
	return stats
}

func (b *Builder) addTextNodes(doc *goquery.Document, selector, nodeType, prefix string) {
	doc.Find(selector).Each(func(index int, selection *goquery.Selection) {
		text := strings.TrimSpace(selection.Text())
		if text == "" {
			return
		}
		nodeID := prefix + "-" + itoa(index)
		b.attachChild(nodeID)
		b.addNode(Node{
			ID:       nodeID,
			Type:     nodeType,
			Tag:      goquery.NodeName(selection),
			Text:     text,
			Parent:   b.RootID,
			Children: []string{},
		})
		b.addEdge(Edge{
			ID:       "contains-" + nodeID,
			Source:   b.RootID,
			Target:   nodeID,
			Relation: "contains",
			Weight:   1,
		})
	})
}

func (b *Builder) addResourceNodes(doc *goquery.Document, selector, nodeType, tag, attr, relation string) {
	doc.Find(selector).Each(func(index int, selection *goquery.Selection) {
		target, ok := selection.Attr(attr)
		if !ok || strings.TrimSpace(target) == "" {
			return
		}
		nodeID := relation + "-" + itoa(index)
		attributes := map[string]string{attr: target}
		text := strings.TrimSpace(selection.Text())
		b.attachChild(nodeID)
		b.addNode(Node{
			ID:         nodeID,
			Type:       nodeType,
			Tag:        tag,
			Attributes: attributes,
			Text:       text,
			Parent:     b.RootID,
			Children:   []string{},
		})
		b.addEdge(Edge{
			ID:       "contains-" + nodeID,
			Source:   b.RootID,
			Target:   nodeID,
			Relation: "contains",
			Weight:   1,
		})
		b.addEdge(Edge{
			ID:       relation + "-" + nodeID,
			Source:   nodeID,
			Target:   target,
			Relation: relation,
			Weight:   1,
		})
	})
}

func (b *Builder) attachChild(childID string) {
	root := b.Nodes[b.RootID]
	root.Children = append(root.Children, childID)
	b.Nodes[b.RootID] = root
}

func (b *Builder) addNode(node Node) {
	b.Nodes[node.ID] = node
}

func (b *Builder) addEdge(edge Edge) {
	b.Edges[edge.ID] = edge
}

func itoa(value int) string {
	return strconv.Itoa(value)
}
