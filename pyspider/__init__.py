"""
pyspider - Python Web Crawler Framework
功能完整的爬虫框架
"""

__version__ = "1.0.0"
__author__ = "pyspider team"

# 核心模块
from pyspider.core.spider import Spider
from pyspider.core.models import Request, Response, Page
from pyspider.downloader.downloader import HTTPDownloader
from pyspider.parser.parser import HTMLParser, JSONParser

# Scrapy 风格
from pyspider.spider.spider import Spider as ScrapySpider, CrawlSpider, Rule, Item, Loader
from pyspider.spider.spider import ItemPipeline, SpiderMiddleware, DownloaderMiddleware

# 动态爬取
from pyspider.dynamic.wait import DynamicWait, ScrollLoader, FormInteractor
from pyspider.dynamic.enhanced import DynamicWaitEnhanced, ScrollLoaderEnhanced, FormInteractorEnhanced

# 性能优化
from pyspider.performance.limiter import RateLimiter, CircuitBreaker, ConnectionPool, AdaptiveRateLimiter
from pyspider.core.multithread import WorkerPool, ConcurrentExecutor, AsyncExecutor

# 分布式
from pyspider.distributed.redis import RedisScheduler, DistributedSpider

# Web 控制台
from pyspider.web.console import WebConsole

# 反反爬
from pyspider.antibot.antibot import AntiBotHandler, CloudflareBypass, AkamaiBypass, CaptchaSolver

# 媒体爬取
from pyspider.media.downloader import MediaDownloader, MediaURLs, DownloadStats

# 定时任务
from pyspider.task.scheduler import Scheduler, TimedTask, CronTask, schedule_task

# 验证码
from pyspider.captcha.solver import CaptchaSolver as CaptchaSolverService

# 代理
from pyspider.proxy.proxy import ProxyPool, Proxy

# 监控
from pyspider.monitor.monitor import SpiderMonitor, SpiderStats
Monitor = SpiderMonitor
Stats = SpiderStats

# AI 提取
from pyspider.extractor.extractor import AIExtractor

# 数据转换
from pyspider.transformer.transformer import DataTransformer, DataValidator

__all__ = [
    # 核心
    'Spider', 'Request', 'Response', 'Page',
    'HTTPDownloader', 'HTMLParser', 'JSONParser',
    
    # Scrapy 风格
    'ScrapySpider', 'CrawlSpider', 'Rule', 'Item', 'Loader',
    'ItemPipeline', 'SpiderMiddleware', 'DownloaderMiddleware',
    
    # 动态爬取
    'DynamicWait', 'ScrollLoader', 'FormInteractor',
    'DynamicWaitEnhanced', 'ScrollLoaderEnhanced', 'FormInteractorEnhanced',
    
    # 性能优化
    'RateLimiter', 'CircuitBreaker', 'ConnectionPool', 'AdaptiveRateLimiter',
    'WorkerPool', 'ConcurrentExecutor', 'AsyncExecutor',
    
    # 分布式
    'RedisScheduler', 'DistributedSpider',
    
    # Web 控制台
    'WebConsole',
    
    # 反反爬
    'AntiBotHandler', 'CloudflareBypass', 'AkamaiBypass', 'CaptchaSolver',
    
    # 媒体爬取
    'MediaDownloader', 'MediaURLs', 'DownloadStats',
    
    # 定时任务
    'Scheduler', 'TimedTask', 'CronTask', 'schedule_task',
    
    # 验证码
    'CaptchaSolverService',
    
    # 代理
    'ProxyPool', 'Proxy',
    
    # 监控
    'Monitor', 'Stats',
    
    # AI 提取
    'AIExtractor',
    
    # 数据转换
    'DataTransformer', 'DataValidator',
]
