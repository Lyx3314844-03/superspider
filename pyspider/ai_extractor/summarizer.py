"""
内容摘要器

自动生成网页内容的摘要

@author: Lan
@version: 2.0.0
@date: 2026-03-20
"""

from typing import List, Dict, Any
from bs4 import BeautifulSoup


class ContentSummarizer:
    """
    内容摘要器

    生成网页内容的简洁摘要
    """

    def __init__(self, max_sentences: int = 3):
        """
        初始化摘要器

        Args:
            max_sentences: 最大句子数
        """
        self.max_sentences = max_sentences

    def summarize(self, html: str) -> Dict[str, Any]:
        """
        生成摘要

        Args:
            html: HTML 内容

        Returns:
            摘要结果
        """
        soup = BeautifulSoup(html, "html.parser")

        # 提取标题
        title = self._extract_title(soup)

        # 提取描述
        description = self._extract_description(soup)

        # 如果已有 meta description，直接使用
        if description:
            return {
                "title": title,
                "summary": description,
                "method": "meta_description",
            }

        # 否则生成摘要
        text = self._extract_main_text(soup)
        summary = self._generate_summary(text)

        return {
            "title": title,
            "summary": summary,
            "method": "extractive",
        }

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取标题"""
        selectors = [
            "title",
            "h1",
            'meta[property="og:title"]',
            ".title",
            ".article-title",
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == "meta":
                    return element.get("content", "")
                return element.get_text(strip=True)

        return ""

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """提取描述"""
        selectors = [
            'meta[name="description"]',
            'meta[property="og:description"]',
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get("content"):
                return element.get("content", "")

        return ""

    def _extract_main_text(self, soup: BeautifulSoup) -> str:
        """提取主要文本"""
        selectors = [
            "article",
            ".content",
            ".main-content",
            ".article-content",
            ".post-content",
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(separator=" ", strip=True)

        return soup.get_text(separator=" ", strip=True)

    def _generate_summary(self, text: str) -> str:
        """
        生成摘要（提取式）

        使用简单的句子重要性评分
        """
        if not text:
            return ""

        # 分句
        sentences = self._split_sentences(text)

        if len(sentences) <= self.max_sentences:
            return " ".join(sentences)

        # 计算句子重要性
        word_freq = self._calculate_word_frequency(text)

        scored_sentences = []
        for i, sentence in enumerate(sentences):
            score = self._score_sentence(sentence, word_freq, i, len(sentences))
            scored_sentences.append((i, score, sentence))

        # 选择最重要的句子
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        top_sentences = scored_sentences[: self.max_sentences]

        # 按原文顺序排列
        top_sentences.sort(key=lambda x: x[0])

        summary = " ".join([s[2] for s in top_sentences])

        return summary

    def _split_sentences(self, text: str) -> List[str]:
        """分句"""
        import re

        # 简单的分句规则
        sentences = re.split(r"[。！？.!?]", text)

        # 清理空句子
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _calculate_word_frequency(self, text: str) -> dict:
        """计算词频"""
        import re
        from collections import Counter

        # 分词（简单按空格和标点）
        words = re.findall(r"\w+", text.lower())

        # 停用词（示例）
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "的",
            "了",
            "是",
            "在",
            "我",
            "有",
            "和",
            "就",
            "不",
            "人",
            "都",
            "一",
        }

        # 过滤停用词
        words = [w for w in words if w not in stop_words and len(w) > 1]

        return Counter(words)

    def _score_sentence(
        self, sentence: str, word_freq: dict, position: int, total: int
    ) -> float:
        """
        评分句子

        考虑因素：
        1. 词频
        2. 位置（开头和结尾的句子更重要）
        3. 句子长度
        """
        import re

        words = re.findall(r"\w+", sentence.lower())
        words = [w for w in words if len(w) > 1]

        if not words:
            return 0

        # 词频得分
        freq_score = sum(word_freq.get(w, 0) for w in words) / len(words)

        # 位置得分
        if position == 0:
            position_score = 1.5  # 第一句最重要
        elif position == total - 1:
            position_score = 1.2  # 最后一句次重要
        else:
            position_score = 1.0

        # 长度得分（避免太短或太长）
        length = len(words)
        if 10 <= length <= 30:
            length_score = 1.0
        else:
            length_score = 0.8

        return freq_score * position_score * length_score

    def summarize_with_keywords(self, html: str, keywords: List[str]) -> Dict[str, Any]:
        """
        基于关键词生成摘要

        Args:
            html: HTML 内容
            keywords: 关键词列表

        Returns:
            摘要结果
        """
        soup = BeautifulSoup(html, "html.parser")
        text = self._extract_main_text(soup)

        if not text:
            return {
                "title": self._extract_title(soup),
                "summary": "",
                "method": "keyword_based",
            }

        sentences = self._split_sentences(text)

        # 找出包含关键词的句子
        keyword_sentences = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(kw.lower() in sentence_lower for kw in keywords):
                keyword_sentences.append(sentence)

        # 限制数量
        keyword_sentences = keyword_sentences[: self.max_sentences]

        return {
            "title": self._extract_title(soup),
            "summary": " ".join(keyword_sentences),
            "method": "keyword_based",
            "keywords": keywords,
        }


# 便捷函数
def summarize(html: str, max_sentences: int = 3) -> Dict[str, Any]:
    """
    生成摘要的便捷函数

    Args:
        html: HTML 内容
        max_sentences: 最大句子数

    Returns:
        摘要结果
    """
    summarizer = ContentSummarizer(max_sentences)
    return summarizer.summarize(html)
