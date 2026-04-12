"""
Node.js 逆向 Fetcher
集成到 PySpider 的 fetcher 流程中
"""

import requests

try:
    from pyspider.fetcher.tornado_fetcher import Fetcher
except ImportError:

    class Fetcher:  # type: ignore[override]
        """在当前源码树缺少旧 fetcher 时提供最小可运行 fallback。"""

        def __init__(self, *args, **kwargs):
            pass

        def fetch(self, task, callback=None):
            fetch_cfg = task.get("fetch", {}) if isinstance(task, dict) else {}
            url = (
                fetch_cfg.get("url") or task.get("url")
                if isinstance(task, dict)
                else None
            )
            if not url:
                raise ValueError("task.url is required")

            method = str(fetch_cfg.get("method") or task.get("method") or "GET").upper()
            headers = dict(fetch_cfg.get("headers") or task.get("headers") or {})
            data = fetch_cfg.get("data") or fetch_cfg.get("body")
            timeout = fetch_cfg.get("timeout", 30)
            response = requests.request(
                method,
                url,
                headers=headers,
                data=data,
                timeout=timeout,
            )
            result = {
                "status_code": response.status_code,
                "content": response.text,
                "headers": dict(response.headers),
                "orig_url": response.url,
                "content_type": response.headers.get("Content-Type", ""),
            }
            if callback is not None:
                callback(result)
            return result


try:
    from .client import NodeReverseClient
except ImportError:
    from pyspider.node_reverse.client import NodeReverseClient


class NodeReverseFetcher(Fetcher):
    """
    集成 Node.js 逆向能力的 Fetcher

    功能:
    1. 自动识别和响应中的加密数据
    2. 自动解密请求参数
    3. 分析JavaScript代码
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reverse_client = NodeReverseClient()

    def fetch(self, task, callback):
        """
        重写fetch方法，集成逆向能力
        """
        # 在请求前处理加密参数
        task = self._pre_process_task(task)

        # 执行正常fetch
        result = super().fetch(task, callback)

        # 后处理响应，分析加密
        if result and result.get("content"):
            result = self._post_process_response(result)

        return result

    def _pre_process_task(self, task):
        """预处理任务，处理加密参数"""
        try:
            # 检查是否有加密参数
            if "encrypt_params" in task.get("fetch", {}):
                encrypt_params = task["fetch"]["encrypt_params"]

                # 如果有加密数据，先解密
                if "encrypted_data" in encrypt_params:
                    decrypt_result = self.reverse_client.decrypt(
                        algorithm=encrypt_params.get("algorithm", "AES"),
                        data=encrypt_params["encrypted_data"],
                        key=encrypt_params.get("key", ""),
                        iv=encrypt_params.get("iv"),
                        mode=encrypt_params.get("mode"),
                    )

                    if decrypt_result.get("success"):
                        # 将解密后的数据添加到task中
                        decrypted = decrypt_result.get("decrypted")
                        if decrypted is not None:
                            task["decrypted_data"] = decrypted
        except Exception as e:
            print(f"NodeReverse: Pre-process failed: {e}")

        return task

    def _post_process_response(self, result):
        """后处理响应，分析加密"""
        try:
            content = result.get("content", "")
            headers = result.get("headers") or {}
            content_type = (
                headers.get("Content-Type")
                or headers.get("content-type")
                or result.get("content_type")
                or result.get("orig_url", "")
            )

            # 如果是JavaScript文件，分析代码
            if content_type.endswith(".js") or "javascript" in content_type:
                crypto_result = self.reverse_client.analyze_crypto(content)

                if crypto_result.get("success"):
                    # 将分析结果添加到响应中
                    result["crypto_analysis"] = crypto_result.get(
                        "analysis", crypto_result
                    )

            # 检查响应中是否包含加密数据
            if self._contains_encrypted_data(content):
                result["has_encrypted_data"] = True
        except Exception as e:
            print(f"NodeReverse: Post-process failed: {e}")

        return result

    def _contains_encrypted_data(self, content):
        """检查内容是否包含加密数据"""
        encrypted_patterns = [
            "encrypted",
            "ciphertext",
            "base64",
            "md5",
            "sha256",
            "aes",
        ]

        content_lower = content.lower()
        return any(pattern in content_lower for pattern in encrypted_patterns)

    def analyze_page_crypto(self, html_content):
        """分析页面中的加密算法"""
        return self.reverse_client.analyze_crypto(html_content)

    def extract_js_crypto(self, js_content):
        """提取JavaScript中的加密相关代码"""
        return self.reverse_client.analyze_ast(
            js_content, ["crypto", "obfuscation", "anti-debug"]
        )

    def decrypt_response_data(self, algorithm, data, key, iv=None, mode=None):
        """解密响应数据"""
        return self.reverse_client.decrypt(
            algorithm=algorithm, data=data, key=key, iv=iv, mode=mode
        )


# 使用示例
def create_node_reverse_fetcher():
    """创建集成逆向能力的fetcher"""
    return NodeReverseFetcher()


# 在pyspider中使用示例
"""
from pyspider import run
from pyspider.node_reverse.fetcher import create_node_reverse_fetcher

if __name__ == '__main__':
    fetcher = create_node_reverse_fetcher()
    run(fetcher=fetcher)
"""
