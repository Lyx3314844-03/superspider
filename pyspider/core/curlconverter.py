"""
curlconverter 集成模块
将 curl 命令转换为 Python requests 代码
"""

import json
import shlex
import subprocess
from typing import Optional


def curl_to_python(curl_command: str, indent: str = "    ") -> Optional[str]:
    """
    将 curl 命令转换为 Python requests 代码

    Args:
        curl_command: curl 命令字符串
        indent: 缩进字符串，默认为 4 个空格

    Returns:
        转换后的 Python 代码字符串，如果失败则返回 None
    """
    try:
        # 使用 curlconverter CLI 工具（Node.js 版本）
        return _curl_to_python_cli(curl_command)

    except Exception as e:
        print(f"转换失败: {e}")
        return None


def _curl_to_python_cli(curl_command: str) -> Optional[str]:
    """使用 curlconverter CLI 工具进行转换"""
    try:
        # 在 Windows 上使用 curlconverter.cmd
        import platform

        if platform.system() == "Windows":
            cmd = ["curlconverter.cmd", "--language", "python", "-"]
        else:
            cmd = ["curlconverter", "--language", "python", "-"]

        result = subprocess.run(
            cmd,
            input=curl_command,
            capture_output=True,
            text=True,
            timeout=30,
            shell=True,  # 在 Windows 上需要 shell=True
        )

        if result.returncode == 0:
            return result.stdout
        else:
            print(f"curlconverter CLI 错误: {result.stderr}")
            return None
    except Exception as e:
        print(f"执行 curlconverter CLI 失败: {e}")
        return None


def install_curlconverter():
    """安装 curlconverter 依赖"""
    print("正在安装 curlconverter...")

    # 安装 Node.js 版本
    try:
        subprocess.run(["npm", "install", "-g", "curlconverter"], check=True)
        print("✓ Node.js curlconverter 安装成功")
    except subprocess.CalledProcessError as e:
        print(f"✗ Node.js curlconverter 安装失败: {e}")


class CurlToPythonConverter:
    """curl 到 Python 转换器类"""

    def __init__(self):
        """初始化转换器"""
        pass

    def convert(self, curl_command: str, indent: str = "    ") -> Optional[str]:
        """
        转换 curl 命令为 Python 代码

        Args:
            curl_command: curl 命令字符串
            indent: 缩进字符串

        Returns:
            转换后的 Python 代码
        """
        return _curl_to_python_cli(curl_command)

    def convert_to_requests(self, curl_command: str, use_session: bool = False) -> str:
        """
        转换为使用 requests 库的代码

        Args:
            curl_command: curl 命令字符串
            use_session: 是否使用 Session 对象

        Returns:
            Python requests 代码
        """
        code = self.convert(curl_command)
        if not code:
            return "# 转换失败"

        if use_session and ("requests.get" in code or "requests.post" in code):
            # 添加 Session 支持
            session_code = "import requests\n\nsession = requests.Session()\n"
            # 简单的转换，实际使用时可能需要更复杂的解析
            code = session_code + code

        return code

    def convert_to_aiohttp(self, curl_command: str) -> str:
        """
        转换为使用 aiohttp 的代码（异步版本）

        Args:
            curl_command: curl 命令字符串

        Returns:
            Python aiohttp 代码
        """
        parsed = _parse_curl_command(curl_command)
        if not parsed:
            return f"""# 转换失败，请手动检查 curl 命令
# curl 命令: {curl_command}
"""

        method = parsed["method"]
        url = parsed["url"]
        headers = parsed["headers"]
        data = parsed["data"]

        header_block = ""
        request_headers = ""
        if headers:
            header_block = (
                f"    headers = {json.dumps(headers, ensure_ascii=False, indent=4)}\n"
            )
            request_headers = ", headers=headers"

        data_block = ""
        request_data = ""
        if data is not None:
            data_block = f"    data = {json.dumps(data, ensure_ascii=False)}\n"
            request_data = ", data=data"

        return f"""import aiohttp
import asyncio

async def fetch():
    async with aiohttp.ClientSession() as session:
{header_block}{data_block}        async with session.request(
            {method!r},
            {url!r}{request_headers}{request_data}
        ) as response:
            response.raise_for_status()
            text = await response.text()
            print(text)
            return text

if __name__ == "__main__":
    asyncio.run(fetch())
"""


def _parse_curl_command(curl_command: str) -> Optional[dict]:
    """解析常见 curl 命令子集，用于生成 aiohttp 代码。"""
    try:
        tokens = shlex.split(curl_command, posix=True)
    except ValueError:
        return None

    if not tokens:
        return None

    if tokens[0].lower() == "curl":
        tokens = tokens[1:]

    method = "GET"
    headers = {}
    data_parts = []
    url = None
    index = 0

    while index < len(tokens):
        token = tokens[index]
        if token in ("-X", "--request") and index + 1 < len(tokens):
            method = tokens[index + 1].upper()
            index += 2
            continue
        if token in ("-H", "--header") and index + 1 < len(tokens):
            raw_header = tokens[index + 1]
            if ":" in raw_header:
                key, value = raw_header.split(":", 1)
                headers[key.strip()] = value.strip()
            index += 2
            continue
        if token in (
            "-d",
            "--data",
            "--data-raw",
            "--data-binary",
            "--data-urlencode",
        ) and index + 1 < len(tokens):
            data_parts.append(tokens[index + 1])
            if method == "GET":
                method = "POST"
            index += 2
            continue
        if token.startswith("http://") or token.startswith("https://"):
            url = token
        index += 1

    if not url:
        return None

    data = "&".join(data_parts) if data_parts else None
    return {
        "method": method,
        "url": url,
        "headers": headers,
        "data": data,
    }


# 便捷函数
def curl_to_python_requests(curl_command: str) -> str:
    """快速将 curl 命令转换为 Python requests 代码"""
    converter = CurlToPythonConverter()
    result = converter.convert(curl_command)
    return result if result else "# 转换失败，请检查 curl 命令格式"


if __name__ == "__main__":
    # 测试示例
    test_curl = 'curl -X GET "https://httpbin.org/get" -H "Accept: application/json"'

    print("测试 curl 命令:")
    print(test_curl)
    print("\n转换后的 Python 代码:")
    print(curl_to_python_requests(test_curl))
