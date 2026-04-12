"""
关系提取器

从图结构中提取各种关系（父子、兄弟、链接、包含等）

@author: Lan
@version: 2.0.0
@date: 2026-03-20
"""

from typing import Dict, List, Any
from collections import defaultdict
from .graph_builder import GraphBuilder


class RelationExtractor:
    """关系提取器"""

    def __init__(self, graph: GraphBuilder):
        """
        初始化关系提取器

        Args:
            graph: 图构建器实例
        """
        self.graph = graph

    def extract_parent_child_relations(self) -> List[Dict[str, Any]]:
        """
        提取父子关系

        Returns:
            关系列表
        """
        relations = []

        for node_id, node in self.graph.nodes.items():
            if node.parent:
                parent_node = self.graph.nodes.get(node.parent)
                if parent_node:
                    relations.append(
                        {
                            "relation": "parent_child",
                            "parent": {
                                "id": node.parent,
                                "tag": parent_node.tag,
                                "type": parent_node.type,
                                "text": (
                                    parent_node.text[:100] if parent_node.text else ""
                                ),
                            },
                            "child": {
                                "id": node_id,
                                "tag": node.tag,
                                "type": node.type,
                                "text": node.text[:100] if node.text else "",
                            },
                        }
                    )

        return relations

    def extract_sibling_relations(self) -> List[Dict[str, Any]]:
        """
        提取兄弟关系

        Returns:
            关系列表
        """
        relations = []

        # 按父节点分组
        children_by_parent = defaultdict(list)

        for node_id, node in self.graph.nodes.items():
            if node.parent:
                children_by_parent[node.parent].append(node)

        # 提取兄弟关系
        for parent_id, children in children_by_parent.items():
            if len(children) < 2:
                continue

            for i in range(len(children) - 1):
                relations.append(
                    {
                        "relation": "sibling",
                        "nodes": [
                            {
                                "id": children[i].id,
                                "tag": children[i].tag,
                                "type": children[i].type,
                                "text": (
                                    children[i].text[:50] if children[i].text else ""
                                ),
                            },
                            {
                                "id": children[i + 1].id,
                                "tag": children[i + 1].tag,
                                "type": children[i + 1].type,
                                "text": (
                                    children[i + 1].text[:50]
                                    if children[i + 1].text
                                    else ""
                                ),
                            },
                        ],
                        "parent_id": parent_id,
                    }
                )

        return relations

    def extract_link_relations(self) -> List[Dict[str, Any]]:
        """
        提取链接关系

        Returns:
            关系列表
        """
        relations = []

        for edge in self.graph.get_links():
            source_node = self.graph.nodes.get(edge.source)
            if source_node:
                relations.append(
                    {
                        "relation": "link",
                        "source": {
                            "id": edge.source,
                            "tag": source_node.tag,
                            "text": source_node.text[:100] if source_node.text else "",
                        },
                        "target": {
                            "url": edge.target,
                        },
                        "weight": edge.weight,
                    }
                )

        return relations

    def extract_image_relations(self) -> List[Dict[str, Any]]:
        """
        提取图片关系

        Returns:
            关系列表
        """
        relations = []

        for edge in self.graph.get_images():
            source_node = self.graph.nodes.get(edge.source)
            if source_node:
                relations.append(
                    {
                        "relation": "image",
                        "source": {
                            "id": edge.source,
                            "tag": source_node.tag,
                            "text": source_node.text[:50] if source_node.text else "",
                        },
                        "target": {
                            "src": edge.target,
                            "alt": source_node.attributes.get("alt", ""),
                        },
                        "weight": edge.weight,
                    }
                )

        return relations

    def extract_containment_relations(self) -> List[Dict[str, Any]]:
        """
        提取包含关系

        Returns:
            关系列表
        """
        relations = []

        for node_id, node in self.graph.nodes.items():
            if node.children:
                contained_nodes = []
                for child_id in node.children[:10]:  # 限制数量
                    child_node = self.graph.nodes.get(child_id)
                    if child_node:
                        contained_nodes.append(
                            {
                                "id": child_id,
                                "tag": child_node.tag,
                                "type": child_node.type,
                            }
                        )

                if contained_nodes:
                    relations.append(
                        {
                            "relation": "contains",
                            "container": {
                                "id": node_id,
                                "tag": node.tag,
                                "type": node.type,
                                "children_count": len(node.children),
                            },
                            "contained": contained_nodes,
                        }
                    )

        return relations

    def extract_all_relations(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        提取所有关系

        Returns:
            关系字典
        """
        return {
            "parent_child": self.extract_parent_child_relations(),
            "sibling": self.extract_sibling_relations(),
            "link": self.extract_link_relations(),
            "image": self.extract_image_relations(),
            "contains": self.extract_containment_relations(),
        }

    def get_relation_stats(self) -> Dict[str, int]:
        """
        获取关系统计

        Returns:
            统计字典
        """
        all_relations = self.extract_all_relations()
        return {
            relation_type: len(relations)
            for relation_type, relations in all_relations.items()
        }

    def visualize_relations(self) -> str:
        """
        可视化关系

        Returns:
            文本可视化
        """
        lines = []
        lines.append("=" * 60)
        lines.append("RELATION GRAPH VISUALIZATION")
        lines.append("=" * 60)

        stats = self.get_relation_stats()
        lines.append(f"\nTotal Relations: {sum(stats.values())}")
        lines.append("\nBy Type:")
        for relation_type, count in stats.items():
            lines.append(f"  - {relation_type}: {count}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
