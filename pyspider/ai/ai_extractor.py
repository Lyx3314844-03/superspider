"""
PySpider AI 集成模块
提供 LLM 智能内容提取功能
"""

import json
import os
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional


class AIExtractor:
    """
    AI 提取器 - 集成 LLM 进行智能内容提取

    使用示例:
        extractor = AIExtractor(api_key="your-api-key")
        result = extractor.extract_structured(html_content, "提取商品信息", {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "price": {"type": "number"}
            }
        })
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-5.2",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("AI_API_KEY")
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    @classmethod
    def from_env(cls) -> "AIExtractor":
        """从环境变量创建提取器"""
        return cls()

    def extract_structured(
        self, content: str, instructions: str, schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        提取结构化数据

        Args:
            content: 页面内容
            instructions: 提取指令
            schema: JSON Schema 定义

        Returns:
            提取的数据
        """
        prompt = f"""请从以下内容中提取结构化数据。

提取要求：{instructions}

期望的输出格式（JSON Schema）：
{json.dumps(schema, ensure_ascii=False)}

页面内容：
{content}

请直接返回符合 JSON Schema 的 JSON 对象，不要包含其他解释。"""

        response = self._call_llm(prompt)
        return self._parse_json(response)

    def understand_page(self, content: str, question: str) -> str:
        """
        页面理解

        Args:
            content: 页面内容
            question: 问题

        Returns:
            回答
        """
        prompt = f"""请分析以下网页内容并回答问题。

问题：{question}

页面内容：
{content}

请详细回答。"""

        return self._call_llm(prompt)

    def generate_spider_config(self, description: str) -> Dict[str, Any]:
        """
        生成爬虫配置

        Args:
            description: 自然语言描述

        Returns:
            配置
        """
        prompt = f"""根据以下自然语言描述，生成爬虫配置（JSON 格式）。

描述：{description}

请返回以下格式的 JSON：
{{
    "start_urls": ["起始 URL"],
    "rules": [
        {{
            "name": "规则名称",
            "pattern": "URL 匹配模式",
            "extract": ["要提取的字段"],
            "follow_links": true/false
        }}
    ],
    "settings": {{
        "concurrency": 并发数，
        "max_depth": 最大深度，
        "delay": 请求延迟（毫秒）
    }}
}}

只返回 JSON，不要其他解释。"""

        response = self._call_llm(prompt)
        return self._parse_json(response)

    def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        if not self.api_key:
            raise ValueError("API key is required")

        request_body = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }
        ).encode("utf-8")

        url = f"{self.base_url}/chat/completions"
        req = urllib.request.Request(
            url,
            data=request_body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    return choices[0]["message"]["content"]
                return ""
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise Exception(f"API error: {e.code} - {error_body}")

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """解析 JSON 响应"""
        text = text.strip()

        # 尝试提取 JSON 部分
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"text": text}


class SpiderAssistant:
    """
    智能爬虫助手
    提供高级 AI 功能
    """

    def __init__(self, api_key: Optional[str] = None):
        self.extractor = AIExtractor(api_key=api_key)

    @classmethod
    def from_env(cls) -> "SpiderAssistant":
        """从环境变量创建助手"""
        return cls()

    def analyze_page(self, content: str) -> Dict[str, Any]:
        """
        分析页面

        Returns:
            {
                "page_type": str,
                "main_content": str,
                "links": List[Dict],
                "entities": List[Dict]
            }
        """
        prompt = f"""请分析以下网页内容，返回结构化信息。

页面内容：
{content}

请返回以下格式的 JSON：
{{
    "page_type": "页面类型（如：文章页、列表页、商品页等）",
    "main_content": "主要内容摘要",
    "links": [{{"url": "链接", "text": "链接文本", "link_type": "链接类型"}}],
    "entities": [{{"name": "实体名", "entity_type": "实体类型", "value": "值"}}]
}}"""

        response = self.extractor._call_llm(prompt)
        return self.extractor._parse_json(response)

    def should_crawl(self, content: str, criteria: str) -> bool:
        """
        判断是否需要爬取

        Args:
            content: 页面内容
            criteria: 爬取标准

        Returns:
            是否需要爬取
        """
        prompt = f"""请判断是否应该爬取以下页面。

爬取标准：{criteria}

页面内容：
{content}

请只返回 true 或 false。"""

        response = self.extractor._call_llm(prompt).strip().lower()
        return response == "true"

    def extract_fields(self, content: str, fields: List[str]) -> Dict[str, Any]:
        """
        提取指定字段

        Args:
            content: 页面内容
            fields: 字段列表

        Returns:
            提取的数据
        """
        prompt = f"""请从以下内容中提取指定字段。

需要提取的字段：{json.dumps(fields, ensure_ascii=False)}

页面内容：
{content}

请返回包含这些字段的 JSON 对象。"""

        response = self.extractor._call_llm(prompt)
        return self.extractor._parse_json(response)


# 使用示例
if __name__ == "__main__":
    # 从环境变量获取 API Key
    extractor = AIExtractor.from_env()

    # 示例：提取结构化数据
    html_content = """
    <html>
        <h1>iPhone 15 Pro</h1>
        <span class="price">¥7999</span>
        <p>Apple 最新旗舰手机</p>
    </html>
    """

    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "price": {"type": "number"},
            "description": {"type": "string"},
        },
    }

    result = extractor.extract_structured(html_content, "提取商品信息", schema)
    print("提取结果:", result)

    # 示例：页面理解
    answer = extractor.understand_page(html_content, "这个商品的价格是多少？")
    print("回答:", answer)

    # 示例：生成爬虫配置
    config = extractor.generate_spider_config("爬取知乎热门问题")
    print("爬虫配置:", config)
