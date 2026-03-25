"""
PySpider AI 增强模块

吸收 crawl4ai、scrapegraphai 的 AI 提取功能
支持 LLM 驱动的内容提取、实体识别、情感分析等

@author: Lan
@version: 2.0.0
@date: 2026-03-20
"""

from .llm_extractor import LLMExtractor
from .smart_parser import SmartParser
from .entity_extractor import EntityExtractor
from .sentiment_analyzer import SentimentAnalyzer
from .summarizer import ContentSummarizer

__all__ = [
    'LLMExtractor',
    'SmartParser',
    'EntityExtractor',
    'SentimentAnalyzer',
    'ContentSummarizer',
]
