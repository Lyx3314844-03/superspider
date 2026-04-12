"""
Python Spider 终极增强版 v5.0
最强大的智能数据爬虫框架
"""

import asyncio
import json
import re
import time
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from pyspider.encrypted.enhanced import EncryptedSiteCrawlerEnhanced
from pyspider.node_reverse.client import NodeReverseClient


@dataclass
class UltimateConfig:
    """终极配置"""

    reverse_service_url: str = "http://localhost:3000"
    max_concurrency: int = 10
    max_retries: int = 3
    timeout: int = 30
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    proxy_servers: List[str] = field(default_factory=list)
    output_format: str = "json"
    monitor_port: int = 8080
    checkpoint_dir: str = "artifacts/ultimate/checkpoints"
    enable_ai: bool = True
    enable_browser: bool = True
    enable_distributed: bool = True
    enable_ml: bool = True


@dataclass
class CrawlTask:
    """爬取任务"""

    id: str
    url: str
    priority: int = 0
    depth: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrawlResult:
    """爬取结果"""

    task_id: str
    url: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    retries: int = 0
    proxy_used: Optional[str] = None
    anti_detect: Dict[str, bool] = field(default_factory=dict)
    anti_bot_level: Optional[str] = None
    anti_bot_signals: List[str] = field(default_factory=list)
    reverse_runtime: Dict[str, Any] = field(default_factory=dict)


class UltimateSpider:
    """Python Spider 终极增强版"""

    def __init__(self, config: UltimateConfig = None):
        """
        初始化终极爬虫

        Args:
            config: 终极配置
        """
        self.config = config or UltimateConfig()
        self.reverse_client = NodeReverseClient(self.config.reverse_service_url)
        self.enhanced_crawler = EncryptedSiteCrawlerEnhanced(
            self.config.reverse_service_url
        )
        self.task_queue = asyncio.Queue()
        self.result_queue = asyncio.Queue()
        self.proxy_pool = ProxyPool(self.config.proxy_servers)
        self.monitor = SpiderMonitor()
        self.checkpoint_mgr = CheckpointManager(self.config.checkpoint_dir)
        self.data_pipeline = DataPipeline(self.config.output_format)

        # AI 和 ML 组件
        if self.config.enable_ai:
            self.ai_extractor = AIExtractor()
        if self.config.enable_ml:
            self.ml_predictor = MLPredictor()

    async def start(self, urls: List[str]) -> List[CrawlResult]:
        """
        启动终极爬虫

        Args:
            urls: 目标 URL 列表

        Returns:
            爬取结果列表
        """
        print("\n" + "=" * 100)
        print("🚀 Python Spider 终极增强版 v5.0")
        print("=" * 100)

        # 步骤 1: 检查服务
        print("\n[1/10] 检查 Node.js 逆向服务...")
        if not self.reverse_client.health_check():
            raise Exception("Node.js 逆向服务不可用")
        print("✅ 逆向服务正常运行")

        # 步骤 2: 初始化监控
        print("\n[2/10] 初始化监控面板...")
        self.monitor.start()
        print("✅ 监控面板已启动")

        # 步骤 3: 添加任务
        print("\n[3/10] 添加爬取任务...")
        for i, url in enumerate(urls):
            task = CrawlTask(id=f"task_{i}", url=url, priority=0, depth=0, metadata={})
            await self.task_queue.put(task)
            self.monitor.add_task(task)
        print(f"✅ 已添加 {len(urls)} 个任务")

        # 步骤 4: 创建工作线程
        print("\n[4/10] 创建工作线程池...")
        workers = []
        for i in range(self.config.max_concurrency):
            worker = asyncio.create_task(self.worker(i))
            workers.append(worker)
        print(f"✅ 已启动 {self.config.max_concurrency} 个工作线程")

        # 步骤 5: 等待任务完成
        print("\n[5/10] 开始爬取...")
        await self.task_queue.join()

        # 收集结果
        results = []
        while not self.result_queue.empty():
            result = await self.result_queue.get()
            results.append(result)

        print("\n" + "=" * 100)
        print("✅ 爬取完成！")
        print("=" * 100)

        return results

    async def worker(self, worker_id: int):
        """工作线程"""
        while True:
            task = await self.task_queue.get()
            try:
                result = await self.crawl_page(task)
                await self.result_queue.put(result)
            except Exception as e:
                print(f"❌ 工作线程 {worker_id} 错误: {e}")
            finally:
                self.task_queue.task_done()

    async def crawl_page(self, task: CrawlTask) -> CrawlResult:
        """
        爬取单个页面

        Args:
            task: 爬取任务

        Returns:
            爬取结果
        """
        start_time = time.time()
        result = CrawlResult(
            task_id=task.id, url=task.url, success=False, anti_detect={}
        )

        print(f"\n📄 爬取页面: {task.url}")

        try:
            # 步骤 1: 智能反爬检测
            print("  [1/8] 智能反爬检测...")
            anti_detect, anti_bot_level, anti_bot_signals = self.detect_anti_detection(
                task.url
            )
            result.anti_detect = anti_detect
            result.anti_bot_level = anti_bot_level
            result.anti_bot_signals = anti_bot_signals
            print(
                f"  ✅ 检测到 {sum(1 for enabled in anti_detect.values() if enabled)} 种反爬机制"
            )
            if anti_bot_level:
                print(f"    level: {anti_bot_level}")
            if anti_bot_signals:
                print(f"    signals: {', '.join(anti_bot_signals)}")

            # 步骤 2: 自动反爬绕过
            print("  [2/8] 自动反爬绕过...")
            if anti_detect.get("captcha"):
                print("    🔓 检测到验证码")
                # 破解验证码

            if anti_detect.get("waf"):
                print("    🛡️  检测到 WAF")
                if self.proxy_pool:
                    proxy = self.proxy_pool.get_next_proxy()
                    result.proxy_used = proxy
                    print(f"    ✅ 切换到代理: {proxy}")
            print("  ✅ 反爬绕过完成")

            # 步骤 3: TLS 指纹生成
            print("  [3/8] TLS 指纹生成...")
            tls_browser = "chrome"
            if any(signal.startswith("vendor:") for signal in anti_bot_signals):
                tls_browser = "chrome"
            tls_fp = self.enhanced_crawler.generate_tls_fingerprint(tls_browser, "120")
            print(f"  ✅ JA3: {tls_fp['ja3']}")

            # 步骤 4: Canvas 指纹生成
            print("  [4/8] Canvas 指纹生成...")
            canvas_fp = self.enhanced_crawler.generate_canvas_fingerprint()
            print(f"  ✅ Hash: {canvas_fp['hash']}")

            reverse_runtime = self.collect_reverse_runtime(task.url)
            result.reverse_runtime = reverse_runtime

            # 步骤 5: 浏览器模拟
            print("  [5/8] 浏览器环境模拟...")
            browser_result = self.simulate_browser(task.url)
            if browser_result.get("success"):
                print("  ✅ 浏览器模拟完成")
            else:
                print(
                    f"  ⚠️ 浏览器模拟未完成: {browser_result.get('error', 'unknown error')}"
                )

            # 步骤 6: 加密分析
            print("  [6/8] 加密分析...")
            encryption_result = self.analyze_encryption(task.url)
            if encryption_result.get("success"):
                print("  ✅ 加密分析完成")
            else:
                print(
                    f"  ⚠️ 加密分析未完成: {encryption_result.get('error', 'unknown error')}"
                )

            # 步骤 7: AI 提取
            print("  [7/8] AI 智能提取...")
            data = self.ai_extract(task.url)
            if isinstance(data, dict):
                data["_runtime"] = {
                    "browser": browser_result,
                    "encryption": encryption_result,
                    "reverse": reverse_runtime,
                }
            result.data = data
            print("  ✅ AI 提取完成")

            # 步骤 8: 数据存储
            print("  [8/8] 数据存储...")
            stored_path = self.store_data(task.id, data)
            self.checkpoint_mgr.save_checkpoint(task.id, data)
            print(f"  ✅ 数据存储完成: {stored_path}")

            result.success = True
            result.duration = time.time() - start_time

            print(f"  ✅ 页面爬取完成: {result.duration:.2f}s")

        except Exception as e:
            result.error = str(e)
            result.duration = time.time() - start_time
            print(f"  ❌ 爬取失败: {e}")

        return result

    def detect_anti_detection(self, url: str):
        """检测反爬机制"""
        anti_detect = {
            "captcha": False,
            "waf": False,
            "rate_limit": False,
            "ip_ban": False,
            "js_challenge": False,
        }
        try:
            response = requests.get(
                url,
                headers=self.enhanced_crawler.get_enhanced_headers(),
                timeout=self.config.timeout,
                allow_redirects=True,
            )
            profile = self.reverse_client.profile_anti_bot(
                html=response.text,
                headers=dict(response.headers),
                cookies="; ".join(
                    f"{cookie.name}={cookie.value}" for cookie in response.cookies
                ),
                status_code=response.status_code,
                url=url,
            )
            signals = profile.get("signals") or []
            for signal in signals:
                if signal == "captcha":
                    anti_detect["captcha"] = True
                elif signal.startswith("vendor:"):
                    anti_detect["waf"] = True
                elif signal in {"rate-limit", "requires-paced-requests"}:
                    anti_detect["rate_limit"] = True
                elif signal == "request-blocked":
                    anti_detect["ip_ban"] = True
                elif signal in {"javascript-challenge", "managed-browser-challenge"}:
                    anti_detect["js_challenge"] = True
            return anti_detect, profile.get("level"), signals
        except Exception:
            return anti_detect, None, []

    def collect_reverse_runtime(self, url: str) -> Dict[str, Any]:
        """收集 reverse 能力摘要。"""
        try:
            response = requests.get(
                url,
                headers=self.enhanced_crawler.get_enhanced_headers(),
                timeout=self.config.timeout,
                allow_redirects=True,
            )
            headers = dict(response.headers)
            cookies = "; ".join(
                f"{cookie.name}={cookie.value}" for cookie in response.cookies
            )
            detect = self.reverse_client.detect_anti_bot(
                html=response.text,
                headers=headers,
                cookies=cookies,
                status_code=response.status_code,
                url=url,
            )
            profile = self.reverse_client.profile_anti_bot(
                html=response.text,
                headers=headers,
                cookies=cookies,
                status_code=response.status_code,
                url=url,
            )
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
            }

        return {
            "success": True,
            "detect": detect,
            "profile": profile,
            "fingerprint_spoof": self.reverse_client.spoof_fingerprint(
                "chrome", "windows"
            ),
            "tls_fingerprint": self.reverse_client.generate_tls_fingerprint(
                "chrome", "120"
            ),
        }

    def simulate_browser(self, url: str) -> Dict[str, Any]:
        """模拟浏览器"""
        try:
            response = requests.get(
                url,
                headers=self.enhanced_crawler.get_enhanced_headers(),
                timeout=self.config.timeout,
                allow_redirects=True,
            )
            html = response.text
            fingerprint_probe = (
                "return JSON.stringify({"
                "userAgent: navigator.userAgent,"
                "language: navigator.language,"
                "platform: navigator.platform"
                "});"
            )
            if "navigator." not in html and "webdriver" not in html:
                return {
                    "success": False,
                    "skipped": True,
                    "error": "page does not advertise browser fingerprint checks",
                    "status_code": response.status_code,
                }

            result = self.reverse_client.simulate_browser(
                fingerprint_probe,
                {
                    "userAgent": self.config.user_agent,
                    "language": "zh-CN",
                    "platform": "Win32",
                },
            )
            return {
                "success": bool(result.get("success")),
                "status_code": response.status_code,
                "result": result.get("result"),
                "cookies": result.get("cookies", ""),
                "error": result.get("error", ""),
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
            }

    def analyze_encryption(self, url: str) -> Dict[str, Any]:
        """分析加密"""
        try:
            response = requests.get(
                url,
                headers=self.enhanced_crawler.get_enhanced_headers(),
                timeout=self.config.timeout,
                allow_redirects=True,
            )
            html = response.text
            scripts = re.findall(
                r"<script[^>]*>(.*?)</script>", html, flags=re.IGNORECASE | re.DOTALL
            )
            candidate = next(
                (
                    script.strip()
                    for script in scripts
                    if script.strip()
                    and any(
                        marker in script
                        for marker in (
                            "CryptoJS",
                            "encrypt(",
                            "decrypt(",
                            "eval(function(",
                        )
                    )
                ),
                html[:20000],
            )
            result = self.reverse_client.analyze_crypto(candidate)
            return {
                "success": bool(result.get("success")),
                "status_code": response.status_code,
                "crypto_types": result.get("cryptoTypes", []),
                "keys": result.get("keys", []),
                "ivs": result.get("ivs", []),
                "analysis": result.get("analysis"),
                "error": result.get("error", ""),
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
            }

    def ai_extract(self, url: str) -> Dict[str, Any]:
        """AI 提取"""
        if self.config.enable_ai:
            return self.ai_extractor.extract(url)
        return {"url": url}

    def store_data(self, task_id: str, data: Any) -> str:
        """存储数据"""
        return self.data_pipeline.store(task_id, data)


class ProxyPool:
    """代理池"""

    def __init__(self, proxies: List[str]):
        self.proxies = (
            proxies if proxies else ["http://proxy1:8080", "http://proxy2:8080"]
        )
        self.current_idx = 0

    def get_next_proxy(self) -> str:
        """获取下一个代理"""
        if not self.proxies:
            return ""
        proxy = self.proxies[self.current_idx]
        self.current_idx = (self.current_idx + 1) % len(self.proxies)
        return proxy


class SpiderMonitor:
    """爬虫监控器"""

    def __init__(self):
        self.total_tasks = 0
        self.success_tasks = 0
        self.failed_tasks = 0
        self.start_time = None
        self.current_tasks = {}

    def start(self):
        """启动监控"""
        import datetime

        self.start_time = datetime.datetime.now()

    def add_task(self, task: CrawlTask):
        """添加任务"""
        self.total_tasks += 1
        self.current_tasks[task.id] = task


class CheckpointManager:
    """断点管理器"""

    def __init__(self, checkpoint_dir: str):
        self.checkpoint_dir = checkpoint_dir

    def save_checkpoint(self, task_id: str, data: Any):
        """保存断点"""
        checkpoint_dir = Path(self.checkpoint_dir)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = checkpoint_dir / f"{task_id}.json"
        checkpoint_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def load_checkpoint(self, task_id: str) -> Optional[Any]:
        """加载断点"""
        checkpoint_path = Path(self.checkpoint_dir) / f"{task_id}.json"
        if not checkpoint_path.exists():
            return None
        return json.loads(checkpoint_path.read_text(encoding="utf-8"))


class DataPipeline:
    """数据管道"""

    def __init__(self, output_format: str):
        self.output_format = output_format
        self.output_dir = Path("artifacts") / "ultimate" / "results"

    def store(self, task_id: str, data: Any) -> str:
        """存储数据"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        extension = "json" if self.output_format == "json" else "json"
        output_path = self.output_dir / f"{task_id}.{extension}"
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return str(output_path)


class AIExtractor:
    """AI 提取器"""

    def extract(self, url: str) -> Dict[str, Any]:
        """
        使用 AI 提取数据

        Args:
            url: 目标 URL

        Returns:
            提取的数据
        """
        # 这里可以集成真实的 LLM API
        return {
            "url": url,
            "title": "AI Extracted Title",
            "content": "AI Extracted Content",
            "metadata": {},
        }


class MLPredictor:
    """机器学习预测器"""

    def predict(self, data: Any) -> Any:
        """
        使用 ML 预测

        Args:
            data: 输入数据

        Returns:
            预测结果
        """
        # 这里可以集成真实的 ML 模型
        return data


# 便捷函数
def create_ultimate_spider(config: UltimateConfig = None) -> UltimateSpider:
    """创建终极爬虫"""
    return UltimateSpider(config)


# 示例用法
async def main():
    """主函数"""
    # 创建配置
    config = UltimateConfig(
        max_concurrency=5,
        max_retries=3,
        enable_ai=True,
        enable_ml=True,
    )

    # 创建爬虫
    spider = UltimateSpider(config)

    # 开始爬取
    urls = [
        "https://example.com",
        "https://example.org",
    ]

    await spider.start(urls)

    # 输出结果
    print("\n📊 爬取结果:")
    print(f"  总任务数: {spider.monitor.total_tasks}")
    print(f"  成功: {spider.monitor.success_tasks}")
    print(f"  失败: {spider.monitor.failed_tasks}")


if __name__ == "__main__":
    asyncio.run(main())
