"""
代理管理模块增强版
支持代理池、自动验证、智能切换、多源采集
"""

import random
import threading
import time
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import json
import os


logger = logging.getLogger(__name__)


@dataclass
class Proxy:
    """代理对象"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"  # http, https, socks4, socks5
    country: Optional[str] = None
    city: Optional[str] = None
    isp: Optional[str] = None
    
    # 性能指标
    response_time: float = 0.0  # 响应时间（毫秒）
    success_count: int = 0
    fail_count: int = 0
    last_used: float = 0.0
    last_checked: float = 0.0
    
    # 状态
    available: bool = True
    anonymous: bool = False  # 是否匿名
    
    @property
    def url(self) -> str:
        """获取代理 URL"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"
    
    @property
    def success_rate(self) -> float:
        """获取成功率"""
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.0
        return self.success_count / total
    
    @property
    def score(self) -> float:
        """获取代理评分（0-100）"""
        # 基于成功率和响应时间评分
        success_score = self.success_rate * 70
        
        # 响应时间评分（越快分数越高）
        if self.response_time > 0:
            time_score = max(0, 30 - (self.response_time / 100))
        else:
            time_score = 0
        
        return min(100, success_score + time_score)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "protocol": self.protocol,
            "country": self.country,
            "city": self.city,
            "isp": self.isp,
            "response_time": self.response_time,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "available": self.available,
            "anonymous": self.anonymous,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Proxy':
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ProxyPool:
    """代理池"""
    
    def __init__(
        self,
        proxy_file: Optional[str] = None,
        validate_url: str = "https://www.google.com",
        validate_timeout: int = 10,
        validate_interval: int = 300,  # 5 分钟
        min_success_rate: float = 0.8,
        max_failures: int = 10,
        auto_switch: bool = True,
    ):
        self._proxies: List[Proxy] = []
        self._current_index = 0
        self._lock = threading.RLock()
        
        # 配置
        self.proxy_file = proxy_file
        self.validate_url = validate_url
        self.validate_timeout = validate_timeout
        self.validate_interval = validate_interval
        self.min_success_rate = min_success_rate
        self.max_failures = max_failures
        self.auto_switch = auto_switch
        
        # 代理源
        self._sources: List[str] = []
        
        # 验证线程
        self._validator_thread: Optional[threading.Thread] = None
        self._stop_validation = False
        
        # 加载代理
        self._load_from_file()
    
    def _load_from_file(self):
        """从文件加载代理"""
        if self.proxy_file and os.path.exists(self.proxy_file):
            try:
                with open(self.proxy_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        proxy = self._parse_proxy_line(line)
                        if proxy:
                            self.add_proxy(proxy)
                
                logger.info(f"从文件加载了 {len(self._proxies)} 个代理")
            except Exception as e:
                logger.error(f"加载代理文件失败：{e}")
    
    def _parse_proxy_line(self, line: str) -> Optional[Proxy]:
        """解析代理行"""
        parts = line.split(':')
        
        if len(parts) >= 2:
            host = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                return None
            
            username = parts[2] if len(parts) > 2 else None
            password = parts[3] if len(parts) > 3 else None
            
            # 检测协议
            protocol = "http"
            if host.startswith("socks5://"):
                protocol = "socks5"
                host = host.replace("socks5://", "")
            elif host.startswith("socks4://"):
                protocol = "socks4"
                host = host.replace("socks4://", "")
            elif host.startswith("https://"):
                protocol = "https"
                host = host.replace("https://", "")
            elif host.startswith("http://"):
                protocol = "http"
                host = host.replace("http://", "")
            
            return Proxy(
                host=host,
                port=port,
                username=username,
                password=password,
                protocol=protocol,
            )
        
        return None
    
    def add_proxy(self, proxy: Proxy) -> bool:
        """添加代理"""
        with self._lock:
            # 检查是否已存在
            for p in self._proxies:
                if p.host == proxy.host and p.port == proxy.port:
                    return False
            
            self._proxies.append(proxy)
            return True
    
    def add_proxies(self, proxies: List[Proxy]) -> int:
        """批量添加代理"""
        count = 0
        for proxy in proxies:
            if self.add_proxy(proxy):
                count += 1
        return count
    
    def remove_proxy(self, proxy: Proxy) -> bool:
        """移除代理"""
        with self._lock:
            if proxy in self._proxies:
                self._proxies.remove(proxy)
                return True
            return False
    
    def get_proxy(self) -> Optional[Proxy]:
        """获取代理（轮询）"""
        with self._lock:
            if not self._proxies:
                return None
            
            # 过滤可用代理
            available = [p for p in self._proxies if p.available]
            
            if not available:
                # 如果没有可用代理，重置所有代理
                logger.warning("没有可用代理，重置所有代理状态")
                for p in self._proxies:
                    p.available = True
                available = self._proxies
            
            # 按评分排序
            available.sort(key=lambda p: p.score, reverse=True)
            
            # 获取最佳代理
            proxy = available[0]
            proxy.last_used = time.time()
            
            return proxy
    
    def get_random_proxy(self) -> Optional[Proxy]:
        """随机获取代理"""
        with self._lock:
            available = [p for p in self._proxies if p.available]
            if not available:
                return None
            return random.choice(available)
    
    def get_best_proxy(self) -> Optional[Proxy]:
        """获取最佳代理"""
        with self._lock:
            available = [p for p in self._proxies if p.available]
            if not available:
                return None
            return max(available, key=lambda p: p.score)
    
    def record_success(self, proxy: Proxy, response_time: float = 0):
        """记录成功"""
        with self._lock:
            proxy.success_count += 1
            proxy.last_used = time.time()
            if response_time > 0:
                # 移动平均
                proxy.response_time = (proxy.response_time * 0.8) + (response_time * 0.2)
            
            # 重置失败计数
            if proxy.fail_count > 0:
                proxy.fail_count = max(0, proxy.fail_count - 1)
    
    def record_failure(self, proxy: Proxy):
        """记录失败"""
        with self._lock:
            proxy.fail_count += 1
            proxy.last_used = time.time()
            
            # 检查是否应该禁用
            if proxy.fail_count >= self.max_failures:
                proxy.available = False
                logger.warning(f"代理 {proxy.host}:{proxy.port} 失败次数过多，已禁用")
    
    def validate_proxy(self, proxy: Proxy) -> bool:
        """验证代理"""
        try:
            proxies = {
                "http": proxy.url,
                "https": proxy.url,
            }
            
            start_time = time.time()
            resp = requests.get(
                self.validate_url,
                proxies=proxies,
                timeout=self.validate_timeout,
            )
            response_time = (time.time() - start_time) * 1000  # 毫秒
            
            if resp.status_code == 200:
                proxy.response_time = response_time
                proxy.last_checked = time.time()
                return True
            else:
                return False
                
        except Exception as e:
            logger.debug(f"代理验证失败 {proxy.url}: {e}")
            return False
    
    def validate_all(self) -> Dict[str, int]:
        """验证所有代理"""
        with self._lock:
            valid_count = 0
            invalid_count = 0
            
            for proxy in self._proxies:
                if self.validate_proxy(proxy):
                    proxy.available = True
                    valid_count += 1
                else:
                    proxy.available = False
                    invalid_count += 1
            
            logger.info(f"代理验证完成：{valid_count} 有效，{invalid_count} 无效")
            
            return {
                "valid": valid_count,
                "invalid": invalid_count,
                "total": len(self._proxies),
            }
    
    def start_auto_validation(self, interval: Optional[int] = None):
        """启动自动验证"""
        interval = interval or self.validate_interval
        
        def validate_loop():
            while not self._stop_validation:
                self.validate_all()
                time.sleep(interval)
        
        self._validator_thread = threading.Thread(target=validate_loop, daemon=True)
        self._validator_thread.start()
        logger.info(f"已启动自动验证，间隔 {interval} 秒")
    
    def stop_auto_validation(self):
        """停止自动验证"""
        self._stop_validation = True
        if self._validator_thread:
            self._validator_thread.join(timeout=5)
        logger.info("已停止自动验证")
    
    def load_from_api(self, api_url: str, parser: callable = None):
        """从 API 加载代理"""
        try:
            resp = requests.get(api_url, timeout=10)
            resp.raise_for_status()
            
            if parser:
                proxies = parser(resp.json())
            else:
                # 默认解析器（假设返回标准格式）
                data = resp.json()
                proxies = []
                for item in data:
                    proxy = Proxy(
                        host=item.get("host", ""),
                        port=item.get("port", 0),
                        username=item.get("username"),
                        password=item.get("password"),
                        protocol=item.get("protocol", "http"),
                        country=item.get("country"),
                    )
                    if proxy.host and proxy.port:
                        proxies.append(proxy)
            
            count = self.add_proxies(proxies)
            logger.info(f"从 API 加载了 {count} 个代理")
            
        except Exception as e:
            logger.error(f"从 API 加载代理失败：{e}")
    
    def load_from_sources(self):
        """从所有源加载代理"""
        for source in self._sources:
            if source.startswith("http"):
                self.load_from_api(source)
            elif os.path.exists(source):
                self.proxy_file = source
                self._load_from_file()
    
    def add_source(self, source: str):
        """添加代理源"""
        self._sources.append(source)
    
    def clear(self):
        """清空代理池"""
        with self._lock:
            self._proxies = []
            self._current_index = 0
    
    def count(self) -> int:
        """获取代理数量"""
        with self._lock:
            return len(self._proxies)
    
    def available_count(self) -> int:
        """获取可用代理数量"""
        with self._lock:
            return sum(1 for p in self._proxies if p.available)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            total = len(self._proxies)
            available = sum(1 for p in self._proxies if p.available)
            
            if total == 0:
                return {
                    "total": 0,
                    "available": 0,
                    "unavailable": 0,
                    "avg_success_rate": 0,
                    "avg_response_time": 0,
                    "by_country": {},
                }
            
            # 平均成功率
            avg_success_rate = sum(p.success_rate for p in self._proxies) / total
            
            # 平均响应时间
            avg_response_time = sum(p.response_time for p in self._proxies if p.response_time > 0)
            avg_response_time = avg_response_time / max(1, sum(1 for p in self._proxies if p.response_time > 0))
            
            # 按国家统计
            by_country = {}
            for p in self._proxies:
                country = p.country or "Unknown"
                if country not in by_country:
                    by_country[country] = {"total": 0, "available": 0}
                by_country[country]["total"] += 1
                if p.available:
                    by_country[country]["available"] += 1
            
            return {
                "total": total,
                "available": available,
                "unavailable": total - available,
                "avg_success_rate": avg_success_rate,
                "avg_response_time": avg_response_time,
                "by_country": by_country,
            }
    
    def save_to_file(self, path: str, only_available: bool = True):
        """保存到文件"""
        with self._lock:
            with open(path, 'w', encoding='utf-8') as f:
                for proxy in self._proxies:
                    if only_available and not proxy.available:
                        continue
                    f.write(f"{proxy.url}\n")
            
            logger.info(f"已保存代理到：{path}")
    
    def export_json(self, path: str):
        """导出为 JSON"""
        with self._lock:
            data = [p.to_dict() for p in self._proxies]
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"已导出代理 JSON 到：{path}")
    
    def import_json(self, path: str):
        """从 JSON 导入"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            proxies = [Proxy.from_dict(item) for item in data]
            count = self.add_proxies(proxies)
            logger.info(f"从 JSON 导入了 {count} 个代理")
            
        except Exception as e:
            logger.error(f"从 JSON 导入代理失败：{e}")
    
    def to_requests_proxies(self) -> Optional[Dict[str, str]]:
        """转换为 requests 代理格式"""
        proxy = self.get_proxy()
        if not proxy:
            return None
        
        return {
            "http": proxy.url,
            "https": proxy.url,
        }
    
    def __len__(self) -> int:
        return self.count()
    
    def __bool__(self) -> bool:
        return self.available_count() > 0


# 免费代理源
FREE_PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
]


class ProxyFetcher:
    """代理采集器"""
    
    def __init__(self):
        self.sources = FREE_PROXY_SOURCES.copy()
    
    def fetch_all(self) -> List[Proxy]:
        """从所有源采集代理"""
        all_proxies = []
        
        for source in self.sources:
            try:
                proxies = self.fetch_from_url(source)
                all_proxies.extend(proxies)
                logger.info(f"从 {source} 采集了 {len(proxies)} 个代理")
            except Exception as e:
                logger.error(f"从 {source} 采集失败：{e}")
        
        return all_proxies
    
    def fetch_from_url(self, url: str) -> List[Proxy]:
        """从 URL 采集代理"""
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        
        proxies = []
        lines = resp.text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split(':')
            if len(parts) >= 2:
                try:
                    host = parts[0].strip()
                    port = int(parts[1].strip())
                    
                    # 验证
                    if self._is_valid_ip(host) and 1 <= port <= 65535:
                        proxies.append(Proxy(host=host, port=port))
                except:
                    continue
        
        return proxies
    
    def _is_valid_ip(self, ip: str) -> bool:
        """检查是否是有效 IP"""
        import re
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        
        if not re.match(pattern, ip):
            # 可能是域名
            return True
        
        # 检查每段数字
        parts = ip.split('.')
        for part in parts:
            if not 0 <= int(part) <= 255:
                return False
        
        return True


# 使用示例
if __name__ == "__main__":
    # 创建代理池
    pool = ProxyPool(
        proxy_file="proxies.txt",
        validate_url="https://www.baidu.com",
        validate_timeout=5,
        validate_interval=300,
    )
    
    # 采集免费代理
    fetcher = ProxyFetcher()
    proxies = fetcher.fetch_all()
    pool.add_proxies(proxies)
    
    print(f"代理池统计：{pool.get_stats()}")
    
    # 获取代理
    proxy = pool.get_best_proxy()
    if proxy:
        print(f"最佳代理：{proxy.url} (评分：{proxy.score:.1f})")
    
    # 验证所有代理
    result = pool.validate_all()
    print(f"验证结果：{result}")
    
    # 启动自动验证
    pool.start_auto_validation(interval=300)
    
    # 使用代理发送请求
    try:
        proxy = pool.get_proxy()
        if proxy:
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
