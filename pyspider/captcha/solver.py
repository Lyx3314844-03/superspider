"""
验证码识别模块
支持多种验证码识别服务
"""

import base64
import requests
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class SolveResult:
    """解决结果"""

    success: bool
    text: Optional[str] = None
    error: Optional[str] = None


class CaptchaSolver:
    """验证码解决器"""

    def __init__(self, api_key: str, service: str = "2captcha"):
        self.api_key = api_key
        self.service = self._normalize_service(service)
        self.timeout = 30
        self.session = requests.Session()

    @staticmethod
    def _normalize_service(service: str) -> str:
        normalized = (service or "2captcha").strip().lower().replace("_", "").replace("-", "")
        if normalized in {"2captcha", "twocaptcha"}:
            return "2captcha"
        if normalized == "anticaptcha":
            return "anticaptcha"
        if normalized == "capmonster":
            return "capmonster"
        return normalized or "2captcha"

    def solve_image(self, image_data: bytes) -> SolveResult:
        """解决图片验证码

        Args:
            image_data: 图片数据

        Returns:
            SolveResult: 解决结果
        """
        if self.service == "2captcha":
            return self._solve_2captcha(image_data)
        elif self.service == "anticaptcha":
            return self._solve_anticaptcha(image_data)
        elif self.service == "capmonster":
            return self._solve_capmonster(image_data)
        else:
            return self._solve_2captcha(image_data)

    def _solve_2captcha(self, image_data: bytes) -> SolveResult:
        """使用 2Captcha 解决"""
        # 上传图片
        base64_image = base64.b64encode(image_data).decode()

        resp = self.session.post(
            "http://2captcha.com/in.php",
            data={
                "key": self.api_key,
                "method": "base64",
                "body": base64_image,
            },
            timeout=self.timeout,
        )

        result = resp.text.split("|")
        if result[0] != "OK":
            return SolveResult(success=False, error=result[0])

        task_id = result[1]

        # 轮询获取结果
        for _ in range(30):
            time.sleep(2)

            resp = self.session.get(
                "http://2captcha.com/res.php",
                params={
                    "key": self.api_key,
                    "action": "get",
                    "id": task_id,
                },
                timeout=self.timeout,
            )

            result = resp.text.split("|")

            if result[0] == "OK":
                return SolveResult(success=True, text=result[1])

            if result[0] != "CAPCHA_NOT_READY":
                return SolveResult(success=False, error=result[0])

        return SolveResult(success=False, error="Timeout")

    def _solve_anticaptcha(self, image_data: bytes) -> SolveResult:
        """使用 Anti-Captcha 解决"""
        base64_image = base64.b64encode(image_data).decode()

        # 创建任务
        resp = self.session.post(
            "https://api.anti-captcha.com/createTask",
            json={
                "clientKey": self.api_key,
                "task": {
                    "type": "ImageToTextTask",
                    "body": base64_image,
                },
            },
            timeout=self.timeout,
        )

        result = resp.json()

        if result.get("errorId") != 0:
            return SolveResult(
                success=False,
                error=result.get("errorDescription"),
            )

        task_id = result["taskId"]

        # 轮询获取结果
        for _ in range(30):
            time.sleep(2)

            resp = self.session.post(
                "https://api.anti-captcha.com/getTaskResult",
                json={
                    "clientKey": self.api_key,
                    "taskId": task_id,
                },
                timeout=self.timeout,
            )

            result = resp.json()

            if result.get("status") == "ready":
                return SolveResult(
                    success=True,
                    text=result["solution"]["text"],
                )

        return SolveResult(success=False, error="Timeout")

    def solve_recaptcha(self, site_key: str, page_url: str) -> SolveResult:
        """解决 reCAPTCHA

        Args:
            site_key: 站点密钥
            page_url: 页面 URL
        """
        if not self.api_key and self.service != "capmonster":
            return SolveResult(success=False, error="API key is required")
        if not site_key or not page_url:
            return SolveResult(success=False, error="site_key and page_url are required")

        if self.service == "anticaptcha":
            return self._solve_anticaptcha_site_challenge(
                task_type="NoCaptchaTaskProxyless",
                site_key=site_key,
                page_url=page_url,
                response_field="gRecaptchaResponse",
            )
        if self.service == "capmonster":
            return self._solve_capmonster_site_challenge(
                task_type="NoCaptchaTaskProxyless",
                site_key=site_key,
                page_url=page_url,
                response_field="gRecaptchaResponse",
            )

        return self._solve_2captcha_site_challenge(
            method="userrecaptcha",
            site_key=site_key,
            page_url=page_url,
        )

    def solve_hcaptcha(self, site_key: str, page_url: str) -> SolveResult:
        """解决 hCaptcha

        Args:
            site_key: 站点密钥
            page_url: 页面 URL
        """
        if not self.api_key and self.service != "capmonster":
            return SolveResult(success=False, error="API key is required")
        if not site_key or not page_url:
            return SolveResult(success=False, error="site_key and page_url are required")

        if self.service == "anticaptcha":
            return self._solve_anticaptcha_site_challenge(
                task_type="HCaptchaTaskProxyless",
                site_key=site_key,
                page_url=page_url,
                response_field="gRecaptchaResponse",
            )
        if self.service == "capmonster":
            return self._solve_capmonster_site_challenge(
                task_type="HCaptchaTaskProxyless",
                site_key=site_key,
                page_url=page_url,
                response_field="gRecaptchaResponse",
            )

        return self._solve_2captcha_site_challenge(
            method="hcaptcha",
            site_key=site_key,
            page_url=page_url,
        )

    def solve_turnstile(
        self,
        site_key: str,
        page_url: str,
        *,
        action: str = "",
        c_data: str = "",
        page_data: str = "",
    ) -> SolveResult:
        """解决 Cloudflare Turnstile"""
        if not self.api_key and self.service != "capmonster":
            return SolveResult(success=False, error="API key is required")
        if not site_key or not page_url:
            return SolveResult(success=False, error="site_key and page_url are required")

        if self.service == "anticaptcha":
            return self._solve_anticaptcha_site_challenge(
                task_type="TurnstileTaskProxyless",
                site_key=site_key,
                page_url=page_url,
                response_field="token",
                action=action,
                c_data=c_data,
                page_data=page_data,
            )
        if self.service == "capmonster":
            return self._solve_capmonster_site_challenge(
                task_type="TurnstileTaskProxyless",
                site_key=site_key,
                page_url=page_url,
                response_field="token",
                action=action,
                c_data=c_data,
                page_data=page_data,
            )

        return self._solve_2captcha_site_challenge(
            method="turnstile",
            site_key=site_key,
            page_url=page_url,
            action=action,
            c_data=c_data,
            page_data=page_data,
        )

    def report_bad(self, task_id: str) -> None:
        """报告错误的识别结果"""
        # 实现报告错误识别
        pass

    def _solve_2captcha_site_challenge(
        self,
        method: str,
        site_key: str,
        page_url: str,
        *,
        action: str = "",
        c_data: str = "",
        page_data: str = "",
    ) -> SolveResult:
        payload = {
            "key": self.api_key,
            "method": method,
            "pageurl": page_url,
        }
        if method == "userrecaptcha":
            payload["googlekey"] = site_key
        else:
            payload["sitekey"] = site_key
        if action:
            payload["action"] = action
        if c_data:
            payload["data"] = c_data
        if page_data:
            payload["pagedata"] = page_data

        resp = self.session.post(
            "http://2captcha.com/in.php",
            data=payload,
            timeout=self.timeout,
        )

        result = resp.text.split("|")
        if result[0] != "OK":
            return SolveResult(success=False, error=result[0])

        task_id = result[1]
        for _ in range(30):
            time.sleep(2)
            resp = self.session.get(
                "http://2captcha.com/res.php",
                params={
                    "key": self.api_key,
                    "action": "get",
                    "id": task_id,
                },
                timeout=self.timeout,
            )
            result = resp.text.split("|")
            if result[0] == "OK":
                return SolveResult(success=True, text=result[1])
            if result[0] != "CAPCHA_NOT_READY":
                return SolveResult(success=False, error=result[0])

        return SolveResult(success=False, error="Timeout")

    def _solve_capmonster(self, image_data: bytes) -> SolveResult:
        """使用 CapMonster 解决"""
        base64_image = base64.b64encode(image_data).decode()

        resp = self.session.post(
            "http://localhost:24999/createTask",
            json={
                "task": {
                    "type": "ImageToTextTask",
                    "body": base64_image,
                },
            },
            timeout=self.timeout,
        )

        result = resp.json()
        if result.get("errorId") not in (None, 0):
            return SolveResult(success=False, error=result.get("errorDescription"))

        task_id = result.get("taskId")
        if not task_id:
            return SolveResult(success=False, error="Missing taskId")

        for _ in range(30):
            time.sleep(2)

            resp = self.session.post(
                "http://localhost:24999/getTaskResult",
                json={
                    "taskId": task_id,
                },
                timeout=self.timeout,
            )

            result = resp.json()

            if result.get("status") == "ready":
                solution = result.get("solution") or {}
                text = solution.get("text")
                if text:
                    return SolveResult(success=True, text=text)
                return SolveResult(success=False, error="Missing solution text")

        return SolveResult(success=False, error="Timeout")

    def _solve_anticaptcha_site_challenge(
        self,
        task_type: str,
        site_key: str,
        page_url: str,
        response_field: str,
        *,
        action: str = "",
        c_data: str = "",
        page_data: str = "",
    ) -> SolveResult:
        task: dict[str, Any] = {
            "type": task_type,
            "websiteURL": page_url,
            "websiteKey": site_key,
        }
        if action:
            task["action"] = action
        if c_data:
            task["cData"] = c_data
        if page_data:
            task["chlPageData"] = page_data

        resp = self.session.post(
            "https://api.anti-captcha.com/createTask",
            json={
                "clientKey": self.api_key,
                "task": task,
            },
            timeout=self.timeout,
        )

        result = resp.json()
        if result.get("errorId") != 0:
            return SolveResult(
                success=False,
                error=result.get("errorDescription"),
            )

        task_id = result["taskId"]
        for _ in range(30):
            time.sleep(2)
            resp = self.session.post(
                "https://api.anti-captcha.com/getTaskResult",
                json={
                    "clientKey": self.api_key,
                    "taskId": task_id,
                },
                timeout=self.timeout,
            )
            result = resp.json()
            if result.get("errorId") not in (None, 0):
                return SolveResult(
                    success=False,
                    error=result.get("errorDescription"),
                )
            if result.get("status") == "ready":
                token = (result.get("solution") or {}).get(response_field)
                if token:
                    return SolveResult(success=True, text=token)
                return SolveResult(success=False, error="Missing solution token")

        return SolveResult(success=False, error="Timeout")

    def _solve_capmonster_site_challenge(
        self,
        task_type: str,
        site_key: str,
        page_url: str,
        response_field: str,
        *,
        action: str = "",
        c_data: str = "",
        page_data: str = "",
    ) -> SolveResult:
        task: dict[str, Any] = {
            "type": task_type,
            "websiteURL": page_url,
            "websiteKey": site_key,
        }
        if action:
            task["action"] = action
        if c_data:
            task["cData"] = c_data
        if page_data:
            task["chlPageData"] = page_data

        resp = self.session.post(
            "http://localhost:24999/createTask",
            json={
                "task": task,
            },
            timeout=self.timeout,
        )

        result = resp.json()
        if result.get("errorId") not in (None, 0):
            return SolveResult(
                success=False,
                error=result.get("errorDescription"),
            )

        task_id = result.get("taskId")
        if not task_id:
            return SolveResult(success=False, error="Missing taskId")

        for _ in range(30):
            time.sleep(2)
            resp = self.session.post(
                "http://localhost:24999/getTaskResult",
                json={
                    "taskId": task_id,
                },
                timeout=self.timeout,
            )
            result = resp.json()
            if result.get("errorId") not in (None, 0):
                return SolveResult(
                    success=False,
                    error=result.get("errorDescription"),
                )
            if result.get("status") == "ready":
                token = (result.get("solution") or {}).get(response_field)
                if token:
                    return SolveResult(success=True, text=token)
                return SolveResult(success=False, error="Missing solution token")

        return SolveResult(success=False, error="Timeout")


class CloudflareBypass:
    """Cloudflare 绕过器"""

    def __init__(self):
        self.session = requests.Session()

    def get_token(self, url: str) -> Optional[str]:
        """获取 Cloudflare 令牌"""
        # 实现 Cloudflare 绕过逻辑
        return None

    def solve_challenge(self, html: str) -> Optional[str]:
        """解决 Cloudflare 挑战"""
        # 解析 JavaScript 挑战
        return None


class AkamaiBypass:
    """Akamai 绕过器"""

    def __init__(self):
        self.session = requests.Session()

    def get_sensor_data(self, url: str) -> Optional[Dict[str, str]]:
        """获取 Akamai sensor 数据"""
        # 实现 Akamai 绕过逻辑
        return None
