"""
Node.js 逆向服务客户端
为 Python Spider 提供统一的逆向能力
"""

import requests
import json
from typing import Dict, List, Optional, Any


class NodeReverseClient:
    """Node.js 逆向服务客户端"""

    DEFAULT_BASE_URL = "http://localhost:3000"

    def __init__(self, base_url: str = None):
        """
        初始化客户端

        Args:
            base_url: 逆向服务地址
        """
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.session.timeout = 30

    def health_check(self) -> bool:
        """健康检查"""
        try:
            resp = self.session.get(f"{self.base_url}/health")
            return resp.status_code == 200
        except Exception:
            return False

    def analyze_crypto(self, code: str) -> Dict[str, Any]:
        """
        分析代码中的加密算法

        Args:
            code: JavaScript 代码

        Returns:
            分析结果
        """
        return self._do_request("/api/crypto/analyze", {"code": code})

    def encrypt(
        self, algorithm: str, data: str, key: str, iv: str = None, mode: str = "CBC"
    ) -> Dict[str, Any]:
        """
        执行加密操作

        Args:
            algorithm: 加密算法 (AES, DES, RSA, MD5, SHA等)
            data: 待加密数据
            key: 密钥
            iv: 初始化向量
            mode: 加密模式

        Returns:
            加密结果
        """
        payload = {"algorithm": algorithm, "data": data, "key": key, "mode": mode}
        if iv:
            payload["iv"] = iv

        return self._do_request("/api/crypto/encrypt", payload)

    def decrypt(
        self, algorithm: str, data: str, key: str, iv: str = None, mode: str = "CBC"
    ) -> Dict[str, Any]:
        """
        执行解密操作

        Args:
            algorithm: 加密算法
            data: 待解密数据
            key: 密钥
            iv: 初始化向量
            mode: 加密模式

        Returns:
            解密结果
        """
        payload = {"algorithm": algorithm, "data": data, "key": key, "mode": mode}
        if iv:
            payload["iv"] = iv

        return self._do_request("/api/crypto/decrypt", payload)

    def execute_js(
        self, code: str, context: Dict = None, timeout: int = 5000
    ) -> Dict[str, Any]:
        """
        执行 JavaScript 代码

        Args:
            code: JavaScript 代码
            context: 上下文变量
            timeout: 超时时间(毫秒)

        Returns:
            执行结果
        """
        payload = {"code": code, "timeout": timeout}
        if context:
            payload["context"] = context

        return self._do_request("/api/js/execute", payload)

    def analyze_ast(self, code: str, analysis: List[str] = None) -> Dict[str, Any]:
        """
        AST 语法分析

        Args:
            code: JavaScript 代码
            analysis: 分析类型列表 ['crypto', 'obfuscation', 'anti-debug']

        Returns:
            分析结果
        """
        payload = {
            "code": code,
            "analysis": analysis or ["crypto", "obfuscation", "anti-debug"],
        }

        return self._do_request("/api/ast/analyze", payload)

    def analyze_webpack(self, code: str) -> Dict[str, Any]:
        """
        Webpack 打包分析

        Args:
            code: Webpack 打包后的代码

        Returns:
            分析结果
        """
        return self._do_request("/api/webpack/analyze", {"code": code})

    def call_function(
        self, function_name: str, args: List, code: str
    ) -> Dict[str, Any]:
        """
        调用 JavaScript 函数

        Args:
            function_name: 函数名
            args: 参数列表
            code: 函数定义代码

        Returns:
            函数返回值
        """
        payload = {"functionName": function_name, "args": args, "code": code}

        return self._do_request("/api/function/call", payload)

    def simulate_browser(
        self, code: str, browser_config: Dict = None
    ) -> Dict[str, Any]:
        """
        模拟浏览器环境

        Args:
            code: JavaScript 代码
            browser_config: 浏览器配置
                {
                    'userAgent': '...',
                    'language': 'zh-CN',
                    'platform': 'Win32'
                }

        Returns:
            执行结果和 cookies
        """
        payload = {"code": code}
        if browser_config:
            payload["browserConfig"] = browser_config

        return self._do_request("/api/browser/simulate", payload)

    def detect_anti_bot(
        self,
        html: str = "",
        js: str = "",
        headers: Optional[Dict[str, Any]] = None,
        cookies: str = "",
        status_code: Optional[int] = None,
        url: str = "",
    ) -> Dict[str, Any]:
        """
        检测页面中的反爬挑战特征
        """
        payload = {
            "html": html,
            "js": js,
            "headers": headers or {},
            "cookies": cookies,
            "url": url,
        }
        if status_code is not None:
            payload["statusCode"] = status_code
        return self._do_request("/api/anti-bot/detect", payload)

    def profile_anti_bot(
        self,
        html: str = "",
        js: str = "",
        headers: Optional[Dict[str, Any]] = None,
        cookies: str = "",
        status_code: Optional[int] = None,
        url: str = "",
    ) -> Dict[str, Any]:
        """
        生成完整的反爬画像、请求蓝图和规避计划
        """
        payload = {
            "html": html,
            "js": js,
            "headers": headers or {},
            "cookies": cookies,
            "url": url,
        }
        if status_code is not None:
            payload["statusCode"] = status_code
        return self._do_request("/api/anti-bot/profile", payload)

    def spoof_fingerprint(
        self,
        browser: str = "chrome",
        platform: str = "windows",
    ) -> Dict[str, Any]:
        """
        生成伪造浏览器指纹。
        """
        return self._do_request(
            "/api/fingerprint/spoof",
            {
                "browser": browser,
                "platform": platform,
            },
        )

    def generate_tls_fingerprint(
        self,
        browser: str = "chrome",
        version: str = "120",
    ) -> Dict[str, Any]:
        """
        生成 TLS 指纹配置。
        """
        return self._do_request(
            "/api/tls/fingerprint",
            {
                "browser": browser,
                "version": version,
            },
        )

    def reverse_signature(
        self, code: str, input_data: str, expected_output: str
    ) -> Dict[str, Any]:
        """
        逆向签名算法

        Args:
            code: 签名代码
            input_data: 输入数据
            expected_output: 期望输出

        Returns:
            逆向结果
        """
        payload = {"code": code, "input": input_data, "expectedOutput": expected_output}

        return self._do_request("/api/signature/reverse", payload)

    def _do_request(self, path: str, payload: Dict) -> Dict[str, Any]:
        """执行 HTTP 请求"""
        try:
            resp = self.session.post(
                f"{self.base_url}{path}", json=payload, timeout=self.session.timeout
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON 解析失败: {e}"}


# 便捷函数
def create_client(base_url: str = None) -> NodeReverseClient:
    """创建逆向客户端"""
    return NodeReverseClient(base_url)
