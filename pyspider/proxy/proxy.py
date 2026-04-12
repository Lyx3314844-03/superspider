"""
代理管理模块
支持代理池、代理验证、自动切换
"""

import random
import threading
import time
from typing import Optional, List
from dataclasses import dataclass
import requests


@dataclass
class Proxy:
    """代理"""

    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    last_used: float = 0.0
    success_count: int = 0
    fail_count: int = 0
    available: bool = True

    @property
    def url(self) -> str:
        """获取代理 URL"""
        if self.username and self.password:
            return f"http://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"http://{self.host}:{self.port}"


class ProxyPool:
    """代理池"""

    def __init__(self):
        self._proxies: List[Proxy] = []
        self._current = 0
        self._lock = threading.RLock()

    def add_proxy(self, proxy: Proxy) -> None:
        """添加代理"""
        with self._lock:
            self._proxies.append(proxy)

    def get_proxy(self) -> Optional[Proxy]:
        """获取代理"""
        with self._lock:
            if not self._proxies:
                return None

            # 轮询获取
            proxy = self._proxies[self._current % len(self._proxies)]
            self._current += 1

            if not proxy.available:
                return self.get_proxy()

            return proxy

    def get_random_proxy(self) -> Optional[Proxy]:
        """随机获取代理"""
        with self._lock:
            if not self._proxies:
                return None
            return random.choice(self._proxies)

    def record_success(self, proxy: Proxy) -> None:
        """记录成功"""
        with self._lock:
            proxy.success_count += 1
            proxy.last_used = time.time()

    def record_failure(self, proxy: Proxy) -> None:
        """记录失败"""
        with self._lock:
            proxy.fail_count += 1
            if proxy.fail_count > 10:
                proxy.available = False

    def remove_proxy(self, proxy: Proxy) -> None:
        """移除代理"""
        with self._lock:
            if proxy in self._proxies:
                self._proxies.remove(proxy)

    def proxy_count(self) -> int:
        """获取代理数量"""
        with self._lock:
            return len(self._proxies)

    def available_count(self) -> int:
        """获取可用代理数量"""
        with self._lock:
            return sum(1 for p in self._proxies if p.available)

    def load_from_file(self, filename: str) -> None:
        """从文件加载代理"""
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split(":")
                if len(parts) >= 2:
                    proxy = Proxy(
                        host=parts[0],
                        port=int(parts[1]),
                        username=parts[2] if len(parts) > 2 else None,
                        password=parts[3] if len(parts) > 3 else None,
                    )
                    self.add_proxy(proxy)

    def save_to_file(self, filename: str) -> None:
        """保存代理到文件"""
        with open(filename, "w") as f:
            for proxy in self._proxies:
                if proxy.username and proxy.password:
                    f.write(
                        f"{proxy.host}:{proxy.port}:{proxy.username}:{proxy.password}\n"
                    )
                else:
                    f.write(f"{proxy.host}:{proxy.port}\n")

    def validate_proxy(
        self, proxy: Proxy, test_url: str = "https://www.google.com", timeout: int = 10
    ) -> bool:
        """验证代理"""
        try:
            proxies = {
                "http": proxy.url,
                "https": proxy.url,
            }
            resp = requests.get(test_url, proxies=proxies, timeout=timeout)
            return resp.status_code == 200
        except Exception:
            return False

    def validate_all(
        self, test_url: str = "https://www.google.com", timeout: int = 10
    ) -> int:
        """验证所有代理"""
        valid_count = 0
        with self._lock:
            for proxy in self._proxies:
                if self.validate_proxy(proxy, test_url, timeout):
                    proxy.available = True
                    valid_count += 1
                else:
                    proxy.available = False
        return valid_count
