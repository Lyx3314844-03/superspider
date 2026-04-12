"""
代理池管理器 - 支持多代理轮换、健康检查和自动故障转移
"""

import time
import threading
import requests
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ProxyStatus(Enum):
    UNKNOWN = "unknown"
    ALIVE = "alive"
    DEAD = "dead"


@dataclass
class Proxy:
    """代理服务器"""

    host: str
    port: int
    protocol: str = "http"  # http, https, socks5
    username: Optional[str] = None
    password: Optional[str] = None
    status: ProxyStatus = ProxyStatus.UNKNOWN
    success_count: int = 0
    failure_count: int = 0
    last_checked: Optional[float] = None
    response_time: float = 0.0

    @property
    def url(self) -> str:
        """获取代理 URL"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def proxies_dict(self) -> Dict[str, str]:
        """获取 requests 格式的代理字典"""
        return {"http": self.url, "https": self.url}

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0


class ProxyPool:
    """代理池管理器"""

    def __init__(
        self,
        check_url: str = "https://httpbin.org/ip",
        check_interval: int = 300,
        max_failures: int = 3,
    ):
        self._proxies: List[Proxy] = []
        self._lock = threading.RLock()
        self._current_index = 0
        self._check_url = check_url
        self._check_interval = check_interval
        self._max_failures = max_failures
        self._health_check_running = False
        self._health_check_thread: Optional[threading.Thread] = None

    def add_proxy(self, proxy: Proxy) -> None:
        """添加代理"""
        with self._lock:
            self._proxies.append(proxy)
            logger.info(f"代理已添加: {proxy.url}")

    def add_proxies(self, proxies: List[Proxy]) -> None:
        """批量添加代理"""
        for proxy in proxies:
            self.add_proxy(proxy)

    def add_proxy_from_string(self, proxy_str: str) -> None:
        """
        从字符串添加代理
        支持格式:
        - http://host:port
        - http://user:pass@host:port
        - host:port
        """
        import re

        # 修复: 使用非贪婪匹配支持密码中的特殊字符
        pattern = r"^(?:(\w+)://)?(?:(.+?):(.+?)@)?([\w.-]+):(\d+)$"
        match = re.match(pattern, proxy_str)
        if match:
            protocol = match.group(1) or "http"
            username = match.group(2)
            password = match.group(3)
            host = match.group(4)
            port = int(match.group(5))
            self.add_proxy(
                Proxy(
                    host=host,
                    port=port,
                    protocol=protocol,
                    username=username,
                    password=password,
                )
            )
        else:
            logger.warning(f"代理格式无效: {proxy_str}")

    def get_proxy(self) -> Optional[Proxy]:
        """获取下一个可用代理(轮询+健康状态)"""
        with self._lock:
            if not self._proxies:
                return None

            # 尝试最多 len(proxies) 次找到可用代理
            for _ in range(len(self._proxies)):
                proxy = self._proxies[self._current_index % len(self._proxies)]
                self._current_index += 1

                if (
                    proxy.status == ProxyStatus.ALIVE
                    and proxy.failure_count < self._max_failures
                ):
                    return proxy

            # 如果没有健康代理,返回第一个未知状态的代理
            for proxy in self._proxies:
                if proxy.status == ProxyStatus.UNKNOWN:
                    return proxy

            # 所有代理都不可用,返回 None
            return None

    def record_success(self, proxy: Proxy) -> None:
        """记录成功"""
        with self._lock:
            proxy.success_count += 1
            proxy.status = ProxyStatus.ALIVE
            proxy.last_checked = time.time()

    def record_failure(self, proxy: Proxy) -> None:
        """记录失败"""
        with self._lock:
            proxy.failure_count += 1
            proxy.last_checked = time.time()
            if proxy.failure_count >= self._max_failures:
                proxy.status = ProxyStatus.DEAD
                logger.warning(f"代理已标记为死亡: {proxy.url}")

    def check_proxy(self, proxy: Proxy, timeout: int = 10) -> bool:
        """检查代理是否可用"""
        try:
            start = time.time()
            resp = requests.get(
                self._check_url, proxies=proxy.proxies_dict, timeout=timeout
            )
            proxy.response_time = time.time() - start
            if resp.status_code == 200:
                proxy.failure_count = 0  # 修复: 恢复时重置失败计数
                self.record_success(proxy)
                return True
            else:
                self.record_failure(proxy)
                return False
        except Exception as e:
            logger.debug(f"代理检查失败 {proxy.url}: {e}")
            self.record_failure(proxy)
            return False

    def start_health_check(self) -> None:
        """启动健康检查后台线程"""
        if self._health_check_running:
            return

        self._health_check_running = True
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop, daemon=True
        )
        self._health_check_thread.start()
        logger.info("代理健康检查已启动")

    def stop_health_check(self) -> None:
        """停止健康检查"""
        self._health_check_running = False
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5)
        logger.info("代理健康检查已停止")

    def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self._health_check_running:
            with self._lock:
                proxies_to_check = list(self._proxies)

            for proxy in proxies_to_check:
                if proxy.status == ProxyStatus.DEAD:
                    # 定期检查死亡代理是否可以恢复
                    if (
                        proxy.last_checked
                        and (time.time() - proxy.last_checked)
                        > self._check_interval * 2
                    ):
                        self.check_proxy(proxy)
                else:
                    self.check_proxy(proxy)

            time.sleep(self._check_interval)

    def check_all(self, timeout: int = 10) -> Dict[str, bool]:
        """检查所有代理"""
        results = {}
        with self._lock:
            for proxy in self._proxies:
                results[proxy.url] = self.check_proxy(proxy, timeout)
        return results

    @property
    def size(self) -> int:
        """代理池大小"""
        return len(self._proxies)

    @property
    def alive_count(self) -> int:
        """可用代理数量"""
        return sum(1 for p in self._proxies if p.status == ProxyStatus.ALIVE)

    @property
    def dead_count(self) -> int:
        """死亡代理数量"""
        return sum(1 for p in self._proxies if p.status == ProxyStatus.DEAD)

    def stats(self) -> Dict:
        """代理池统计"""
        return {
            "total": self.size,
            "alive": self.alive_count,
            "dead": self.dead_count,
            "unknown": sum(1 for p in self._proxies if p.status == ProxyStatus.UNKNOWN),
        }
