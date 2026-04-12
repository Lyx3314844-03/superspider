// Rustspider 图结构模块

//! 图结构爬虫
//!
//! 吸收 ScrapegraphAI 的图结构设计

use scraper::{Html, Selector};
use serde::Serialize;
use std::collections::{HashMap, HashSet, VecDeque};
use std::sync::{Arc, Mutex};

/// 图节点
#[derive(Debug, Clone, Serialize)]
pub struct Node {
    pub id: String,
    pub node_type: String,
    pub tag: String,
    pub attributes: HashMap<String, String>,
    pub text: String,
    pub children: Vec<String>,
    pub parent: Option<String>,
}

impl Node {
    pub fn new(id: String, node_type: String, tag: String) -> Self {
        Self {
            id,
            node_type,
            tag,
            attributes: HashMap::new(),
            text: String::new(),
            children: Vec::new(),
            parent: None,
        }
    }

    pub fn with_text(mut self, text: String) -> Self {
        self.text = text;
        self
    }

    pub fn with_attributes(mut self, attrs: HashMap<String, String>) -> Self {
        self.attributes = attrs;
        self
    }

    pub fn with_parent(mut self, parent: String) -> Self {
        self.parent = Some(parent);
        self
    }

    pub fn add_child(&mut self, child_id: String) {
        self.children.push(child_id);
    }
}

/// 图边
#[derive(Debug, Clone, Serialize)]
pub struct Edge {
    pub id: String,
    pub source: String,
    pub target: String,
    pub relation: String,
    pub weight: f64,
}

impl Edge {
    pub fn new(id: String, source: String, target: String, relation: String) -> Self {
        Self {
            id,
            source,
            target,
            relation,
            weight: 1.0,
        }
    }

    pub fn with_weight(mut self, weight: f64) -> Self {
        self.weight = weight;
        self
    }
}

/// 图构建器
pub struct GraphBuilder {
    pub nodes: HashMap<String, Node>,
    pub edges: HashMap<String, Edge>,
    pub root_id: Option<String>,
}

impl GraphBuilder {
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            edges: HashMap::new(),
            root_id: None,
        }
    }

    pub fn add_node(&mut self, node: Node) {
        let id = node.id.clone();
        self.nodes.insert(id, node);
    }

    pub fn add_edge(&mut self, edge: Edge) {
        let id = edge.id.clone();
        self.edges.insert(id, edge);
    }

    pub fn set_root(&mut self, root_id: String) {
        self.root_id = Some(root_id);
    }

    pub fn get_node(&self, node_id: &str) -> Option<&Node> {
        self.nodes.get(node_id)
    }

    pub fn get_node_mut(&mut self, node_id: &str) -> Option<&mut Node> {
        self.nodes.get_mut(node_id)
    }

    pub fn get_children(&self, node_id: &str) -> Vec<&Node> {
        let node = match self.get_node(node_id) {
            Some(n) => n,
            None => return Vec::new(),
        };

        node.children
            .iter()
            .filter_map(|id| self.nodes.get(id))
            .collect()
    }

    pub fn get_parent(&self, node_id: &str) -> Option<&Node> {
        let node = self.get_node(node_id)?;

        match &node.parent {
            Some(parent_id) => self.nodes.get(parent_id),
            None => None,
        }
    }

    pub fn get_nodes_by_type(&self, node_type: &str) -> Vec<&Node> {
        self.nodes
            .values()
            .filter(|n| n.node_type == node_type)
            .collect()
    }

    pub fn get_nodes_by_tag(&self, tag: &str) -> Vec<&Node> {
        self.nodes.values().filter(|n| n.tag == tag).collect()
    }

    pub fn get_links(&self) -> Vec<&Edge> {
        self.edges
            .values()
            .filter(|e| e.relation == "link")
            .collect()
    }

    pub fn get_images(&self) -> Vec<&Edge> {
        self.edges
            .values()
            .filter(|e| e.relation == "image")
            .collect()
    }

    pub fn bfs(&self, start_id: &str) -> Vec<&Node> {
        let mut visited = HashSet::new();
        let mut queue = VecDeque::new();
        let mut result = Vec::new();

        queue.push_back(start_id);

        while let Some(node_id) = queue.pop_front() {
            if visited.contains(node_id) {
                continue;
            }

            if let Some(node) = self.get_node(node_id) {
                visited.insert(node_id);
                result.push(node);

                for child_id in &node.children {
                    queue.push_back(child_id);
                }
            }
        }

        result
    }

    pub fn dfs(&self, start_id: &str) -> Vec<&Node> {
        let mut visited = HashSet::new();
        let mut stack = Vec::new();
        let mut result = Vec::new();

        stack.push(start_id);

        while let Some(node_id) = stack.pop() {
            if visited.contains(node_id) {
                continue;
            }

            if let Some(node) = self.get_node(node_id) {
                visited.insert(node_id);
                result.push(node);

                // 逆序压栈，保证顺序遍历
                for child_id in node.children.iter().rev() {
                    stack.push(child_id);
                }
            }
        }

        result
    }

    pub fn find_path(&self, start_id: &str, end_id: &str) -> Option<Vec<String>> {
        let mut visited = HashSet::new();
        let mut queue = VecDeque::new();

        queue.push_back((start_id, vec![start_id.to_string()]));

        while let Some((node_id, path)) = queue.pop_front() {
            if node_id == end_id {
                return Some(path);
            }

            if visited.contains(node_id) {
                continue;
            }

            visited.insert(node_id);

            if let Some(node) = self.get_node(node_id) {
                for child_id in &node.children {
                    let mut new_path = path.clone();
                    new_path.push(child_id.clone());
                    queue.push_back((child_id, new_path));
                }
            }
        }

        None
    }

    pub fn extract_subgraph(&self, start_id: &str, max_depth: usize) -> GraphBuilder {
        let mut subgraph = GraphBuilder::new();
        let mut visited = HashSet::new();
        let mut queue = VecDeque::new();

        queue.push_back((start_id, 0));

        while let Some((node_id, depth)) = queue.pop_front() {
            if depth > max_depth || visited.contains(node_id) {
                continue;
            }

            if let Some(node) = self.get_node(node_id) {
                // 复制节点
                let mut new_node = node.clone();
                new_node.children.clear();
                subgraph.add_node(new_node);
                visited.insert(node_id);

                // 添加子节点
                for child_id in &node.children {
                    queue.push_back((child_id, depth + 1));
                }
            }
        }

        subgraph
    }

    pub fn stats(&self) -> HashMap<String, usize> {
        let mut stats = HashMap::new();

        stats.insert("total_nodes".to_string(), self.nodes.len());
        stats.insert("total_edges".to_string(), self.edges.len());

        // 按类型统计
        let mut type_counts: HashMap<String, usize> = HashMap::new();
        for node in self.nodes.values() {
            *type_counts.entry(node.node_type.clone()).or_insert(0) += 1;
        }

        for (node_type, count) in type_counts {
            stats.insert(format!("type_{}", node_type), count);
        }

        stats
    }

    pub fn rebuild_from_html(&mut self, html: &str) {
        self.nodes.clear();
        self.edges.clear();
        self.root_id = None;

        let document_id = "document".to_string();
        self.add_node(Node::new(
            document_id.clone(),
            "document".to_string(),
            "html".to_string(),
        ));
        self.set_root(document_id.clone());

        let parsed = Html::parse_document(html);
        self.add_text_nodes(&parsed, &document_id, "title", "title", "title");
        self.add_text_nodes(&parsed, &document_id, "h1, h2, h3", "heading", "heading");
        self.add_resource_nodes(
            &parsed,
            &document_id,
            "a[href]",
            "link",
            "a",
            "href",
            "link",
        );
        self.add_resource_nodes(
            &parsed,
            &document_id,
            "img[src]",
            "image",
            "img",
            "src",
            "image",
        );
    }

    fn add_text_nodes(
        &mut self,
        parsed: &Html,
        parent_id: &str,
        selector: &str,
        node_type: &str,
        tag_prefix: &str,
    ) {
        let Ok(selector) = Selector::parse(selector) else {
            return;
        };
        for (index, element) in parsed.select(&selector).enumerate() {
            let text = element
                .text()
                .map(str::trim)
                .filter(|value| !value.is_empty())
                .collect::<Vec<_>>()
                .join(" ");
            if text.is_empty() {
                continue;
            }
            let node_id = format!("{tag_prefix}-{index}");
            let node = Node::new(
                node_id.clone(),
                node_type.to_string(),
                element.value().name().to_string(),
            )
            .with_text(text)
            .with_parent(parent_id.to_string());
            self.attach_child(parent_id, node_id.clone());
            self.add_node(node);
            self.add_edge(Edge::new(
                format!("contains-{parent_id}-{node_id}"),
                parent_id.to_string(),
                node_id,
                "contains".to_string(),
            ));
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn add_resource_nodes(
        &mut self,
        parsed: &Html,
        parent_id: &str,
        selector: &str,
        node_type: &str,
        tag: &str,
        attribute: &str,
        relation: &str,
    ) {
        let Ok(selector) = Selector::parse(selector) else {
            return;
        };
        for (index, element) in parsed.select(&selector).enumerate() {
            let Some(target) = element.value().attr(attribute) else {
                continue;
            };
            if target.trim().is_empty() {
                continue;
            }

            let mut attributes = HashMap::new();
            attributes.insert(attribute.to_string(), target.to_string());
            let text = element
                .text()
                .map(str::trim)
                .filter(|value| !value.is_empty())
                .collect::<Vec<_>>()
                .join(" ");

            let node_id = format!("{relation}-{index}");
            let mut node = Node::new(node_id.clone(), node_type.to_string(), tag.to_string())
                .with_parent(parent_id.to_string())
                .with_attributes(attributes);
            if !text.is_empty() {
                node = node.with_text(text);
            }

            self.attach_child(parent_id, node_id.clone());
            self.add_node(node);
            self.add_edge(Edge::new(
                format!("contains-{parent_id}-{node_id}"),
                parent_id.to_string(),
                node_id.clone(),
                "contains".to_string(),
            ));
            self.add_edge(Edge::new(
                format!("{relation}-{node_id}"),
                node_id,
                target.to_string(),
                relation.to_string(),
            ));
        }
    }

    fn attach_child(&mut self, parent_id: &str, child_id: String) {
        if let Some(parent) = self.get_node_mut(parent_id) {
            parent.add_child(child_id);
        }
    }
}

impl Default for GraphBuilder {
    fn default() -> Self {
        Self::new()
    }
}

/// 线程安全的图构建器
pub struct ThreadSafeGraph {
    inner: Arc<Mutex<GraphBuilder>>,
}

impl ThreadSafeGraph {
    pub fn new() -> Self {
        Self {
            inner: Arc::new(Mutex::new(GraphBuilder::new())),
        }
    }

    pub fn add_node(&self, node: Node) {
        let mut graph = self.inner.lock().unwrap();
        graph.add_node(node);
    }

    pub fn add_edge(&self, edge: Edge) {
        let mut graph = self.inner.lock().unwrap();
        graph.add_edge(edge);
    }

    pub fn get_node(&self, node_id: &str) -> Option<Node> {
        let graph = self.inner.lock().unwrap();
        graph.get_node(node_id).cloned()
    }

    pub fn bfs(&self, start_id: &str) -> Vec<Node> {
        let graph = self.inner.lock().unwrap();
        graph.bfs(start_id).iter().map(|n| (*n).clone()).collect()
    }

    pub fn dfs(&self, start_id: &str) -> Vec<Node> {
        let graph = self.inner.lock().unwrap();
        graph.dfs(start_id).iter().map(|n| (*n).clone()).collect()
    }
}

impl Default for ThreadSafeGraph {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_graph_builder() {
        let mut graph = GraphBuilder::new();

        let node1 = Node::new("1".to_string(), "element".to_string(), "div".to_string());
        let node2 = Node::new("2".to_string(), "element".to_string(), "h1".to_string());
        let node3 = Node::new("3".to_string(), "link".to_string(), "a".to_string());

        graph.add_node(node1);
        graph.add_node(node2);
        graph.add_node(node3);

        assert_eq!(graph.nodes.len(), 3);
        assert_eq!(graph.get_nodes_by_tag("div").len(), 1);
        assert_eq!(graph.get_nodes_by_tag("a").len(), 1);
    }

    #[test]
    fn test_bfs() {
        let mut graph = GraphBuilder::new();

        let mut node1 = Node::new("1".to_string(), "root".to_string(), "html".to_string());
        let mut node2 = Node::new("2".to_string(), "element".to_string(), "body".to_string());
        let node3 = Node::new("3".to_string(), "element".to_string(), "div".to_string());

        node1.add_child("2".to_string());
        node2.add_child("3".to_string());

        graph.add_node(node1);
        graph.add_node(node2);
        graph.add_node(node3);
        graph.set_root("1".to_string());

        let result = graph.bfs("1");
        assert_eq!(result.len(), 3);
    }

    #[test]
    fn test_rebuild_from_html_extracts_links_images_and_title() {
        let mut graph = GraphBuilder::new();
        graph.rebuild_from_html(
            r#"
            <html>
              <head><title>Graph Demo</title></head>
              <body>
                <h1>Headline</h1>
                <a href="https://example.com/page">Read more</a>
                <img src="https://example.com/image.png" alt="demo" />
              </body>
            </html>
            "#,
        );

        assert_eq!(graph.root_id.as_deref(), Some("document"));
        assert!(!graph.get_nodes_by_type("link").is_empty());
        assert!(!graph.get_nodes_by_type("image").is_empty());
        assert!(graph
            .get_nodes_by_tag("title")
            .iter()
            .any(|node| node.text == "Graph Demo"));
        assert!(graph
            .get_links()
            .iter()
            .any(|edge| edge.target == "https://example.com/page"));
        assert!(graph
            .get_images()
            .iter()
            .any(|edge| edge.target == "https://example.com/image.png"));
    }
}
