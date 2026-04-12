"""
PySpider 图结构爬虫模块

吸收 scrapegraphai 的图结构爬虫功能
支持基于图的页面遍历和关系提取

@author: Lan
@version: 2.0.0
@date: 2026-03-20
"""

from .graph_builder import GraphBuilder
from .node_traversal import NodeTraversal
from .relation_extractor import RelationExtractor

__all__ = [
    "GraphBuilder",
    "NodeTraversal",
    "RelationExtractor",
]
