// Rustspider Python 绑定模块

//! FFI 绑定
//! 
//! 提供 Python 语言绑定

use pyo3::prelude::*;
use pyo3::types::PyDict;

use crate::async_runtime::{Request, PriorityQueue, DedupQueue};
use crate::graph::{GraphBuilder, Node, Edge};
use crate::ai::{SmartParser, PageType, PageData};
use crate::spider::{SpiderEngine, SpiderConfig, SpiderBuilder, SpiderStats};

/// Python 模块：rustspider
#[pymodule]
fn rustspider(_py: Python, m: &PyModule) -> PyResult<()> {
    // 异步运行时
    m.add_class::<PyRequest>()?;
    m.add_class::<PyPriorityQueue>()?;
    m.add_class::<PyDedupQueue>()?;

    // 图结构
    m.add_class::<PyNode>()?;
    m.add_class::<PyEdge>()?;
    m.add_class::<PyGraphBuilder>()?;

    // AI
    m.add_class::<PySmartParser>()?;
    m.add_class::<PyPageType>()?;
    m.add_class::<PyPageData>()?;

    // 爬虫
    m.add_class::<PySpiderConfig>()?;
    m.add_class::<PySpiderBuilder>()?;
    m.add_class::<PySpiderEngine>()?;
    m.add_class::<PySpiderStats>()?;

    Ok(())
}

/// Python Request 包装器
#[pyclass]
#[derive(Clone)]
pub struct PyRequest {
    #[pyo3(get, set)]
    pub url: String,
    #[pyo3(get, set)]
    pub method: String,
    #[pyo3(get, set)]
    pub priority: i32,
}

#[pymethods]
impl PyRequest {
    #[new]
    #[args(url, method = "\"GET\"", priority = "0")]
    fn new(url: &str, method: &str, priority: i32) -> Self {
        Self {
            url: url.to_string(),
            method: method.to_string(),
            priority,
        }
    }

    fn to_request(&self) -> Request {
        let mut req = Request::new(self.url.clone());
        req.method = self.method.clone();
        req.priority = self.priority;
        req
    }

    fn __repr__(&self) -> String {
        format!("Request(url='{}', method='{}', priority={})", self.url, self.method, self.priority)
    }
}

/// Python 优先级队列包装器
#[pyclass]
pub struct PyPriorityQueue {
    queue: std::sync::Arc<PriorityQueue>,
}

#[pymethods]
impl PyPriorityQueue {
    #[new]
    fn new() -> Self {
        Self {
            queue: std::sync::Arc::new(PriorityQueue::new()),
        }
    }

    fn push(&self, request: &PyRequest) -> PyResult<()> {
        self.queue.push(request.to_request())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    fn pop(&self) -> PyResult<Option<PyRequest>> {
        if let Some(req) = self.queue.pop() {
            Ok(Some(PyRequest {
                url: req.url,
                method: req.method,
                priority: req.priority,
            }))
        } else {
            Ok(None)
        }
    }

    fn is_empty(&self) -> bool {
        self.queue.is_empty()
    }

    fn size(&self) -> usize {
        self.queue.size()
    }
}

/// Python 去重队列包装器
#[pyclass]
pub struct PyDedupQueue {
    queue: std::sync::Arc<DedupQueue>,
}

#[pymethods]
impl PyDedupQueue {
    #[new]
    fn new() -> Self {
        Self {
            queue: std::sync::Arc::new(DedupQueue::new(std::sync::Arc::new(PriorityQueue::new()))),
        }
    }

    fn push(&self, request: &PyRequest) -> PyResult<bool> {
        match self.queue.push(request.to_request()) {
            Ok(_) => Ok(true),
            Err(_) => Ok(false),
        }
    }

    fn pop(&self) -> PyResult<Option<PyRequest>> {
        if let Some(req) = self.queue.pop() {
            Ok(Some(PyRequest {
                url: req.url,
                method: req.method,
                priority: req.priority,
            }))
        } else {
            Ok(None)
        }
    }

    fn is_empty(&self) -> bool {
        self.queue.is_empty()
    }

    fn size(&self) -> usize {
        self.queue.size()
    }
}

/// Python Node 包装器
#[pyclass]
#[derive(Clone)]
pub struct PyNode {
    #[pyo3(get, set)]
    pub id: String,
    #[pyo3(get, set)]
    pub node_type: String,
    #[pyo3(get, set)]
    pub tag: String,
    #[pyo3(get, set)]
    pub text: String,
}

#[pymethods]
impl PyNode {
    #[new]
    #[args(id, node_type, tag, text = "\"\"")]
    fn new(id: &str, node_type: &str, tag: &str, text: &str) -> Self {
        Self {
            id: id.to_string(),
            node_type: node_type.to_string(),
            tag: tag.to_string(),
            text: text.to_string(),
        }
    }

    fn __repr__(&self) -> String {
        format!("Node(id='{}', type='{}', tag='{}')", self.id, self.node_type, self.tag)
    }
}

/// Python Edge 包装器
#[pyclass]
#[derive(Clone)]
pub struct PyEdge {
    #[pyo3(get, set)]
    pub id: String,
    #[pyo3(get, set)]
    pub source: String,
    #[pyo3(get, set)]
    pub target: String,
    #[pyo3(get, set)]
    pub relation: String,
}

#[pymethods]
impl PyEdge {
    #[new]
    #[args(id, source, target, relation)]
    fn new(id: &str, source: &str, target: &str, relation: &str) -> Self {
        Self {
            id: id.to_string(),
            source: source.to_string(),
            target: target.to_string(),
            relation: relation.to_string(),
        }
    }

    fn __repr__(&self) -> String {
        format!("Edge(id='{}', source='{}', target='{}')", self.id, self.source, self.target)
    }
}

/// Python GraphBuilder 包装器
#[pyclass]
pub struct PyGraphBuilder {
    graph: GraphBuilder,
}

#[pymethods]
impl PyGraphBuilder {
    #[new]
    fn new() -> Self {
        Self {
            graph: GraphBuilder::new(),
        }
    }

    fn add_node(&mut self, node: &PyNode) {
        let mut n = Node::new(node.id.clone(), node.node_type.clone(), node.tag.clone());
        n.text = node.text.clone();
        self.graph.add_node(n);
    }

    fn add_edge(&mut self, edge: &PyEdge) {
        let e = Edge::new(
            edge.id.clone(),
            edge.source.clone(),
            edge.target.clone(),
            edge.relation.clone(),
        );
        self.graph.add_edge(e);
    }

    fn bfs(&self, start_id: &str) -> Vec<PyNode> {
        self.graph
            .bfs(start_id)
            .iter()
            .map(|n| PyNode {
                id: n.id.clone(),
                node_type: n.node_type.clone(),
                tag: n.tag.clone(),
                text: n.text.clone(),
            })
            .collect()
    }

    fn dfs(&self, start_id: &str) -> Vec<PyNode> {
        self.graph
            .dfs(start_id)
            .iter()
            .map(|n| PyNode {
                id: n.id.clone(),
                node_type: n.node_type.clone(),
                tag: n.tag.clone(),
                text: n.text.clone(),
            })
            .collect()
    }

    fn stats(&self, py: Python) -> PyObject {
        let stats = self.graph.stats();
        let dict = PyDict::new(py);
        for (key, value) in stats {
            dict.set_item(key, value).unwrap();
        }
        dict.into()
    }
}

/// Python 页面类型包装器
#[pyclass]
#[derive(Clone, Copy)]
pub enum PyPageType {
    Article,
    Product,
    Video,
    List,
    Search,
    Generic,
}

/// Python 页面数据包装器
#[pyclass]
pub struct PyPageData {
    #[pyo3(get)]
    pub page_type: PyPageType,
    #[pyo3(get)]
    pub title: Option<String>,
    #[pyo3(get)]
    pub description: Option<String>,
    #[pyo3(get)]
    pub text: Option<String>,
}

/// Python SmartParser 包装器
#[pyclass]
pub struct PySmartParser {
    parser: SmartParser,
}

#[pymethods]
impl PySmartParser {
    #[new]
    fn new() -> Self {
        Self {
            parser: SmartParser::new(),
        }
    }

    fn detect_page_type(&self, html: &str) -> PyPageType {
        match self.parser.detect_page_type(html) {
            PageType::Article => PyPageType::Article,
            PageType::Product => PyPageType::Product,
            PageType::Video => PyPageType::Video,
            PageType::List => PyPageType::List,
            PageType::Search => PyPageType::Search,
            PageType::Generic => PyPageType::Generic,
        }
    }

    fn parse(&self, html: &str) -> PyPageData {
        let data = self.parser.parse(html);
        PyPageData {
            page_type: match data.page_type {
                PageType::Article => PyPageType::Article,
                PageType::Product => PyPageType::Product,
                PageType::Video => PyPageType::Video,
                PageType::List => PyPageType::List,
                PageType::Search => PyPageType::Search,
                PageType::Generic => PyPageType::Generic,
            },
            title: data.title,
            description: data.description,
            text: data.text,
        }
    }
}

/// Python SpiderConfig 包装器
#[pyclass]
#[derive(Clone)]
pub struct PySpiderConfig {
    #[pyo3(get, set)]
    pub name: String,
    #[pyo3(get, set)]
    pub concurrency: usize,
    #[pyo3(get, set)]
    pub max_requests: usize,
}

#[pymethods]
impl PySpiderConfig {
    #[new]
    fn new() -> Self {
        Self {
            name: "default".to_string(),
            concurrency: 5,
            max_requests: 1000,
        }
    }
}

impl Default for PySpiderConfig {
    fn default() -> Self {
        Self::new()
    }
}

/// Python SpiderBuilder 包装器
#[pyclass]
pub struct PySpiderBuilder {
    builder: SpiderBuilder,
}

#[pymethods]
impl PySpiderBuilder {
    #[new]
    fn new() -> Self {
        Self {
            builder: SpiderBuilder::new(),
        }
    }

    fn name(&self, name: &str) -> Self {
        Self {
            builder: self.builder.clone().name(name),
        }
    }

    fn concurrency(&self, concurrency: usize) -> Self {
        Self {
            builder: self.builder.clone().concurrency(concurrency),
        }
    }

    fn max_requests(&self, max_requests: usize) -> Self {
        Self {
            builder: self.builder.clone().max_requests(max_requests),
        }
    }

    fn build(&self) -> PySpiderEngine {
        PySpiderEngine {
            engine: self.builder.clone().build(),
        }
    }
}

impl Default for PySpiderBuilder {
    fn default() -> Self {
        Self::new()
    }
}

/// Python SpiderEngine 包装器
#[pyclass]
pub struct PySpiderEngine {
    engine: SpiderEngine,
}

#[pymethods]
impl PySpiderEngine {
    fn add_url(&self, url: &str) -> PyResult<()> {
        self.engine
            .add_url(url)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    fn run(&self, py: Python) -> PyResult<()> {
        // 注意：这里需要异步运行
        // 实际使用应该用 tokio 运行时
        py.allow_threads(|| {
            // 简化实现
            println!("Spider running...");
        });
        Ok(())
    }

    fn stop(&self) -> PyResult<()> {
        self.engine
            .stop()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    fn is_running(&self) -> bool {
        self.engine.is_running()
    }

    fn get_stats(&self) -> PySpiderStats {
        PySpiderStats {
            stats: self.engine.get_stats(),
        }
    }
}

/// Python SpiderStats 包装器
#[pyclass]
pub struct PySpiderStats {
    stats: SpiderStats,
}

#[pymethods]
impl PySpiderStats {
    fn __repr__(&self) -> String {
        format!("{}", self.stats)
    }

    #[getter]
    fn name(&self) -> &str {
        &self.stats.name
    }

    #[getter]
    fn running(&self) -> bool {
        self.stats.running
    }

    #[getter]
    fn requested(&self) -> usize {
        self.stats.requested
    }

    #[getter]
    fn handled(&self) -> usize {
        self.stats.handled
    }

    #[getter]
    fn failed(&self) -> usize {
        self.stats.failed
    }

    #[getter]
    fn queue_size(&self) -> usize {
        self.stats.queue_size
    }
}
