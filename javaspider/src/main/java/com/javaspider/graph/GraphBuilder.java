package com.javaspider.graph;

import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class GraphBuilder {
    private final Map<String, GraphNode> nodes = new LinkedHashMap<>();
    private final Map<String, GraphEdge> edges = new LinkedHashMap<>();
    private String rootId;

    public GraphBuilder buildFromHtml(String html) {
        Document document = Jsoup.parse(html == null ? "" : html);
        nodes.clear();
        edges.clear();
        rootId = "document";
        addNode(new GraphNode(rootId, "document", "html"));

        addTextNodes(document, "title", "title", "title");
        addTextNodes(document, "h1, h2, h3", "heading", "heading");
        addResourceNodes(document, "a[href]", "link", "a", "href", "link");
        addResourceNodes(document, "img[src]", "image", "img", "src", "image");
        return this;
    }

    public Map<String, GraphNode> nodes() {
        return Map.copyOf(nodes);
    }

    public Map<String, GraphEdge> edges() {
        return Map.copyOf(edges);
    }

    public String rootId() {
        return rootId;
    }

    public List<GraphEdge> links() {
        return edges.values().stream().filter(edge -> "link".equals(edge.relation())).toList();
    }

    public List<GraphEdge> images() {
        return edges.values().stream().filter(edge -> "image".equals(edge.relation())).toList();
    }

    public Map<String, Integer> stats() {
        Map<String, Integer> stats = new LinkedHashMap<>();
        stats.put("total_nodes", nodes.size());
        stats.put("total_edges", edges.size());
        for (GraphNode node : nodes.values()) {
            stats.merge("type_" + node.type().toLowerCase(Locale.ROOT), 1, Integer::sum);
        }
        return stats;
    }

    private void addTextNodes(Document document, String selector, String nodeType, String prefix) {
        Elements elements = document.select(selector);
        for (int index = 0; index < elements.size(); index++) {
            Element element = elements.get(index);
            String text = element.text().trim();
            if (text.isBlank()) {
                continue;
            }
            String nodeId = prefix + "-" + index;
            attachChild(nodeId);
            addNode(new GraphNode(nodeId, nodeType, element.tagName(), Map.of(), text, new ArrayList<>(), rootId));
            addEdge(new GraphEdge("contains-" + nodeId, rootId, nodeId, "contains", 1.0));
        }
    }

    private void addResourceNodes(Document document, String selector, String nodeType, String tag, String attribute, String relation) {
        Elements elements = document.select(selector);
        for (int index = 0; index < elements.size(); index++) {
            Element element = elements.get(index);
            String target = element.attr(attribute).trim();
            if (target.isBlank()) {
                continue;
            }
            String nodeId = relation + "-" + index;
            Map<String, String> attributes = Map.of(attribute, target);
            attachChild(nodeId);
            addNode(new GraphNode(nodeId, nodeType, tag, attributes, element.text().trim(), new ArrayList<>(), rootId));
            addEdge(new GraphEdge("contains-" + nodeId, rootId, nodeId, "contains", 1.0));
            addEdge(new GraphEdge(relation + "-" + nodeId, nodeId, target, relation, 1.0));
        }
    }

    private void attachChild(String childId) {
        GraphNode root = nodes.get(rootId);
        if (root != null) {
            root.children().add(childId);
        }
    }

    private void addNode(GraphNode node) {
        nodes.put(node.id(), node);
    }

    private void addEdge(GraphEdge edge) {
        edges.put(edge.id(), edge);
    }

    public record GraphNode(
        String id,
        String type,
        String tag,
        Map<String, String> attributes,
        String text,
        List<String> children,
        String parent
    ) {
        public GraphNode(String id, String type, String tag) {
            this(id, type, tag, Map.of(), "", new ArrayList<>(), null);
        }
    }

    public record GraphEdge(
        String id,
        String source,
        String target,
        String relation,
        double weight
    ) {
    }
}
