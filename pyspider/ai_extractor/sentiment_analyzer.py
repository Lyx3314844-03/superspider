"""
情感分析器

分析网页内容的情感倾向（正面、负面、中性）

@author: Lan
@version: 2.0.0
@date: 2026-03-20
"""

from typing import Dict, Any
from bs4 import BeautifulSoup


class SentimentAnalyzer:
    """
    情感分析器

    分析文本内容的情感倾向
    """

    # 简单的情感词库（示例）
    POSITIVE_WORDS = {
        "好",
        "优秀",
        "出色",
        "完美",
        "棒",
        "赞",
        "喜欢",
        "爱",
        "推荐",
        "值得",
        "满意",
        "好评",
        "优质",
        "精彩",
        "成功",
        "good",
        "great",
        "excellent",
        "amazing",
        "wonderful",
        "love",
        "like",
        "best",
        "perfect",
        "awesome",
    }

    NEGATIVE_WORDS = {
        "差",
        "糟糕",
        "烂",
        "坏",
        "失望",
        "不满",
        "讨厌",
        "恨",
        "差评",
        "垃圾",
        "失败",
        "错误",
        "问题",
        "bug",
        "故障",
        "bad",
        "terrible",
        "awful",
        "horrible",
        "worst",
        "hate",
        "dislike",
        "disappointed",
        "poor",
    }

    def __init__(self):
        """初始化情感分析器"""
        self.text = ""

    def analyze(self, html: str) -> Dict[str, Any]:
        """
        分析情感

        Args:
            html: HTML 内容

        Returns:
            分析结果
        """
        soup = BeautifulSoup(html, "html.parser")
        self.text = soup.get_text().lower()

        # 统计情感词
        positive_count = sum(1 for word in self.POSITIVE_WORDS if word in self.text)
        negative_count = sum(1 for word in self.NEGATIVE_WORDS if word in self.text)

        # 计算情感得分
        total = positive_count + negative_count
        if total == 0:
            sentiment = "neutral"
            score = 0.5
        else:
            score = positive_count / total
            if score > 0.6:
                sentiment = "positive"
            elif score < 0.4:
                sentiment = "negative"
            else:
                sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "score": round(score, 2),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "positive_words": self._find_words(self.POSITIVE_WORDS),
            "negative_words": self._find_words(self.NEGATIVE_WORDS),
        }

    def _find_words(self, word_set) -> list:
        """查找文本中出现的情感词"""
        found = []
        text_lower = self.text.lower()
        for word in word_set:
            if word.lower() in text_lower:
                found.append(word)
        return list(set(found))

    def is_positive(self) -> bool:
        """是否正面"""
        result = self.analyze_from_text(self.text)
        return result["sentiment"] == "positive"

    def is_negative(self) -> bool:
        """是否负面"""
        result = self.analyze_from_text(self.text)
        return result["sentiment"] == "negative"

    def is_neutral(self) -> bool:
        """是否中性"""
        result = self.analyze_from_text(self.text)
        return result["sentiment"] == "neutral"

    def analyze_from_text(self, text: str) -> Dict[str, Any]:
        """
        从文本分析情感

        Args:
            text: 文本内容

        Returns:
            分析结果
        """
        text_lower = text.lower()

        positive_count = sum(1 for word in self.POSITIVE_WORDS if word in text_lower)
        negative_count = sum(1 for word in self.NEGATIVE_WORDS if word in text_lower)

        total = positive_count + negative_count
        if total == 0:
            sentiment = "neutral"
            score = 0.5
        else:
            score = positive_count / total
            if score > 0.6:
                sentiment = "positive"
            elif score < 0.4:
                sentiment = "negative"
            else:
                sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "score": round(score, 2),
            "positive_count": positive_count,
            "negative_count": negative_count,
        }


# 便捷函数
def analyze_sentiment(html: str) -> Dict[str, Any]:
    """
    分析情感的便捷函数

    Args:
        html: HTML 内容

    Returns:
        分析结果
    """
    analyzer = SentimentAnalyzer()
    return analyzer.analyze(html)
