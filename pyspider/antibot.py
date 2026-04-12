#!/usr/bin/env python3
"""
PySpider 反爬增强模块 - 代理池和 User-Agent 轮换
"""

import sys
import json
import random
import requests
from typing import List, Optional
from threading import Lock


class ProxyPool:
    """代理池管理"""

    def __init__(self, max_failed: int = 3, test_url: str = "https://www.google.com"):
        self.proxies: List[str] = []
        self.lock = Lock()
        self.max_failed = max_failed
        self.test_url = test_url
        self.failed_count = {}
        self.load_from_file()

    def add(self, proxy: str):
        """添加代理"""
        with self.lock:
            if proxy not in self.proxies:
                self.proxies.append(proxy)
        self.save_to_file()

    def get_random(self) -> Optional[str]:
        """获取随机代理"""
        with self.lock:
            if not self.proxies:
                return None
            return random.choice(self.proxies)

    def validate(self, proxy: str) -> bool:
        """验证代理是否可用"""
        if not self.test_url:
            return True

        try:
            response = requests.get(
                self.test_url,
                proxies={"http": f"http://{proxy}", "https": f"http://{proxy}"},
                timeout=10,
            )
            return response.status_code == 200
        except Exception:
            return False

    def load_from_file(self):
        """从文件加载代理"""
        try:
            with open("proxies.txt", "r") as f:
                self.proxies = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            pass

    def save_to_file(self):
        """保存代理到文件"""
        with self.lock:
            with open("proxies.txt", "w") as f:
                for proxy in self.proxies:
                    f.write(proxy + "\n")

    def list_all(self):
        """列出所有代理"""
        print(f"代理池大小: {len(self.proxies)}")
        for i, p in enumerate(self.proxies, 1):
            print(f"{i}. {p}")

    def test_all(self):
        """测试所有代理"""
        print("测试所有代理...")
        for p in self.proxies:
            valid = self.validate(p)
            status = "✓ 有效" if valid else "✗ 无效"
            print(f"{p} - {status}")

    def clear(self):
        """清空代理池"""
        with self.lock:
            self.proxies = []
        self.save_to_file()
        print("代理池已清空")


# User-Agent 池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]


def get_random_user_agent() -> str:
    """获取随机 User-Agent"""
    return random.choice(USER_AGENTS)


# 反爬策略配置
class AntiBotConfig:
    def __init__(self):
        self.enable_proxy = True
        self.enable_ua = True
        self.enable_cookie = True
        self.min_delay = 1000
        self.max_delay = 3000
        self.max_retries = 3

    def save(self, filename: str = "antibot_config.json"):
        with open(filename, "w") as f:
            json.dump(self.__dict__, f, indent=2)

    def load(self, filename: str = "antibot_config.json"):
        try:
            with open(filename, "r") as f:
                self.__dict__.update(json.load(f))
        except FileNotFoundError:
            pass


def detect_captcha(html: str) -> bool:
    """检测验证码"""
    captcha_patterns = [
        "captcha",
        "验证码",
        "verify",
        "robot",
        "blocked",
        "请验证",
        "security check",
        "human verification",
    ]
    html_lower = html.lower()
    return any(pattern in html_lower for pattern in captcha_patterns)


def proxy_command(args: List[str]):
    """代理管理命令"""
    pp = ProxyPool()

    if len(args) < 2:
        print("用法: antibot.py proxy <命令>")
        print("命令: add <proxy> | list | test | clear")
        return

    command = args[1]

    if command == "add" and len(args) > 2:
        pp.add(args[2])
        print(f"添加代理: {args[2]}")
    elif command == "list":
        pp.list_all()
    elif command == "test":
        pp.test_all()
    elif command == "clear":
        pp.clear()


def main():
    if len(sys.argv) < 2:
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║         PySpider 反爬增强模块                              ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        print("\n用法: antibot.py [命令]")
        print("\n命令:")
        print("  proxy <命令>   代理池管理")
        print("  test           测试反爬功能")
        print("  config         显示当前配置")
        return

    command = sys.argv[1]

    if command == "proxy":
        proxy_command(sys.argv[1:])
    elif command == "test":
        print("测试 User-Agent 轮换:")
        for i in range(3):
            print(f"  {i+1}. {get_random_user_agent()[:60]}...")
        print("\n测试代理池:")
        pp = ProxyPool()
        pp.list_all()
    elif command == "config":
        config = AntiBotConfig()
        config.load()
        print("当前反爬配置:")
        print(f"  启用代理: {config.enable_proxy}")
        print(f"  启用 UA: {config.enable_ua}")
        print(f"  启用 Cookie: {config.enable_cookie}")
        print(f"  最小延迟: {config.min_delay}ms")
        print(f"  最大延迟: {config.max_delay}ms")
        print(f"  最大重试: {config.max_retries}")


if __name__ == "__main__":
    main()
