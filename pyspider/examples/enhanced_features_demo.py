"""
增强版 pyspider 使用示例
展示新增的持久化队列、重试、错误处理、配置、Cookie、代理功能
"""

import sys
sys.path.insert(0, 'C:/Users/Administrator/spider')

from pyspider.core.config import ConfigLoader, create_default_config
from pyspider.core.queue import PersistentPriorityQueue, RetryQueue, QueueItem
from pyspider.core.retry import RetryHandler, RetryConfig, RetryStrategy, CircuitBreaker
from pyspider.core.exceptions import SpiderError, ErrorType, ErrorHandler, HTTPError
from pyspider.core.cookie import CookieJar
from pyspider.proxy.proxy_pool import ProxyPool, ProxyFetcher


def demo_config():
    """配置管理示例"""
    print("\n" + "="*60)
    print("配置管理示例")
    print("="*60)
    
    # 创建默认配置（如果不存在）
    import os
    if not os.path.exists("config.yaml"):
        create_default_config("config.yaml")
    
    # 加载配置
    loader = ConfigLoader("config.yaml")
    
    print(f"爬虫名称：{loader.spider.name}")
    print(f"最大请求数：{loader.spider.max_requests}")
    print(f"线程数：{loader.spider.thread_count}")
    print(f"下载器超时：{loader.downloader.timeout}秒")
    print(f"代理启用：{loader.proxy.enabled}")
    
    # 使用点路径获取
    print(f"媒体输出目录：{loader.get('media.output_dir')}")
    
    # 验证配置
    errors = loader.validate()
    if errors:
        print("配置验证失败:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✓ 配置验证通过")


def demo_queue():
    """持久化队列示例"""
    print("\n" + "="*60)
    print("持久化队列示例")
    print("="*60)
    
    # 创建队列
    queue = PersistentPriorityQueue(db_path="demo_queue.db", max_size=10000)
    
    # 添加请求（不同优先级）
    queue.put("https://example.com/1", priority=10, depth=0)
    queue.put("https://example.com/2", priority=5, depth=1)
    queue.put("https://example.com/3", priority=15, depth=0)
    queue.put("https://example.com/4", priority=8, depth=2)
    
    print(f"队列大小：{queue.size()}")
    print(f"统计信息：{queue.get_stats()}")
    
    # 获取请求（按优先级顺序）
    print("\n按优先级获取请求:")
    while queue.size() > 0:
        item = queue.get()
        print(f"  获取：{item.url} (优先级：{item.priority}, 深度：{item.depth})")
    
    # 重试队列
    retry_queue = RetryQueue(max_retries=3)
    test_item = QueueItem(url="https://example.com/failed", priority=10)
    retry_queue.add_retry(test_item, reason="Timeout")
    
    print(f"\n重试队列大小：{retry_queue.size()}")
    
    queue.close()


def demo_retry():
    """重试机制示例"""
    print("\n" + "="*60)
    print("重试机制示例")
    print("="*60)
    
    import requests
    
    # 配置重试
    config = RetryConfig(
        max_retries=3,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        base_delay=1.0,
    )
    
    handler = RetryHandler(config)
    
    # 示例：带重试的 HTTP 请求
    def make_request(url: str):
        return requests.get(url, timeout=10)
    
    # 执行（可能失败）
    print("尝试请求 https://httpbin.org/status/500 (会返回 500 错误)...")
    result = handler.execute_with_retry(make_request, "https://httpbin.org/status/500")
    
    print(f"成功：{result.success}")
    print(f"尝试次数：{result.attempts}")
    print(f"总耗时：{result.total_time:.2f}秒")
    print(f"延迟列表：{result.delays}")
    print(f"统计信息：{handler.get_stats()}")
    
    # 熔断器示例
    print("\n熔断器示例:")
    breaker = CircuitBreaker(failure_threshold=3, timeout=10)
    
    try:
        def failing_request():
            raise Exception("Service unavailable")
        breaker.call(failing_request)
    except Exception as e:
        print(f"熔断器测试：{e}")
    
    print(f"熔断器状态：{breaker.get_stats()}")


def demo_error_handling():
    """错误处理示例"""
    print("\n" + "="*60)
    print("错误处理示例")
    print("="*60)
    
    # 创建错误处理器
    handler = ErrorHandler()
    
    # 注册处理器
    def log_rate_limit(error):
        print(f"  [处理器] 遇到频率限制：{error.context.url}")
    
    handler.register_handler(ErrorType.RATE_LIMIT_ERROR, log_rate_limit)
    
    # 创建各种错误
    errors = [
        HTTPError("页面不存在", status_code=404).record(),
        SpiderError(
            "服务器错误",
            error_type=ErrorType.HTTP_5XX_ERROR,
            context=type('obj', (object,), {'url': 'https://example.com', 'status_code': 500})()
        ).record(),
    ]
    
    # 处理错误
    for error in errors:
        print(f"\n处理错误：{error}")
        handler.handle(error)
    
    print(f"\n错误摘要：{handler.get_error_summary()}")


def demo_cookie():
    """Cookie 管理示例"""
    print("\n" + "="*60)
    print("Cookie 管理示例")
    print("="*60)
    
    # 创建 Cookie 容器
    jar = CookieJar(persist_file="demo_cookies.pkl")
    
    # 设置 Cookie
    jar.set("session_id", "abc123", domain="example.com", expires=3600)
    jar.set("user_id", "12345", domain=".example.com", path="/admin")
    jar.set("preferences", "dark_mode", domain="example.com")
    
    # 获取 Cookie
    cookie = jar.get("session_id", "example.com")
    if cookie:
        print(f"Cookie: {cookie.name} = {cookie.value}")
    
    # 获取 URL 适用的 Cookie
    cookies = jar.get_for_url("https://www.example.com/admin/page")
    print(f"URL Cookies: {cookies}")
    
    # 统计信息
    print(f"统计：{jar.get_stats()}")
    
    # 导出
    jar.export_netscape("demo_cookies.txt")
    print("已导出 Netscape 格式 Cookie")


def demo_proxy():
    """代理管理示例"""
    print("\n" + "="*60)
    print("代理管理示例")
    print("="*60)
    
    # 创建代理池
    pool = ProxyPool(
        proxy_file="proxies.txt",
        validate_url="https://www.baidu.com",
        validate_timeout=5,
    )
    
    # 采集免费代理
    print("正在采集免费代理...")
    fetcher = ProxyFetcher()
    proxies = fetcher.fetch_all()
    added = pool.add_proxies(proxies)
    print(f"采集了 {added} 个代理")
    
    print(f"代理池统计：{pool.get_stats()}")
    
    # 获取代理
    proxy = pool.get_best_proxy()
    if proxy:
        print(f"最佳代理：{proxy.url} (评分：{proxy.score:.1f})")
    
    # 使用示例
    try:
        import requests
        proxy = pool.get_proxy()
        if proxy:
            print(f"使用代理 {proxy.url} 发送请求...")
            resp = requests.get(
                "https://www.baidu.com",
                proxies={"http": proxy.url, "https": proxy.url},
                timeout=10,
            )
            print(f"请求成功：{resp.status_code}")
            pool.record_success(proxy, resp.elapsed.total_seconds() * 1000)
    except Exception as e:
        if proxy:
            pool.record_failure(proxy)
        print(f"请求失败：{e}")
    
    # 保存代理
    pool.save_to_file("valid_proxies.txt")
    pool.export_json("proxies.json")


def main():
    """主函数"""
    print("\n" + "╔"*60 + "╗")
    print("║"*20 + " pyspider 增强功能演示 " + "║"*20)
    print("╚"*60 + "╝")
    
    try:
        # 1. 配置管理
        demo_config()
        
        # 2. 持久化队列
        demo_queue()
        
        # 3. 重试机制
        demo_retry()
        
        # 4. 错误处理
        demo_error_handling()
        
        # 5. Cookie 管理
        demo_cookie()
        
        # 6. 代理管理
        demo_proxy()
        
        print("\n" + "═"*60)
        print("演示完成！")
        print("═"*60)
        
    except Exception as e:
        print(f"\n演示失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
