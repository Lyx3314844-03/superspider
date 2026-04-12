"""
图构建器

构建网页的图结构表示
节点：页面元素
边：元素间的关系

@author: Lan
@version: 2.0.0
@date: 2026-03-20
"""

from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
import hashlib


@dataclass
class Node:
    """图节点"""
    id: str
    type: str  # 'element', 'text', 'link', 'image', etc.
    tag: str
    attributes: Dict[str, str] = field(default_factory=dict)
    text: str = ""
    children: List[str] = field(default_factory=list)
    parent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'type': self.type,
            'tag': self.tag,
            'attributes': self.attributes,
            'text': self.text,
            'children': self.children,
            'parent': self.parent,
        }


@dataclass
class Edge:
    """图边"""
    id: str
    source: str
    target: str
    relation: str  # 'parent', 'sibling', 'link', 'contains', etc.
    weight: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'source': self.source,
            'target': self.target,
            'relation': self.relation,
            'weight': self.weight,
        }


class GraphBuilder:
    """
    图构建器
    
    从 HTML 构建图结构
    """
    
    def __init__(self):
        """初始化图构建器"""
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        self.root_id: Optional[str] = None
    
    def build(self, html: str) -> 'GraphBuilder':
        """
        从 HTML 构建图
        
        Args:
            html: HTML 内容
            
        Returns:
            self
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 从 body 开始构建
        body = soup.find('body')
        if body:
            self.root_id = self._build_tree(body, None)
        else:
            # 如果没有 body，从 html 开始
            self.root_id = self._build_tree(soup.find('html'), None)
        
        return self
    
    def _build_tree(self, element, parent_id: Optional[str]) -> Optional[str]:
        """
        递归构建 DOM 树
        
        Args:
            element: BeautifulSoup 元素
            parent_id: 父节点 ID
            
        Returns:
            节点 ID
        """
        if not element:
            return None
        
        # 生成节点 ID
        node_id = self._generate_node_id(element)
        
        # 跳过已存在的节点
        if node_id in self.nodes:
            return node_id
        
        # 确定节点类型
        node_type = self._determine_node_type(element)
        
        # 创建节点
        node = Node(
            id=node_id,
            type=node_type,
            tag=element.name if hasattr(element, 'name') else '#text',
            attributes=self._extract_attributes(element),
            text=self._extract_text(element),
            parent=parent_id,
        )
        
        self.nodes[node_id] = node
        
        # 添加父子关系
        if parent_id:
            parent_node = self.nodes.get(parent_id)
            if parent_node:
                parent_node.children.append(node_id)
                self._add_edge(parent_id, node_id, 'parent')
        
        # 处理子节点
        if hasattr(element, 'children'):
            for child in element.children:
                child_id = self._build_tree(child, node_id)
                if child_id:
                    # 添加兄弟关系
                    if len(node.children) > 1:
                        prev_child = node.children[-2]
                        self._add_edge(prev_child, child_id, 'sibling')
        
        # 特殊处理链接
        if element.name == 'a' and element.get('href'):
            self._add_edge(node_id, element.get('href'), 'link')
        
        # 特殊处理图片
        if element.name == 'img' and element.get('src'):
            self._add_edge(node_id, element.get('src'), 'image')
        
        return node_id
    
    def _generate_node_id(self, element) -> str:
        """生成节点唯一 ID"""
        if hasattr(element, 'name') and element.name:
            # 使用标签名 + 属性 + 位置生成 ID
            content = f"{element.name}{str(element.attrs)}{element.sourceline}"
        else:
            content = str(element)[:100]
        
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _determine_node_type(self, element) -> str:
        """确定节点类型"""
        if not hasattr(element, 'name'):
            return 'text'
        
        tag = element.name
        
        type_mapping = {
            'a': 'link',
            'img': 'image',
            'video': 'video',
            'audio': 'audio',
            'form': 'form',
            'input': 'input',
            'button': 'button',
            'table': 'table',
            'ul': 'list',
            'ol': 'list',
            'h1': 'heading',
            'h2': 'heading',
            'h3': 'heading',
            'h4': 'heading',
            'h5': 'heading',
            'h6': 'heading',
            'p': 'paragraph',
            'div': 'container',
            'span': 'inline',
            'article': 'article',
            'section': 'section',
            'header': 'header',
            'footer': 'footer',
            'nav': 'navigation',
        }
        
        return type_mapping.get(tag, 'element')
    
    def _extract_attributes(self, element) -> Dict[str, str]:
        """提取属性"""
        if not hasattr(element, 'attrs'):
            return {}
        
        # 只保留重要属性
        important_attrs = [
            'id', 'class', 'name', 'href', 'src', 'alt',
            'title', 'type', 'value', 'placeholder',
            'data-', 'aria-', 'itemprop',
        ]
        
        result = {}
        for attr, value in element.attrs.items():
            if any(imp in attr for imp in important_attrs):
                result[attr] = value if isinstance(value, str) else ' '.join(value)
        
        return result
    
    def _extract_text(self, element) -> str:
        """提取文本"""
        if not hasattr(element, 'get_text'):
            return str(element)
        
        text = element.get_text(separator=' ', strip=True)
        
        # 限制长度
        if len(text) > 500:
            text = text[:500] + '...'
        
        return text
    
    def _add_edge(self, source: str, target: str, relation: str, weight: float = 1.0):
        """添加边"""
        edge_id = f"{source}_{target}_{relation}"
        
        if edge_id not in self.edges:
            self.edges[edge_id] = Edge(
                id=edge_id,
                source=source,
                target=target,
                relation=relation,
                weight=weight,
            )
    
    def get_nodes_by_type(self, node_type: str) -> List[Node]:
        """按类型获取节点"""
        return [n for n in self.nodes.values() if n.type == node_type]
    
    def get_nodes_by_tag(self, tag: str) -> List[Node]:
        """按标签获取节点"""
        return [n for n in self.nodes.values() if n.tag == tag]
    
    def get_children(self, node_id: str) -> List[Node]:
        """获取子节点"""
        node = self.nodes.get(node_id)
        if not node:
            return []
        
        return [self.nodes[cid] for cid in node.children if cid in self.nodes]
    
    def get_parent(self, node_id: str) -> Optional[Node]:
        """获取父节点"""
        node = self.nodes.get(node_id)
        if not node or not node.parent:
            return None
        
        return self.nodes.get(node.parent)
    
    def get_links(self) -> List[Edge]:
        """获取所有链接"""
        return [e for e in self.edges.values() if e.relation == 'link']
    
    def get_images(self) -> List[Edge]:
        """获取所有图片"""
        return [e for e in self.edges.values() if e.relation == 'image']
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'nodes': {nid: n.to_dict() for nid, n in self.nodes.items()},
            'edges': {eid: e.to_dict() for eid, e in self.edges.items()},
            'root': self.root_id,
            'stats': {
                'total_nodes': len(self.nodes),
                'total_edges': len(self.edges),
                'node_types': self._count_node_types(),
            },
        }
    
    def _count_node_types(self) -> Dict[str, int]:
        """统计节点类型"""
        from collections import Counter
        return dict(Counter(n.type for n in self.nodes.values()))
    
    def visualize(self) -> str:
        """生成简单的文本可视化"""
        if not self.root_id:
            return "Empty graph"
        
        lines = []
        self._visualize_node(self.root_id, 0, lines)
        return '\n'.join(lines)
    
    def _visualize_node(self, node_id: str, depth: int, lines: list):
        """递归可视化节点"""
        node = self.nodes.get(node_id)
        if not node:
            return
        
        indent = "  " * depth
        icon = self._get_node_icon(node)
        lines.append(f"{indent}{icon} {node.tag} ({node.type})")
        
        for child_id in node.children[:5]:  # 限制显示数量
            self._visualize_node(child_id, depth + 1, lines)
        
        if len(node.children) > 5:
            lines.append(f"{indent}  ... ({len(node.children) - 5} more)")
    
    def _get_node_icon(self, node: Node) -> str:
        """获取节点图标"""
        icons = {
            'link': '🔗',
            'image': '🖼️',
            'video': '🎥',
            'heading': '📝',
            'paragraph': '📄',
            'container': '📦',
            'form': '📋',
            'button': '🔘',
            'list': '📝',
        }
        return icons.get(node.type, '🔹')


# 便捷函数
def build_graph(html: str) -> GraphBuilder:
    """
    构建图的便捷函数
    
    Args:
        html: HTML 内容
        
    Returns:
        GraphBuilder 实例
    """
    builder = GraphBuilder()
    return builder.build(html)
