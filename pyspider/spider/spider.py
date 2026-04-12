"""
Scrapy 风格爬虫模块
支持 Spider、CrawlSpider、Item、Loader、FeedExporter、CrawlerProcess 等。
"""

from __future__ import annotations

import csv
import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse

from pyspider.core.models import Page, Request, Response
from pyspider.downloader.downloader import HTTPDownloader
from pyspider.parser.parser import HTMLParser, JSONParser


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

    rules: List["Rule"] = []

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

    link_extractor: "LinkExtractor"
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
        self.tags = tags or ["a"]
        self.attrs = attrs or ["href"]
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

    def copy(self) -> "Item":
        """复制"""
        return Item(**self._values.copy())


class Loader:
    """数据加载器（Scrapy 风格）"""

    def __init__(self, item: Item = None):
        self.item = item or Item()
        self._loaders = {}

    def add_css(self, field_name: str, css_selector: str, page: Page) -> "Loader":
        """使用 CSS 选择器添加字段"""
        parser = HTMLParser(page.response.text)
        value = parser.css_first(css_selector)
        self.item.set(field_name, value)
        return self

    def add_xpath(self, field_name: str, xpath_selector: str, page: Page) -> "Loader":
        """使用 XPath 添加字段"""
        parser = HTMLParser(page.response.text)
        value = parser.xpath_first(xpath_selector)
        self.item.set(field_name, value)
        return self

    def add_json(self, field_name: str, json_path: str, page: Page) -> "Loader":
        """使用 JSON 路径添加字段"""
        parser = JSONParser(page.response.text)
        value = parser.get(json_path)
        self.item.set(field_name, value)
        return self

    def add_value(self, field_name: str, value: Any) -> "Loader":
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

    def process_spider_output(
        self, response: Response, result: List, spider: Spider
    ) -> List:
        """处理蜘蛛输出"""
        return result

    def process_spider_exception(
        self, response: Response, exception: Exception, spider: Spider
    ) -> None:
        """处理蜘蛛异常"""
        pass


class DownloaderMiddleware(ABC):
    """下载器中间件（Scrapy 风格）"""

    def process_request(self, request: Request, spider: Spider) -> None:
        """处理请求"""
        pass

    def process_response(
        self, request: Request, response: Response, spider: Spider
    ) -> Response:
        """处理响应"""
        return response

    def process_exception(
        self, request: Request, exception: Exception, spider: Spider
    ) -> None:
        """处理异常"""
        pass


class ScrapyPlugin(ABC):
    """项目级扩展入口。"""

    name: str = "plugin"

    def configure(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        """允许插件在 spider 实例化前修改项目配置。"""
        return config

    def provide_pipelines(self) -> Iterable[ItemPipeline]:
        return []

    def provide_spider_middlewares(self) -> Iterable[SpiderMiddleware]:
        return []

    def provide_downloader_middlewares(self) -> Iterable[DownloaderMiddleware]:
        return []

    def on_spider_opened(self, spider: Spider) -> None:
        pass

    def on_spider_closed(self, spider: Spider) -> None:
        pass

    def process_item(self, item: Item, spider: Spider) -> Any:
        return item


class FeedExporter:
    """轻量 Feed 导出器，接口风格与 Scrapy 接近。"""

    def __init__(self, fmt: str, output_path: str, append: bool = False):
        self.format = fmt.lower()
        self.output_path = Path(output_path)
        self.append = append
        self.items: List[Dict[str, Any]] = []

    @classmethod
    def json(cls, output_path: str) -> "FeedExporter":
        return cls("json", output_path)

    @classmethod
    def csv(cls, output_path: str) -> "FeedExporter":
        return cls("csv", output_path)

    @classmethod
    def jsonlines(cls, output_path: str) -> "FeedExporter":
        return cls("jsonlines", output_path)

    def export_item(self, item: Any) -> None:
        self.items.append(_item_to_dict(item))

    def export_items(self, items: Iterable[Any]) -> None:
        for item in items:
            self.export_item(item)

    def close(self) -> Path:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        if self.format == "json":
            payload = []
            if self.append and self.output_path.exists():
                try:
                    payload = json.loads(self.output_path.read_text(encoding="utf-8"))
                except Exception:
                    payload = []
            payload.extend(self.items)
            self.output_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return self.output_path

        if self.format == "jsonlines":
            lines: List[str] = []
            if self.append and self.output_path.exists():
                existing = self.output_path.read_text(encoding="utf-8").strip()
                if existing:
                    lines.append(existing)
            lines.extend(json.dumps(item, ensure_ascii=False) for item in self.items)
            self.output_path.write_text(
                "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8"
            )
            return self.output_path

        if self.format == "csv":
            fieldnames: List[str] = []
            for item in self.items:
                for key in item.keys():
                    if key not in fieldnames:
                        fieldnames.append(key)
            with self.output_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.items)
            return self.output_path

        raise ValueError(f"unsupported feed format: {self.format}")


class CrawlerProcess:
    """最小可运行的 Scrapy 风格执行器。"""

    def __init__(
        self,
        spider: Spider,
        downloader: Optional[HTTPDownloader] = None,
        pipelines: Optional[List[ItemPipeline]] = None,
        spider_middlewares: Optional[List[SpiderMiddleware]] = None,
        downloader_middlewares: Optional[List[DownloaderMiddleware]] = None,
        plugins: Optional[List[ScrapyPlugin]] = None,
    ):
        self.spider = spider
        self.downloader = downloader or HTTPDownloader()
        self.pipelines = list(pipelines or [])
        self.spider_middlewares = list(spider_middlewares or [])
        self.downloader_middlewares = list(downloader_middlewares or [])
        self.plugins = list(plugins or [])
        self.collected_items: List[Item] = []
        self._seen_urls: set[str] = set()
        self.spider.crawler = self

    def crawl(self) -> List[Item]:
        for plugin in self.plugins:
            plugin.on_spider_opened(self.spider)
        queue = list(self.spider.start_requests())
        for pipeline in self.pipelines:
            pipeline.open_spider(self.spider)

        try:
            while queue:
                request = queue.pop(0)
                if request.url in self._seen_urls:
                    continue
                if not self._is_allowed(request.url):
                    continue
                self._seen_urls.add(request.url)

                try:
                    for middleware in self.downloader_middlewares:
                        middleware.process_request(request, self.spider)

                    response = self.downloader.download(request)
                    for middleware in self.downloader_middlewares:
                        response = middleware.process_response(
                            request, response, self.spider
                        )
                except Exception as exc:
                    for middleware in self.downloader_middlewares:
                        middleware.process_exception(request, exc, self.spider)
                    raise

                page = Page(response=response)
                callback = request.callback or self.spider.parse

                for middleware in self.spider_middlewares:
                    middleware.process_spider_input(request, self.spider)

                try:
                    results = _normalize_callback_output(callback(page))
                    for middleware in self.spider_middlewares:
                        results = middleware.process_spider_output(
                            response, results, self.spider
                        )
                except Exception as exc:
                    for middleware in self.spider_middlewares:
                        middleware.process_spider_exception(response, exc, self.spider)
                    raise

                if isinstance(self.spider, CrawlSpider):
                    results.extend(self.spider._requests_to_follow(page))

                for result in results:
                    if isinstance(result, Request):
                        if result.url not in self._seen_urls:
                            queue.append(result)
                        continue

                    item = (
                        result
                        if isinstance(result, Item)
                        else Item(**_item_to_dict(result))
                    )
                    for pipeline in self.pipelines:
                        processed = pipeline.process_item(item, self.spider)
                        if isinstance(processed, Item):
                            item = processed
                        elif isinstance(processed, dict):
                            item = Item(**processed)
                    for plugin in self.plugins:
                        processed = plugin.process_item(item, self.spider)
                        if isinstance(processed, Item):
                            item = processed
                        elif isinstance(processed, dict):
                            item = Item(**processed)
                    self.collected_items.append(item)
        finally:
            for pipeline in self.pipelines:
                pipeline.close_spider(self.spider)
            for plugin in self.plugins:
                plugin.on_spider_closed(self.spider)
            closer = getattr(self.downloader, "close", None)
            if callable(closer):
                closer()

        return self.collected_items

    def start(self) -> List[Item]:
        return self.crawl()

    def _is_allowed(self, url: str) -> bool:
        if not self.spider.allowed_domains:
            return True
        netloc = urlparse(url).netloc
        return any(
            netloc == domain or netloc.endswith(f".{domain}")
            for domain in self.spider.allowed_domains
        )


def _normalize_callback_output(result: Any) -> List[Any]:
    if result is None:
        return []
    if isinstance(result, (Request, Item, dict)):
        return [result]
    if isinstance(result, Iterable) and not isinstance(result, (str, bytes)):
        return list(result)
    return [result]


def _item_to_dict(item: Any) -> Dict[str, Any]:
    if isinstance(item, Item):
        return item.to_dict()
    if isinstance(item, dict):
        return dict(item)
    raise TypeError(f"unsupported item type: {type(item)!r}")


def response_selector(response: Response) -> HTMLParser:
    return HTMLParser(response.text)


def response_follow(
    response: Response, url: str, callback: Optional[Callable] = None
) -> Request:
    return Request(url=urljoin(response.url, url), callback=callback)


Response.selector = property(response_selector)  # type: ignore[attr-defined]
Response.follow = response_follow  # type: ignore[attr-defined]
Page.follow = lambda self, url, callback=None: response_follow(self.response, url, callback)  # type: ignore[attr-defined]


def load_ai_project_assets(project_root: Path | None = None) -> Dict[str, Any]:
    root = (project_root or Path.cwd()).resolve()
    schema_path = root / "ai-schema.json"
    blueprint_path = root / "ai-blueprint.json"
    prompt_path = root / "ai-extract-prompt.txt"
    auth_path = root / "ai-auth.json"

    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "url": {"type": "string"},
        },
    }
    if schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

    blueprint: Dict[str, Any] = {}
    if blueprint_path.exists():
        blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))

    extraction_prompt = str(blueprint.get("extraction_prompt") or "").strip()
    if not extraction_prompt and prompt_path.exists():
        extraction_prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not extraction_prompt:
        extraction_prompt = "提取标题、摘要和 URL"

    pagination = blueprint.get("pagination") or {}
    javascript_runtime = blueprint.get("javascript_runtime") or {}
    anti_bot_strategy = blueprint.get("anti_bot_strategy") or {}
    auth = blueprint.get("authentication") or {}
    recommended_runner = (
        javascript_runtime.get("recommended_runner")
        or anti_bot_strategy.get("recommended_runner")
        or "http"
    )
    request_headers: Dict[str, str] = {}
    request_cookies: Dict[str, str] = {}
    browser_meta: Dict[str, Any] = {}
    if auth_path.exists():
        auth_payload = json.loads(auth_path.read_text(encoding="utf-8"))
        request_headers.update(
            {
                str(key): str(value)
                for key, value in dict(auth_payload.get("headers") or {}).items()
            }
        )
        request_cookies.update(
            {
                str(key): str(value)
                for key, value in dict(auth_payload.get("cookies") or {}).items()
            }
        )
        if auth_payload.get("storage_state_file"):
            browser_meta["storage_state_file"] = str(auth_payload.get("storage_state_file"))
        if auth_payload.get("cookies_file"):
            browser_meta["cookies_file"] = str(auth_payload.get("cookies_file"))
        if auth_payload.get("session"):
            browser_meta["session"] = str(auth_payload.get("session"))
    if os.getenv("SPIDER_AUTH_COOKIE"):
        request_headers["Cookie"] = os.getenv("SPIDER_AUTH_COOKIE", "")
    if os.getenv("SPIDER_AUTH_HEADERS_JSON"):
        try:
            request_headers.update(
                {
                    str(key): str(value)
                    for key, value in json.loads(
                        os.getenv("SPIDER_AUTH_HEADERS_JSON", "{}")
                    ).items()
                }
            )
        except Exception:
            pass
    if bool(auth.get("required")) and recommended_runner == "http":
        recommended_runner = "browser"

    return {
        "project_root": str(root),
        "schema": schema,
        "blueprint": blueprint,
        "extraction_prompt": extraction_prompt,
        "pagination_enabled": bool(pagination.get("enabled")),
        "pagination_selectors": list(pagination.get("selectors") or []),
        "recommended_runner": recommended_runner,
        "auth_required": bool(auth.get("required")),
        "request_headers": request_headers,
        "request_cookies": request_cookies,
        "browser_meta": browser_meta,
    }


def ai_start_request_meta(assets: Dict[str, Any]) -> Dict[str, Any]:
    runner = str(assets.get("recommended_runner") or "http")
    meta: Dict[str, Any] = {"runner": runner} if runner != "http" else {}
    browser_meta = dict(assets.get("browser_meta") or {})
    if browser_meta:
        meta["browser"] = browser_meta
    return meta


def apply_ai_request_strategy(request: Request, assets: Dict[str, Any]) -> Request:
    runner = str(assets.get("recommended_runner") or "http")
    if runner != "http":
        request.meta["runner"] = runner
    browser_meta = dict(assets.get("browser_meta") or {})
    if browser_meta:
        request.meta["browser"] = {**dict(request.meta.get("browser") or {}), **browser_meta}
    for key, value in dict(assets.get("request_headers") or {}).items():
        request.headers[str(key)] = str(value)
    for key, value in dict(assets.get("request_cookies") or {}).items():
        request.cookies[str(key)] = str(value)
    return request


def iter_ai_follow_requests(
    page: Page,
    callback: Optional[Callable],
    assets: Dict[str, Any],
) -> List[Request]:
    if not assets.get("pagination_enabled"):
        return []

    selectors = list(assets.get("pagination_selectors") or [])
    seen: set[str] = set()
    requests: List[Request] = []
    for selector in selectors:
        for link in page.response.css(f"{selector}::attr(href)").getall():
            if not link or link in seen:
                continue
            seen.add(link)
            request = page.follow(link, callback)
            requests.append(apply_ai_request_strategy(request, assets))
    return requests


__all__ = [
    "apply_ai_request_strategy",
    "ai_start_request_meta",
    "CrawlerProcess",
    "CrawlSpider",
    "DownloaderMiddleware",
    "FeedExporter",
    "Item",
    "ItemPipeline",
    "iter_ai_follow_requests",
    "LinkExtractor",
    "Loader",
    "load_ai_project_assets",
    "Rule",
    "ScrapyPlugin",
    "Spider",
    "SpiderMiddleware",
]
