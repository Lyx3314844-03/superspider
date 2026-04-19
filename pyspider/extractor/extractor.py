"""
AI 内容提取模块
支持 OpenAI/Claude 等 AI API
"""

import json
import requests
from typing import Dict, List, Optional, Any


class AIExtractor:
    """AI 内容提取器"""

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://api.openai.com/v1/chat/completions",
        model: str = "gpt-5.2",
        timeout: int = 30,
    ):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
        )

    def extract(
        self,
        content: str,
        schema: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """提取结构化数据"""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": f"Extract structured data from the following content according to this schema:\n{json.dumps(schema)}\n\nContent:\n{content}",
                },
            ],
        }

        try:
            resp = self.session.post(self.api_url, json=payload, timeout=self.timeout)
            resp.raise_for_status()

            result = resp.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            print(f"AI extract error: {e}")

        return None

    def summarize(self, content: str, max_length: int = 200) -> Optional[str]:
        """总结内容"""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": f"Summarize the following content in {max_length} characters:\n{content}",
                },
            ],
            "max_tokens": 100,
        }

        try:
            resp = self.session.post(self.api_url, json=payload, timeout=self.timeout)
            resp.raise_for_status()

            result = resp.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"AI summarize error: {e}")

        return None

    def extract_keywords(self, content: str, max_keywords: int = 10) -> List[str]:
        """提取关键词"""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": f"Extract top {max_keywords} keywords from the following content as a JSON array:\n{content}",
                },
            ],
        }

        try:
            resp = self.session.post(self.api_url, json=payload, timeout=self.timeout)
            resp.raise_for_status()

            result = resp.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            print(f"AI keyword extraction error: {e}")

        return []

    def classify(
        self,
        content: str,
        categories: List[str],
    ) -> Optional[str]:
        """分类内容"""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": f"Classify the following content into one of these categories: {', '.join(categories)}\n\nContent:\n{content}\n\nCategory:",
                },
            ],
            "max_tokens": 10,
        }

        try:
            resp = self.session.post(self.api_url, json=payload, timeout=self.timeout)
            resp.raise_for_status()

            result = resp.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"AI classification error: {e}")

        return None

    def analyze_sentiment(self, content: str) -> Optional[Dict[str, Any]]:
        """情感分析"""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": f"Analyze the sentiment of the following text. Return JSON with 'sentiment' (positive/negative/neutral) and 'confidence' (0-1):\n{content}",
                },
            ],
        }

        try:
            resp = self.session.post(self.api_url, json=payload, timeout=self.timeout)
            resp.raise_for_status()

            result = resp.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            print(f"AI sentiment analysis error: {e}")

        return None

    def translate(self, content: str, target_language: str) -> Optional[str]:
        """翻译"""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": f"Translate the following text to {target_language}:\n{content}",
                },
            ],
        }

        try:
            resp = self.session.post(self.api_url, json=payload, timeout=self.timeout)
            resp.raise_for_status()

            result = resp.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"AI translation error: {e}")

        return None

    def answer_question(self, context: str, question: str) -> Optional[str]:
        """问答"""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": f"Answer the following question based on the provided context:\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:",
                },
            ],
        }

        try:
            resp = self.session.post(self.api_url, json=payload, timeout=self.timeout)
            resp.raise_for_status()

            result = resp.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"AI Q&A error: {e}")

        return None
