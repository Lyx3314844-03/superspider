import requests
from typing import List, Optional, Dict, Any


class CrawleeBridgeClient:
    """
    Python 语言调用 Crawlee 桥接服务的客户端
    """

    def __init__(self, bridge_url: str = "http://localhost:3100"):
        self.bridge_url = bridge_url
        self.session = requests.Session()

    def crawl(
        self, urls: List[str], script: Optional[str] = None, max_concurrency: int = 2
    ) -> Dict[str, Any]:
        """
        执行 Crawlee 抓取任务

        Args:
            urls: 目标 URL 列表
            script: 可选的页面执行脚本 (JavaScript)
            max_concurrency: 并发数

        Returns:
            抓取结果字典
        """
        payload = {
            "urls": urls,
            "onPageScript": script or "",
            "maxConcurrency": max_concurrency,
        }

        try:
            response = self.session.post(
                f"{self.bridge_url}/api/crawl", json=payload, timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Crawlee Bridge Error: {e}")
