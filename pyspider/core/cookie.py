"""
Cookie 管理模块
支持持久化、自动过期、域名隔离
"""

import pickle
import threading
import time
import os
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


@dataclass
class Cookie:
    """Cookie 对象"""

    name: str
    value: str
    domain: str = ""
    path: str = "/"
    expires: Optional[float] = None  # Unix 时间戳
    secure: bool = False
    http_only: bool = False
    same_site: str = "Lax"  # Strict, Lax, None
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires is None:
            return False
        return time.time() > self.expires

    def is_persistent(self) -> bool:
        """是否是持久化 Cookie"""
        return self.expires is not None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "value": self.value,
            "domain": self.domain,
            "path": self.path,
            "expires": self.expires,
            "secure": self.secure,
            "httpOnly": self.http_only,
            "sameSite": self.same_site,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Cookie":
        """从字典创建"""
        return cls(
            name=data.get("name", ""),
            value=data.get("value", ""),
            domain=data.get("domain", ""),
            path=data.get("path", "/"),
            expires=data.get("expires"),
            secure=data.get("secure", False),
            http_only=data.get("httpOnly", False),
            same_site=data.get("sameSite", "Lax"),
        )

    def matches_url(self, url: str) -> bool:
        """检查是否匹配 URL"""
        parsed = urlparse(url)
        host = parsed.netloc.split(":")[0]

        # 检查域名
        if self.domain:
            if self.domain.startswith("."):
                # .example.com 匹配 example.com 和所有子域名
                if not (host == self.domain[1:] or host.endswith(self.domain)):
                    return False
            else:
                if host != self.domain:
                    return False

        # 检查路径
        if not parsed.path.startswith(self.path):
            return False

        # 检查 secure
        if self.secure and parsed.scheme != "https":
            return False

        return True


class CookieJar:
    """Cookie 容器"""

    def __init__(self, persist_file: Optional[str] = None):
        self._cookies: Dict[str, Dict[str, Cookie]] = {}  # domain -> name -> cookie
        self._lock = threading.RLock()
        self._persist_file = persist_file
        self._auto_save = True
        self._max_cookies = 10000
        self._load()

    def _get_domain(self, url: str) -> str:
        """从 URL 提取域名"""
        parsed = urlparse(url)
        return parsed.netloc.split(":")[0]

    def _load(self):
        """从文件加载"""
        if self._persist_file and os.path.exists(self._persist_file):
            try:
                with open(self._persist_file, "rb") as f:
                    self._cookies = pickle.load(f)
                logger.info(f"已加载 {self.count()} 个 Cookie")
            except Exception as e:
                logger.error(f"加载 Cookie 失败：{e}")

    def _save(self):
        """保存到文件"""
        if self._persist_file and self._auto_save:
            try:
                os.makedirs(os.path.dirname(self._persist_file), exist_ok=True)
                with open(self._persist_file, "wb") as f:
                    pickle.dump(self._cookies, f)
                logger.debug(f"已保存 {self.count()} 个 Cookie")
            except Exception as e:
                logger.error(f"保存 Cookie 失败：{e}")

    def set(
        self,
        name: str,
        value: str,
        domain: str = "",
        path: str = "/",
        expires: Optional[int] = None,
        secure: bool = False,
        http_only: bool = False,
        same_site: str = "Lax",
    ):
        """
        设置 Cookie

        Args:
            name: Cookie 名称
            value: Cookie 值
            domain: 域名
            path: 路径
            expires: 过期时间（Unix 时间戳或秒数）
            secure: 是否仅 HTTPS
            http_only: 是否仅 HTTP
            same_site: SameSite 策略
        """
        with self._lock:
            # 处理 expires
            if expires is not None and expires < 10000000000:
                # 相对时间（秒）
                expires = time.time() + expires

            cookie = Cookie(
                name=name,
                value=value,
                domain=domain,
                path=path,
                expires=expires,
                secure=secure,
                http_only=http_only,
                same_site=same_site,
            )

            # 按域名存储
            if not domain:
                domain = "_default"

            if domain not in self._cookies:
                self._cookies[domain] = {}

            # 检查数量限制
            total = sum(len(cookies) for cookies in self._cookies.values())
            if total >= self._max_cookies:
                self._remove_oldest()

            self._cookies[domain][name] = cookie

            if self._auto_save:
                self._save()

    def get(self, name: str, domain: Optional[str] = None) -> Optional[Cookie]:
        """获取 Cookie"""
        with self._lock:
            if domain:
                if domain in self._cookies and name in self._cookies[domain]:
                    cookie = self._cookies[domain][name]
                    if not cookie.is_expired():
                        cookie.last_accessed = time.time()
                        return cookie
            else:
                # 搜索所有域名
                for domain_cookies in self._cookies.values():
                    if name in domain_cookies:
                        cookie = domain_cookies[name]
                        if not cookie.is_expired():
                            cookie.last_accessed = time.time()
                            return cookie
            return None

    def get_for_url(self, url: str) -> Dict[str, str]:
        """获取适用于 URL 的所有 Cookie"""
        with self._lock:
            result = {}
            for domain, domain_cookies in self._cookies.items():
                for name, cookie in domain_cookies.items():
                    if not cookie.is_expired() and cookie.matches_url(url):
                        result[name] = cookie.value
                        cookie.last_accessed = time.time()

            if self._auto_save:
                self._save()

            return result

    def get_all(self, domain: Optional[str] = None) -> List[Cookie]:
        """获取所有 Cookie"""
        with self._lock:
            if domain:
                cookies = self._cookies.get(domain, {}).values()
            else:
                cookies = []
                for domain_cookies in self._cookies.values():
                    cookies.extend(domain_cookies.values())

            return [c for c in cookies if not c.is_expired()]

    def delete(self, name: str, domain: Optional[str] = None):
        """删除 Cookie"""
        with self._lock:
            if domain:
                if domain in self._cookies and name in self._cookies[domain]:
                    del self._cookies[domain][name]
            else:
                for domain_cookies in self._cookies.values():
                    if name in domain_cookies:
                        del domain_cookies[name]

            self._save()

    def clear(self, domain: Optional[str] = None):
        """清空 Cookie"""
        with self._lock:
            if domain:
                if domain in self._cookies:
                    self._cookies[domain] = {}
            else:
                self._cookies = {}

            self._save()

    def count(self) -> int:
        """获取 Cookie 数量"""
        with self._lock:
            return sum(len(cookies) for cookies in self._cookies.values())

    def _remove_oldest(self):
        """移除最旧的 Cookie"""
        oldest_time = float("inf")
        oldest_domain = None
        oldest_name = None

        for domain, domain_cookies in self._cookies.items():
            for name, cookie in domain_cookies.items():
                if cookie.created_at < oldest_time:
                    oldest_time = cookie.created_at
                    oldest_domain = domain
                    oldest_name = name

        if oldest_domain and oldest_name:
            del self._cookies[oldest_domain][oldest_name]
            logger.debug(f"移除最旧 Cookie: {oldest_name}@{oldest_domain}")

    def cleanup_expired(self):
        """清理过期 Cookie"""
        with self._lock:
            count = 0
            for domain in list(self._cookies.keys()):
                for name in list(self._cookies[domain].keys()):
                    if self._cookies[domain][name].is_expired():
                        del self._cookies[domain][name]
                        count += 1
                if not self._cookies[domain]:
                    del self._cookies[domain]

            if count > 0:
                logger.info(f"清理了 {count} 个过期 Cookie")
                self._save()

    def update_from_response(self, response_headers: Dict[str, str], url: str):
        """从响应头更新 Cookie"""
        set_cookie = response_headers.get("Set-Cookie") or response_headers.get(
            "set-cookie"
        )
        if not set_cookie:
            return

        domain = self._get_domain(url)

        # 解析 Set-Cookie 头
        if isinstance(set_cookie, str):
            cookies = [set_cookie]
        else:
            cookies = set_cookie

        for cookie_str in cookies:
            self._parse_set_cookie(cookie_str, domain, url)

    def _parse_set_cookie(self, cookie_str: str, default_domain: str, url: str):
        """解析 Set-Cookie 头"""
        parts = cookie_str.split(";")
        if not parts:
            return

        # 名称和值
        name_value = parts[0].strip()
        if "=" not in name_value:
            return

        name, value = name_value.split("=", 1)

        # 属性
        domain = default_domain
        path = "/"
        expires = None
        secure = False
        http_only = False
        same_site = "Lax"

        for part in parts[1:]:
            part = part.strip().lower()

            if part.startswith("domain="):
                domain = part[7:].strip()
            elif part.startswith("path="):
                path = part[5:].strip()
            elif part.startswith("expires="):
                # 解析过期时间
                try:
                    expires_str = part[8:].strip()
                    expires = datetime.strptime(
                        expires_str, "%a, %d %b %Y %H:%M:%S GMT"
                    )
                    expires = expires.timestamp()
                except Exception:
                    pass
            elif part.startswith("max-age="):
                # 相对过期时间
                try:
                    max_age = int(part[8:])
                    expires = time.time() + max_age
                except Exception:
                    pass
            elif part == "secure":
                secure = True
            elif part == "httponly":
                http_only = True
            elif part.startswith("samesite="):
                same_site = part[9:].strip().capitalize()

        self.set(
            name=name,
            value=value,
            domain=domain,
            path=path,
            expires=expires,
            secure=secure,
            http_only=http_only,
            same_site=same_site,
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        with self._lock:
            result = {}
            for domain, cookies in self._cookies.items():
                result[domain] = {
                    name: cookie.to_dict()
                    for name, cookie in cookies.items()
                    if not cookie.is_expired()
                }
            return result

    def from_dict(self, data: dict):
        """从字典加载"""
        with self._lock:
            for domain, cookies in data.items():
                if domain not in self._cookies:
                    self._cookies[domain] = {}
                for name, cookie_data in cookies.items():
                    self._cookies[domain][name] = Cookie.from_dict(cookie_data)
            self._save()

    def export_netscape(self, path: str):
        """导出为 Netscape 格式（适用于 curl、wget 等）"""
        with self._lock:
            lines = ["# Netscape HTTP Cookie File"]
            lines.append(f"# Generated at {datetime.now().isoformat()}")
            lines.append("")

            for domain, cookies in self._cookies.items():
                for name, cookie in cookies.items():
                    if cookie.is_expired():
                        continue

                    # Netscape 格式
                    # domain  flag  path  secure  expiration  name  value
                    flag = "TRUE" if cookie.domain.startswith(".") else "FALSE"
                    secure = "TRUE" if cookie.secure else "FALSE"
                    expires = int(cookie.expires) if cookie.expires else 0

                    lines.append(
                        f"{cookie.domain}\t{flag}\t{cookie.path}\t{secure}\t{expires}\t{name}\t{cookie.value}"
                    )

            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            logger.info(f"已导出 Netscape 格式 Cookie 到：{path}")

    def import_netscape(self, path: str):
        """从 Netscape 格式导入"""
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split("\t")
                if len(parts) < 7:
                    continue

                domain = parts[0]
                path = parts[2]
                secure = parts[3] == "TRUE"
                expires = int(parts[4]) if parts[4] else None
                name = parts[5]
                value = parts[6]

                self.set(
                    name=name,
                    value=value,
                    domain=domain,
                    path=path,
                    expires=expires,
                    secure=secure,
                )

        logger.info(f"已从 Netscape 格式导入 Cookie：{path}")

    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            total = 0
            expired = 0
            persistent = 0
            by_domain = {}

            for domain, cookies in self._cookies.items():
                domain_total = 0
                for cookie in cookies.values():
                    total += 1
                    domain_total += 1
                    if cookie.is_expired():
                        expired += 1
                    if cookie.is_persistent():
                        persistent += 1
                by_domain[domain] = domain_total

            return {
                "total": total,
                "expired": expired,
                "persistent": persistent,
                "session": total - persistent,
                "domains": len(by_domain),
                "by_domain": by_domain,
            }

    def set_auto_save(self, enabled: bool):
        """设置自动保存"""
        self._auto_save = enabled

    def close(self):
        """关闭并保存"""
        self._save()


# 使用示例
if __name__ == "__main__":
    # 创建 Cookie 容器
    jar = CookieJar(persist_file="cookies.pkl")

    # 设置 Cookie
    jar.set("session_id", "abc123", domain="example.com", expires=3600)
    jar.set("user_id", "12345", domain=".example.com", path="/admin")

    # 获取 Cookie
    cookie = jar.get("session_id", "example.com")
    print(f"Cookie: {cookie.name} = {cookie.value}")

    # 获取 URL 适用的 Cookie
    cookies = jar.get_for_url("https://www.example.com/admin/page")
    print(f"URL Cookies: {cookies}")

    # 统计信息
    print(f"统计：{jar.get_stats()}")

    # 导出
    jar.export_netscape("cookies.txt")

    # 清理过期
    jar.cleanup_expired()
