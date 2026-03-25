"""
HTTP 下载器
"""

import time
import requests
from typing import Optional, Dict
from pyspider.core.models import Request, Response


class HTTPDownloader:
    """HTTP 下载器"""
    
    def __init__(self, timeout: int = 30):
        self.session = requests.Session()
        self.timeout = timeout
    
    def download(self, req: Request) -> Response:
        """下载页面"""
        start_time = time.time()
        
        try:
            # 执行请求
            resp = self.session.request(
                method=req.method,
                url=req.url,
                headers=req.headers,
                data=req.body,
                timeout=self.timeout
            )
            
            duration = time.time() - start_time
            
            return Response(
                url=req.url,
                status_code=resp.status_code,
                headers=dict(resp.headers),
                content=resp.content,
                text=resp.text,
                request=req,
                duration=duration,
                error=None
            )
            
        except Exception as e:
            return Response(
                url=req.url,
                status_code=0,
                headers={},
                content=b'',
                text='',
                request=req,
                duration=time.time() - start_time,
                error=e
            )
    
    def set_timeout(self, timeout: int) -> None:
        """设置超时"""
        self.timeout = timeout
    
    def set_headers(self, headers: Dict[str, str]) -> None:
        """设置默认请求头"""
        self.session.headers.update(headers)
    
    def set_cookies(self, cookies: Dict[str, str]) -> None:
        """设置 Cookie"""
        self.session.cookies.update(cookies)
