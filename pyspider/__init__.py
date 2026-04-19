"""
pyspider - Python Web Crawler Framework

顶层包改为懒加载，避免导入一个符号时把所有子系统和可选依赖都立即拉起。
"""

from __future__ import annotations

import importlib

__version__ = "1.0.0"
__author__ = "pyspider team"

_EXPORTS = {
    "Spider": ("pyspider.core.spider", "Spider"),
    "Request": ("pyspider.core.models", "Request"),
    "Response": ("pyspider.core.models", "Response"),
    "Page": ("pyspider.core.models", "Page"),
    "HTTPDownloader": ("pyspider.downloader.downloader", "HTTPDownloader"),
    "HTMLParser": ("pyspider.parser.parser", "HTMLParser"),
    "JSONParser": ("pyspider.parser.parser", "JSONParser"),
    "ScrapySpider": ("pyspider.spider.spider", "Spider"),
    "CrawlSpider": ("pyspider.spider.spider", "CrawlSpider"),
    "Rule": ("pyspider.spider.spider", "Rule"),
    "LinkExtractor": ("pyspider.spider.spider", "LinkExtractor"),
    "Item": ("pyspider.spider.spider", "Item"),
    "Loader": ("pyspider.spider.spider", "Loader"),
    "FeedExporter": ("pyspider.spider.spider", "FeedExporter"),
    "CrawlerProcess": ("pyspider.spider.spider", "CrawlerProcess"),
    "ScrapyPlugin": ("pyspider.spider.spider", "ScrapyPlugin"),
    "ItemPipeline": ("pyspider.spider.spider", "ItemPipeline"),
    "SpiderMiddleware": ("pyspider.spider.spider", "SpiderMiddleware"),
    "DownloaderMiddleware": ("pyspider.spider.spider", "DownloaderMiddleware"),
    "DynamicWait": ("pyspider.dynamic.wait", "DynamicWait"),
    "ScrollLoader": ("pyspider.dynamic.wait", "ScrollLoader"),
    "FormInteractor": ("pyspider.dynamic.wait", "FormInteractor"),
    "DynamicWaitEnhanced": ("pyspider.dynamic.enhanced", "DynamicWaitEnhanced"),
    "ScrollLoaderEnhanced": ("pyspider.dynamic.enhanced", "ScrollLoaderEnhanced"),
    "FormInteractorEnhanced": ("pyspider.dynamic.enhanced", "FormInteractorEnhanced"),
    "RateLimiter": ("pyspider.performance.limiter", "RateLimiter"),
    "CircuitBreaker": ("pyspider.performance.circuit_breaker", "CircuitBreaker"),
    "ConnectionPool": ("pyspider.performance.limiter", "ConnectionPool"),
    "AdaptiveRateLimiter": ("pyspider.performance.limiter", "AdaptiveRateLimiter"),
    "WorkerPool": ("pyspider.core.multithread", "WorkerPool"),
    "ConcurrentExecutor": ("pyspider.core.multithread", "ConcurrentExecutor"),
    "AsyncExecutor": ("pyspider.core.multithread", "AsyncExecutor"),
    "RedisScheduler": ("pyspider.distributed.redis", "RedisScheduler"),
    "DistributedSpider": ("pyspider.distributed.redis", "DistributedSpider"),
    "WebConsole": ("pyspider.web.console", "WebConsole"),
    "AntiBotHandler": ("pyspider.antibot.antibot", "AntiBotHandler"),
    "CloudflareBypass": ("pyspider.antibot.antibot", "CloudflareBypass"),
    "AkamaiBypass": ("pyspider.antibot.antibot", "AkamaiBypass"),
    "CaptchaSolver": ("pyspider.antibot.antibot", "CaptchaSolver"),
    "MediaDownloader": ("pyspider.media.downloader", "MediaDownloader"),
    "MediaURLs": ("pyspider.media.downloader", "MediaURLs"),
    "DownloadStats": ("pyspider.media.downloader", "DownloadStats"),
    "Scheduler": ("pyspider.task.scheduler", "Scheduler"),
    "TimedTask": ("pyspider.task.scheduler", "TimedTask"),
    "CronTask": ("pyspider.task.scheduler", "CronTask"),
    "schedule_task": ("pyspider.task.scheduler", "schedule_task"),
    "CaptchaSolverService": ("pyspider.captcha.solver", "CaptchaSolver"),
    "ProxyPool": ("pyspider.proxy.proxy", "ProxyPool"),
    "Proxy": ("pyspider.proxy.proxy", "Proxy"),
    "Monitor": ("pyspider.monitor.monitor", "SpiderMonitor"),
    "Stats": ("pyspider.monitor.monitor", "SpiderStats"),
    "SpiderMonitor": ("pyspider.monitor.monitor", "SpiderMonitor"),
    "SpiderStats": ("pyspider.monitor.monitor", "SpiderStats"),
    "AIExtractor": ("pyspider.extractor.extractor", "AIExtractor"),
    "DataTransformer": ("pyspider.transformer.transformer", "DataTransformer"),
    "DataValidator": ("pyspider.transformer.transformer", "DataValidator"),
    "RequestFingerprint": ("pyspider.core.contracts", "RequestFingerprint"),
    "AutoscaledFrontier": ("pyspider.core.contracts", "AutoscaledFrontier"),
    "FrontierConfig": ("pyspider.core.contracts", "FrontierConfig"),
    "MiddlewareChain": ("pyspider.core.contracts", "MiddlewareChain"),
    "FileArtifactStore": ("pyspider.core.contracts", "FileArtifactStore"),
    "ObservabilityCollector": ("pyspider.core.contracts", "ObservabilityCollector"),
    "FailureClassifier": ("pyspider.core.contracts", "FailureClassifier"),
    "RuntimeSessionPool": ("pyspider.core.contracts", "SessionPool"),
    "ProxyPolicy": ("pyspider.core.contracts", "ProxyPolicy"),
    "IncrementalCrawler": ("pyspider.core.incremental", "IncrementalCrawler"),
    "AuditEvent": ("pyspider.runtime.audit", "AuditEvent"),
    "MemoryAuditTrail": ("pyspider.runtime.audit", "MemoryAuditTrail"),
    "FileAuditTrail": ("pyspider.runtime.audit", "FileAuditTrail"),
    "CompositeAuditTrail": ("pyspider.runtime.audit", "CompositeAuditTrail"),
    "Event": ("pyspider.events", "Event"),
    "EventBus": ("pyspider.events", "EventBus"),
    "TaskLifecyclePayload": ("pyspider.events", "TaskLifecyclePayload"),
    "TaskResultPayload": ("pyspider.events", "TaskResultPayload"),
    "TaskDeletedPayload": ("pyspider.events", "TaskDeletedPayload"),
}

__all__ = [
    "Spider",
    "Request",
    "Response",
    "Page",
    "HTTPDownloader",
    "HTMLParser",
    "JSONParser",
    "ScrapySpider",
    "CrawlSpider",
    "Rule",
    "LinkExtractor",
    "Item",
    "Loader",
    "FeedExporter",
    "CrawlerProcess",
    "ScrapyPlugin",
    "RequestFingerprint",
    "AutoscaledFrontier",
    "FrontierConfig",
    "MiddlewareChain",
    "FileArtifactStore",
    "ObservabilityCollector",
    "FailureClassifier",
    "RuntimeSessionPool",
    "ProxyPolicy",
    "IncrementalCrawler",
    "AuditEvent",
    "MemoryAuditTrail",
    "FileAuditTrail",
    "CompositeAuditTrail",
    "Event",
    "EventBus",
    "TaskLifecyclePayload",
    "TaskResultPayload",
    "TaskDeletedPayload",
]


def __getattr__(name: str):
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module 'pyspider' has no attribute {name!r}")

    module_name, attr_name = target
    module = importlib.import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(list(globals().keys()) + __all__)
