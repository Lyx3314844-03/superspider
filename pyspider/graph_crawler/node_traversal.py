"""
Pyspider 图遍历模块

实现图的 BFS/DFS 遍历和子图提取

@author: Lan
@version: 2.0.0
@date: 2026-03-20
"""

from typing import List, Dict, Any, Optional, Callable, Set
from .graph_builder import Node, GraphBuilder


class NodeTraversal:
    """节点遍历器"""

    def __init__(self, graph: GraphBuilder):
        """
        初始化遍历器

        Args:
            graph: 图构建器实例
        """
        self.graph = graph

    def bfs(self, start_id: str, visit_func: Optional[Callable] = None) -> List[Node]:
        """
        广度优先遍历 (BFS)

        Args:
            start_id: 起始节点 ID
            visit_func: 访问函数

        Returns:
            访问的节点列表
        """
        visited: Set[str] = set()
        queue = [start_id]
        result = []

        while queue:
            node_id = queue.pop(0)

            if node_id in visited:
                continue

            node = self.graph.nodes.get(node_id)
            if not node:
                continue

            visited.add(node_id)
            result.append(node)

            if visit_func:
                visit_func(node)

            # 添加子节点
            queue.extend(node.children)

        return result

    def dfs(self, start_id: str, visit_func: Optional[Callable] = None) -> List[Node]:
        """
        深度优先遍历 (DFS)

        Args:
            start_id: 起始节点 ID
            visit_func: 访问函数

        Returns:
            访问的节点列表
        """
        visited: Set[str] = set()
        stack = [start_id]
        result = []

        while stack:
            node_id = stack.pop()

            if node_id in visited:
                continue

            node = self.graph.nodes.get(node_id)
            if not node:
                continue

            visited.add(node_id)
            result.append(node)

            if visit_func:
                visit_func(node)

            # 添加子节点（逆序，保证顺序遍历）
            stack.extend(reversed(node.children))

        return result

    def traverse_by_type(self, node_type: str) -> List[Node]:
        """
        按类型遍历节点

        Args:
            node_type: 节点类型

        Returns:
            节点列表
        """
        return self.graph.get_nodes_by_type(node_type)

    def traverse_by_tag(self, tag: str) -> List[Node]:
        """
        按标签遍历节点

        Args:
            tag: 标签名

        Returns:
            节点列表
        """
        return self.graph.get_nodes_by_tag(tag)

    def traverse_links(self) -> List[Dict[str, Any]]:
        """
        遍历所有链接

        Returns:
            链接信息列表
        """
        links = []
        for edge in self.graph.get_links():
            source_node = self.graph.nodes.get(edge.source)
            if source_node:
                links.append(
                    {
                        "text": source_node.text,
                        "url": edge.target,
                        "parent": source_node.parent,
                    }
                )
        return links

    def traverse_images(self) -> List[Dict[str, Any]]:
        """
        遍历所有图片

        Returns:
            图片信息列表
        """
        images = []
        for edge in self.graph.get_images():
            source_node = self.graph.nodes.get(edge.source)
            if source_node:
                images.append(
                    {
                        "alt": source_node.attributes.get("alt", ""),
                        "src": edge.target,
                        "parent": source_node.parent,
                    }
                )
        return images

    def extract_subgraph(self, start_id: str, max_depth: int = 3) -> GraphBuilder:
        """
        提取子图

        Args:
            start_id: 起始节点 ID
            max_depth: 最大深度

        Returns:
            子图构建器
        """
        from copy import deepcopy

        subgraph = GraphBuilder()
        visited: Set[str] = set()
        queue = [(start_id, 0)]

        while queue:
            node_id, depth = queue.pop(0)

            if depth > max_depth or node_id in visited:
                continue

            node = self.graph.nodes.get(node_id)
            if not node:
                continue

            # 复制节点
            subgraph.nodes[node_id] = deepcopy(node)
            visited.add(node_id)

            # 添加子节点
            for child_id in node.children:
                queue.append((child_id, depth + 1))

        return subgraph

    def find_path(self, start_id: str, end_id: str) -> Optional[List[str]]:
        """
        查找两个节点之间的路径

        Args:
            start_id: 起始节点 ID
            end_id: 目标节点 ID

        Returns:
            路径节点 ID 列表
        """
        visited: Set[str] = set()
        queue = [(start_id, [start_id])]

        while queue:
            node_id, path = queue.pop(0)

            if node_id == end_id:
                return path

            if node_id in visited:
                continue

            visited.add(node_id)
            node = self.graph.nodes.get(node_id)

            if node:
                for child_id in node.children:
                    if child_id not in visited:
                        queue.append((child_id, path + [child_id]))

        return None

    def get_ancestors(self, node_id: str) -> List[str]:
        """
        获取祖先节点

        Args:
            node_id: 节点 ID

        Returns:
            祖先节点 ID 列表
        """
        ancestors = []
        current_id = node_id

        while current_id:
            node = self.graph.nodes.get(current_id)
            if not node or not node.parent:
                break

            ancestors.append(node.parent)
            current_id = node.parent

        return ancestors

    def get_descendants(self, node_id: str) -> List[str]:
        """
        获取后代节点

        Args:
            node_id: 节点 ID

        Returns:
            后代节点 ID 列表
        """
        descendants = []
        node = self.graph.nodes.get(node_id)

        if not node:
            return descendants

        for child_id in node.children:
            descendants.append(child_id)
            descendants.extend(self.get_descendants(child_id))

        return descendants
