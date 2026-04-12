"""
加密网站爬取模块
为 Python Spider 提供强大的加密网站爬取能力
"""

import re
import requests
from typing import Dict, Optional, Any
from pyspider.node_reverse.client import NodeReverseClient


class EncryptedSiteCrawler:
    """加密网站爬虫"""

    def __init__(self, reverse_service_url: str = "http://localhost:3000"):
        """
        初始化加密网站爬虫

        Args:
            reverse_service_url: Node.js 逆向服务地址
        """
        self.reverse_client = NodeReverseClient(reverse_service_url)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
            }
        )

        # 配置超时适配器
        from requests.adapters import HTTPAdapter

        adapter = HTTPAdapter(max_retries=3)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self._timeout = 30  # 存储超时时间

        # 加密检测模式
        self.encryption_patterns = [
            r"CryptoJS\.(AES|DES|RSA|MD5|SHA|HMAC|RC4|Base64)",
            r"encrypt\(|decrypt\(",
            r"createCipheriv|createDecipheriv",
            r"publicEncrypt|privateDecrypt",
            r"btoa\(|atob\(",
            r"eval\(function\(p,a,c,k,e,d\)",
            r"\\x[0-9a-fA-F]{2}",
        ]

    def crawl(self, url: str) -> Dict[str, Any]:
        """
        爬取加密网站

        Args:
            url: 目标网站 URL

        Returns:
            爬取结果
        """
        result = {
            "url": url,
            "html": "",
            "anti_bot_profile": None,
            "encryption_info": {
                "patterns": [],
                "encrypted_scripts": {},
                "script_count": 0,
            },
            "decrypted_data": [],
            "webpack_modules": 0,
            "success": False,
            "error": None,
        }

        print("\n" + "=" * 80)
        print("🔐 加密网站爬取处理器 (Python Spider)")
        print("=" * 80)

        try:
            # 步骤 1: 检查逆向服务
            print("\n[1/6] 检查 Node.js 逆向服务...")
            if not self._check_reverse_service():
                result["error"] = "Node.js 逆向服务不可用"
                result["success"] = False
                return result
            print("✅ 逆向服务正常运行")

            # 步骤 2: 获取页面
            print("\n[2/6] 获取加密页面...")
            response = self._fetch_page(url)
            if response is None:
                result["error"] = "获取页面失败"
                result["success"] = False
                return result
            html = response.text
            result["html"] = html
            print(f"✅ 页面获取成功，大小: {len(html)} 字节")

            anti_bot_profile = self._profile_anti_bot(url, response)
            if anti_bot_profile:
                result["anti_bot_profile"] = anti_bot_profile

            # 步骤 3: 检测加密
            print("\n[3/6] 检测页面加密...")
            encryption_info = self._detect_encryption(html)
            result["encryption_info"] = encryption_info
            if encryption_info["patterns"] or encryption_info["encrypted_scripts"]:
                self._print_encryption_info(encryption_info)
            else:
                print("ℹ️  未检测到明显加密")
            print("✅ 加密检测完成")

            # 步骤 4: 模拟浏览器环境
            print("\n[4/6] 模拟浏览器环境...")
            self._simulate_browser(html)
            print("✅ 浏览器模拟完成")

            # 步骤 5: 分析加密算法
            print("\n[5/6] 分析加密算法...")
            if encryption_info["encrypted_scripts"]:
                self._analyze_encryption(encryption_info["encrypted_scripts"])
            print("✅ 加密分析完成")

            # 步骤 6: 执行混淆代码
            print("\n[6/6] 执行混淆代码...")
            self._execute_obfuscated_code(html)
            print("✅ 混淆代码执行完成")

            result["success"] = True
            print("\n" + "=" * 80)
            print("✅ 加密网站爬取完成！")
            print("=" * 80 + "\n")

        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
            print(f"❌ 处理加密网站时出错: {e}")

        return result

    def _check_reverse_service(self) -> bool:
        """检查逆向服务"""
        try:
            return self.reverse_client.health_check()
        except Exception:
            return False

    def _fetch_page(self, url: str):
        """获取页面"""
        try:
            resp = self.session.get(url, allow_redirects=True, timeout=self._timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            print(f"❌ 获取页面失败: {e}")
            return None

    def _profile_anti_bot(self, url: str, response) -> Optional[Dict[str, Any]]:
        """生成反爬画像并应用请求蓝图"""
        try:
            profile = self.reverse_client.profile_anti_bot(
                html=response.text,
                headers=dict(response.headers),
                cookies="; ".join(
                    f"{cookie.name}={cookie.value}" for cookie in response.cookies
                ),
                status_code=response.status_code,
                url=url,
            )
        except Exception as e:
            print(f"⚠️  反爬画像分析失败: {e}")
            return None

        if not profile or not profile.get("success"):
            return None

        print(
            f"🛡️  Anti-bot profile: level={profile.get('level')} "
            f"score={profile.get('score')}"
        )
        signals = profile.get("signals") or []
        if signals:
            print(f"   signals: {', '.join(signals)}")
        recommendations = profile.get("recommendations") or []
        if recommendations:
            print(f"   next: {recommendations[0]}")

        headers = profile.get("requestBlueprint", {}).get("headers", {})
        if isinstance(headers, dict):
            for key, value in headers.items():
                if isinstance(key, str) and isinstance(value, str):
                    self.session.headers[key] = value

        return profile

    def _detect_encryption(self, html: str) -> Dict[str, Any]:
        """检测加密"""
        info = {"patterns": [], "encrypted_scripts": {}, "script_count": 0}

        # 检测加密模式
        for pattern in self.encryption_patterns:
            if re.search(pattern, html):
                info["patterns"].append(pattern)

        # 提取 script 标签
        script_pattern = re.compile(r"<script[^>]*>(.*?)</script>", re.DOTALL)
        scripts = script_pattern.findall(html)
        info["script_count"] = len(scripts)

        # 分析每个脚本
        for i, script in enumerate(scripts):
            script = script.strip()
            if script and not script.startswith("<!--"):
                if self._is_encrypted(script):
                    key = f"script_{i}"
                    info["encrypted_scripts"][key] = script

        return info

    def _is_encrypted(self, code: str) -> bool:
        """检查代码是否被加密"""
        if (
            "eval(function(" in code
            or "\\x" in code
            or (len(code) > 1000 and " " not in code)
        ):
            return True

        return any(
            keyword in code
            for keyword in ["CryptoJS.", "encrypt(", "decrypt(", "atob(", "btoa("]
        )

    def _simulate_browser(self, html: str):
        """模拟浏览器环境"""
        # 检测浏览器指纹
        if re.search(r"navigator\.(userAgent|platform|language|vendor)", html):
            print("  🌐 检测到浏览器指纹检测")

            try:
                result = self.reverse_client.simulate_browser(
                    "return JSON.stringify({userAgent: navigator.userAgent, platform: navigator.platform});",
                    {
                        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "language": "zh-CN",
                        "platform": "Win32",
                    },
                )

                if result.get("success"):
                    print("  ✅ 浏览器环境模拟成功")
            except Exception as e:
                print(f"  ⚠️  浏览器模拟失败: {e}")

    def _analyze_encryption(self, scripts: Dict[str, str]):
        """分析加密算法"""
        for key, script in scripts.items():
            print(f"  🔍 分析 {key}...")

            try:
                result = self.reverse_client.analyze_crypto(script)

                if result.get("success") and result.get("cryptoTypes"):
                    print("    ✅ 检测到加密算法:")
                    for crypto in result["cryptoTypes"]:
                        print(
                            f"      - {crypto['name']} (置信度: {crypto['confidence']:.2f})"
                        )

                if result.get("keys"):
                    print("    🔑 密钥:")
                    for key in result["keys"]:
                        print(f"      - {key}")
            except Exception as e:
                print(f"    ❌ 分析失败: {e}")

    def _execute_obfuscated_code(self, html: str):
        """执行混淆代码"""
        # 查找 eval 混淆的代码
        eval_pattern = re.compile(r"eval\(function\(p,a,c,k,e,d\)\{(.*?)\}")
        matches = eval_pattern.findall(html)

        count = 0
        for obfuscated_code in matches[:5]:
            count += 1
            print(f"  📦 执行混淆代码块 #{count}...")

            try:
                result = self.reverse_client.execute_js(
                    obfuscated_code,
                    {
                        "window": {},
                        "document": {},
                        "navigator": {"userAgent": "Mozilla/5.0"},
                    },
                    10000,
                )

                if result.get("success"):
                    print("    ✅ 执行成功")
                    result_text = str(result.get("result", ""))
                    print(f"    📝 结果: {result_text[:100]}")
            except Exception as e:
                print(f"    ❌ 执行失败: {e}")

        if count == 0:
            print("  ℹ️  未找到 eval 混淆代码")

    def _print_encryption_info(self, info: Dict[str, Any]):
        """打印加密信息"""
        if info["patterns"]:
            print("  🔐 检测到加密模式:")
            for pattern in info["patterns"]:
                print(f"    - {pattern}")

        if info["encrypted_scripts"]:
            print(f"  📜 加密脚本数: {len(info['encrypted_scripts'])}")

        print(f"  📄 总脚本数: {info['script_count']}")


# 便捷函数
def create_crawler(reverse_service_url: str = None) -> EncryptedSiteCrawler:
    """创建加密网站爬虫"""
    return EncryptedSiteCrawler(reverse_service_url)
