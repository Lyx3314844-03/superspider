"""
LLM 内容提取器

使用大语言模型进行智能内容提取
支持 OpenAI GPT、Claude、Gemini 等模型

@author: Lan
@version: 2.0.0
@date: 2026-03-20
"""

import json
import requests
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """LLM 客户端基类"""
    
    @abstractmethod
    def chat(self, messages: List[Dict], **kwargs) -> str:
        """发送聊天请求"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT 客户端"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.openai.com/v1/chat/completions"
    
    def chat(self, messages: List[Dict], **kwargs) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            **kwargs
        }
        
        response = requests.post(self.api_url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]


class LLMExtractor:
    """
    LLM 内容提取器
    
    使用大语言模型从网页内容中提取结构化数据
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        """
        初始化 LLM 提取器
        
        Args:
            api_key: LLM API Key
            model: 模型名称
        """
        self.api_key = api_key
        self.model = model
        self.client = OpenAIClient(api_key, model) if api_key else None
    
    def extract(self, html: str, prompt: str) -> str:
        """
        从 HTML 中提取内容
        
        Args:
            html: HTML 内容
            prompt: 提取提示
            
        Returns:
            提取结果
        """
        if not self.client:
            raise ValueError("API key not set")
        
        messages = [
            {"role": "system", "content": "You are a helpful web content extractor."},
            {"role": "user", "content": f"{prompt}\n\nHTML Content:\n{html}"}
        ]
        
        return self.client.chat(messages)
    
    def extract_structured(self, html: str, schema: Dict[str, Any]) -> Dict:
        """
        提取结构化数据
        
        Args:
            html: HTML 内容
            schema: 数据结构定义
            
        Returns:
            结构化数据
        """
        prompt = f"""Extract the following information from the HTML:
{json.dumps(schema, indent=2, ensure_ascii=False)}

Return the result as JSON."""
        
        result = self.extract(html, prompt)
        
        # 尝试解析 JSON
        try:
            # 清理可能的 markdown 标记
            if result.startswith("```json"):
                result = result[7:]
            if result.endswith("```"):
                result = result[:-3]
            return json.loads(result.strip())
        except:
            return {"raw": result}
    
    def extract_with_examples(self, html: str, schema: Dict, examples: List[Dict]) -> Dict:
        """
        使用示例进行提取（Few-shot Learning）
        
        Args:
            html: HTML 内容
            schema: 数据结构定义
            examples: 示例数据
            
        Returns:
            提取结果
        """
        examples_text = "\n\n".join([
            f"Example {i+1}:\n{json.dumps(ex, indent=2, ensure_ascii=False)}"
            for i, ex in enumerate(examples)
        ])
        
        prompt = f"""Extract information from HTML following these examples:
{examples_text}

Schema:
{json.dumps(schema, indent=2, ensure_ascii=False)}

Return the result as JSON."""
        
        result = self.extract(html, prompt)
        
        try:
            if result.startswith("```json"):
                result = result[7:]
            if result.endswith("```"):
                result = result[:-3]
            return json.loads(result.strip())
        except:
            return {"raw": result}
    
    def set_model(self, model: str):
        """切换模型"""
        self.model = model
        if self.api_key:
            self.client = OpenAIClient(self.api_key, model)
    
    def set_api_key(self, api_key: str):
        """设置 API Key"""
        self.api_key = api_key
        self.client = OpenAIClient(api_key, self.model)


# 便捷函数
def extract_with_llm(html: str, prompt: str, api_key: str, model: str = "gpt-4") -> str:
    """
    使用 LLM 提取内容的便捷函数
    
    Args:
        html: HTML 内容
        prompt: 提取提示
        api_key: API Key
        model: 模型名称
        
    Returns:
        提取结果
    """
    extractor = LLMExtractor(api_key, model)
    return extractor.extract(html, prompt)


def extract_json_with_llm(html: str, schema: Dict, api_key: str, model: str = "gpt-4") -> Dict:
    """
    使用 LLM 提取 JSON 数据的便捷函数
    
    Args:
        html: HTML 内容
        schema: 数据结构定义
        api_key: API Key
        model: 模型名称
        
    Returns:
        JSON 数据
    """
    extractor = LLMExtractor(api_key, model)
    return extractor.extract_structured(html, schema)
