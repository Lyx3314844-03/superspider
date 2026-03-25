"""
Scrapy 风格爬虫模块
支持 Spider、CrawlSpider、Item、Loader 等
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from pyspider.core.models import Request, Response, Page
from pyspider.parser.parser import HTMLParser, JSONParser
import re


class Spider(ABC):
    """基础爬虫类（Scrapy 风格）"""
    
    name: str = "spider"
    start_urls: List[str] = []
    allowed_domains: List[str] = []
    custom_settings: Dict[str, Any] = {}
    
    def __init__(self):
        self.crawler = None
        self.settings = self.custom_settings.copy()
    
    def start_requests(self) -> List[Request]:
        """生成起始请求"""
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse)
    
    @abstractmethod
    def parse(self, page: Page) -> Any:
        """解析方法（必须实现）"""
        pass
    
    def parse_item(self, page: Page) -> Optional[Dict[str, Any]]:
        """物品解析方法"""
        return None
    
    def log(self, message: str, level: str = "INFO") -> None:
        """日志记录"""
        print(f"[{self.name}] {level}: {message}")


class CrawlSpider(Spider):
    """自动爬取爬虫（类似 Scrapy CrawlSpider）"""
    
    rules: List['Rule'] = []
    
    def __init__(self):
        super().__init__()
        self._compiled_rules = []
        self._compile_rules()
    
    def _compile_rules(self) -> None:
        """编译规则"""
        for rule in self.rules:
            self._compiled_rules.append(rule)
    
    def _requests_to_follow(self, page: Page) -> List[Request]:
        """生成跟进请求"""
        requests = []
        for rule in self._compiled_rules:
            links = rule.link_extractor.extract_links(page)
            for link in links:
                req = Request(url=link, callback=self._response_downloaded())
                requests.append(req)
        return requests
    
    def _response_downloaded(self) -> Callable:
        """响应下载回调"""
        def callback(page: Page):
            return self.parse(page)
        return callback


@dataclass
class Rule:
    """爬取规则"""
    link_extractor: 'LinkExtractor'
    callback: Optional[Callable] = None
    follow: bool = True
    process_links: Optional[Callable] = None
    process_request: Optional[Callable] = None


class LinkExtractor:
    """链接提取器"""
    
    def __init__(
        self,
        allow: List[str] = None,
        deny: List[str] = None,
        allow_domains: List[str] = None,
        deny_domains: List[str] = None,
        restrict_xpaths: List[str] = None,
        tags: List[str] = None,
        attrs: List[str] = None,
        process_value: Optional[Callable] = None,
    ):
        self.allow = allow or []
        self.deny = deny or []
        self.allow_domains = allow_domains or []
        self.deny_domains = deny_domains or []
        self.restrict_xpaths = restrict_xpaths or []
        self.tags = tags or ['a']
        self.attrs = attrs or ['href']
        self.process_value = process_value
    
    def extract_links(self, page: Page) -> List[str]:
        """提取链接"""
        parser = HTMLParser(page.response.text)
        links = []
        
        for tag in self.tags:
            for attr in self.attrs:
                selector = f"{tag}[{attr}]"
                extracted = parser.css_attr(selector, attr)
                
                for link in extracted:
                    if self._should_follow(link, page):
                        links.append(link)
        
        return links
    
    def _should_follow(self, link: str, page: Page) -> bool:
        """检查是否应该跟进"""
        # 检查 allow
        if self.allow and not any(re.search(pattern, link) for pattern in self.allow):
            return False
        
        # 检查 deny
        if self.deny and any(re.search(pattern, link) for pattern in self.deny):
            return False
        
        return True


class Item:
    """数据项（Scrapy 风格）"""
    
    def __init__(self, *args, **kwargs):
        self._values = {}
        for key, value in kwargs.items():
            self[key] = value
    
    def __setitem__(self, key: str, value: Any) -> None:
        self._values[key] = value
    
    def __getitem__(self, key: str) -> Any:
        return self._values.get(key)
    
    def __delitem__(self, key: str) -> None:
        if key in self._values:
            del self._values[key]
    
    def __contains__(self, key: str) -> bool:
        return key in self._values
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取值"""
        return self._values.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置值"""
        self._values[key] = value
    
    def keys(self) -> List[str]:
        """获取所有键"""
        return list(self._values.keys())
    
    def values(self) -> List[Any]:
        """获取所有值"""
        return list(self._values.values())
    
    def items(self) -> List[tuple]:
        """获取所有键值对"""
        return list(self._values.items())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return dict(self._values)
    
    def copy(self) -> 'Item':
        """复制"""
        return Item(**self._values.copy())


class Loader:
    """数据加载器（Scrapy 风格）"""
    
    def __init__(self, item: Item = None):
        self.item = item or Item()
        self._loaders = {}
    
    def add_css(self, field_name: str, css_selector: str, page: Page) -> 'Loader':
        """使用 CSS 选择器添加字段"""
        parser = HTMLParser(page.response.text)
        value = parser.css_first(css_selector)
        self.item.set(field_name, value)
        return self
    
    def add_xpath(self, field_name: str, xpath_selector: str, page: Page) -> 'Loader':
        """使用 XPath 添加字段"""
        parser = HTMLParser(page.response.text)
        value = parser.xpath_first(xpath_selector)
        self.item.set(field_name, value)
        return self
    
    def add_json(self, field_name: str, json_path: str, page: Page) -> 'Loader':
        """使用 JSON 路径添加字段"""
        parser = JSONParser(page.response.text)
        value = parser.get(json_path)
        self.item.set(field_name, value)
        return self
    
    def add_value(self, field_name: str, value: Any) -> 'Loader':
        """直接添加值"""
        self.item.set(field_name, value)
        return self
    
    def load_item(self) -> Item:
        """加载 Item"""
        return self.item


class ItemPipeline(ABC):
    """物品管道（Scrapy 风格）"""
    
    def open_spider(self, spider: Spider) -> None:
        """爬虫打开时调用"""
        pass
    
    def close_spider(self, spider: Spider) -> None:
        """爬虫关闭时调用"""
        pass
    
    @abstractmethod
    def process_item(self, item: Item, spider: Spider) -> Any:
        """处理物品（必须实现）"""
        pass


class SpiderMiddleware(ABC):
    """爬虫中间件（Scrapy 风格）"""
    
    def process_spider_input(self, request: Request, spider: Spider) -> None:
        """处理蜘蛛输入"""
        pass
    
    def process_spider_output(self, response: Response, result: List, spider: Spider) -> List:
        """处理蜘蛛输出"""
        return result
    
    def process_spider_exception(self, response: Response, exception: Exception, spider: Spider) -> None:
        """处理蜘蛛异常"""
        pass


class DownloaderMiddleware(ABC):
    """下载器中间件（Scrapy 风格）"""
    
    def process_request(self, request: Request, spider: Spider) -> None:
        """处理请求"""
        pass
    
    def process_response(self, request: Request, response: Response, spider: Spider) -> Response:
        """处理响应"""
        return response
    
    def process_exception(self, request: Request, exception: Exception, spider: Spider) -> None:
        """处理异常"""
        pass
