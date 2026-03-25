"""
HTML 和 JSON 解析器
"""

from bs4 import BeautifulSoup
from typing import List, Optional, Any
import json


class HTMLParser:
    """HTML 解析器"""
    
    def __init__(self, html: str):
        self.soup = BeautifulSoup(html, 'lxml')
        self.html = html
    
    def css(self, selector: str) -> List[str]:
        """CSS 选择器提取"""
        return [elem.get_text(strip=True) for elem in self.soup.select(selector)]
    
    def css_first(self, selector: str) -> Optional[str]:
        """获取第一个匹配"""
        elem = self.soup.select_one(selector)
        return elem.get_text(strip=True) if elem else None
    
    def css_attr(self, selector: str, attr: str) -> List[str]:
        """获取属性"""
        return [elem.get(attr, '') for elem in self.soup.select(selector)]
    
    def css_attr_first(self, selector: str, attr: str) -> Optional[str]:
        """获取第一个属性"""
        elem = self.soup.select_one(selector)
        return elem.get(attr) if elem else None
    
    def links(self) -> List[str]:
        """获取所有链接"""
        return self.css_attr('a', 'href')
    
    def images(self) -> List[str]:
        """获取所有图片"""
        return self.css_attr('img', 'src')
    
    def title(self) -> Optional[str]:
        """获取标题"""
        title_tag = self.soup.find('title')
        return title_tag.get_text(strip=True) if title_tag else None
    
    def text(self) -> str:
        """获取文本"""
        return self.soup.get_text(strip=True)
    
    def html(self) -> str:
        """获取 HTML"""
        return self.html


class JSONParser:
    """JSON 解析器"""
    
    def __init__(self, json_str: str):
        self.data = json.loads(json_str)
    
    def get(self, path: str) -> Any:
        """获取 JSON 路径"""
        keys = path.split('.')
        result = self.data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
            elif isinstance(result, list) and key.isdigit():
                result = result[int(key)]
            else:
                return None
        return result
    
    def get_string(self, path: str) -> Optional[str]:
        """获取字符串"""
        val = self.get(path)
        return str(val) if val is not None else None
    
    def get_int(self, path: str) -> Optional[int]:
        """获取整数"""
        val = self.get(path)
        return int(val) if val is not None else None
    
    def get_float(self, path: str) -> Optional[float]:
        """获取浮点数"""
        val = self.get(path)
        return float(val) if val is not None else None
    
    def get_bool(self, path: str) -> Optional[bool]:
        """获取布尔值"""
        val = self.get(path)
        return bool(val) if val is not None else None
    
    def get_list(self, path: str) -> Optional[List]:
        """获取列表"""
        val = self.get(path)
        return val if isinstance(val, list) else None
