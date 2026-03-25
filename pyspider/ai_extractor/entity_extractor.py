"""
实体提取器

从网页内容中提取命名实体（人名、地名、组织、时间等）

@author: Lan
@version: 2.0.0
@date: 2026-03-20
"""

import re
from typing import Dict, List, Any
from bs4 import BeautifulSoup


class EntityExtractor:
    """
    实体提取器
    
    提取网页中的命名实体
    """
    
    # 实体模式
    ENTITY_PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]*',
        'url': r'https?://[^\s<>"{}|\\^`\[\]]+',
        'date': r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b',
        'time': r'\b\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM)?\b',
        'money': r'[\$€£￥¥]\s*\d+[,\.]?\d*',
        'percentage': r'\d+\.?\d*\s*%',
    }
    
    def __init__(self):
        """初始化实体提取器"""
        self.soup = None
        self.text = ""
    
    def extract(self, html: str) -> Dict[str, List[str]]:
        """
        提取所有实体
        
        Args:
            html: HTML 内容
            
        Returns:
            实体字典
        """
        self.soup = BeautifulSoup(html, 'html.parser')
        self.text = self.soup.get_text()
        
        result = {}
        
        # 提取正则实体
        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            matches = re.findall(pattern, self.text, re.IGNORECASE)
            if matches:
                result[entity_type] = list(set(matches))
        
        # 提取结构化实体
        result['persons'] = self._extract_persons()
        result['organizations'] = self._extract_organizations()
        result['locations'] = self._extract_locations()
        result['products'] = self._extract_products()
        
        # 清理空列表
        result = {k: v for k, v in result.items() if v}
        
        return result
    
    def _extract_persons(self) -> List[str]:
        """提取人名"""
        persons = []
        
        # 尝试从 meta 提取
        author = self.soup.select_one('meta[name="author"]')
        if author and author.get('content'):
            persons.append(author.get('content'))
        
        # 尝试从常见选择器提取
        selectors = ['.author', '.byline', '[itemprop="author"]']
        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text and len(text) < 100:  # 避免提取到长文本
                    persons.append(text)
        
        return list(set(persons))
    
    def _extract_organizations(self) -> List[str]:
        """提取组织名"""
        orgs = []
        
        # 从 meta 提取
        org = self.soup.select_one('meta[name="application-name"]')
        if org and org.get('content'):
            orgs.append(org.get('content'))
        
        # 从版权信息提取
        copyright_info = self.soup.select_one('meta[name="copyright"]')
        if copyright_info and copyright_info.get('content'):
            orgs.append(copyright_info.get('content'))
        
        return list(set(orgs))
    
    def _extract_locations(self) -> List[str]:
        """提取地点"""
        locations = []
        
        # 从结构化数据提取
        location = self.soup.select_one('[itemprop="location"], .location, .address')
        if location:
            text = location.get_text(strip=True)
            if text:
                locations.append(text)
        
        return list(set(locations))
    
    def _extract_products(self) -> List[str]:
        """提取产品名"""
        products = []
        
        # 从常见选择器提取
        selectors = [
            '.product-name', '.product-title', '[itemprop="name"]',
            'meta[property="product:name"]', 'h1.product-title',
        ]
        
        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    products.append(element.get('content'))
                else:
                    text = element.get_text(strip=True)
                    if text and len(text) < 200:
                        products.append(text)
        
        return list(set(products))
    
    def extract_emails(self) -> List[str]:
        """提取邮箱"""
        return re.findall(self.ENTITY_PATTERNS['email'], self.text)
    
    def extract_phones(self) -> List[str]:
        """提取电话"""
        return re.findall(self.ENTITY_PATTERNS['phone'], self.text)
    
    def extract_urls(self) -> List[str]:
        """提取 URL"""
        return re.findall(self.ENTITY_PATTERNS['url'], self.text)
    
    def extract_dates(self) -> List[str]:
        """提取日期"""
        return re.findall(self.ENTITY_PATTERNS['date'], self.text)
    
    def extract_times(self) -> List[str]:
        """提取时间"""
        return re.findall(self.ENTITY_PATTERNS['time'], self.text)
    
    def extract_money(self) -> List[str]:
        """提取金额"""
        return re.findall(self.ENTITY_PATTERNS['money'], self.text)
    
    def extract_percentages(self) -> List[str]:
        """提取百分比"""
        return re.findall(self.ENTITY_PATTERNS['percentage'], self.text)


# 便捷函数
def extract_entities(html: str) -> Dict[str, List[str]]:
    """
    提取实体的便捷函数
    
    Args:
        html: HTML 内容
        
    Returns:
        实体字典
    """
    extractor = EntityExtractor()
    return extractor.extract(html)
