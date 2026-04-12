"""
媒体下载模块
支持 HLS/DASH/普通文件下载
"""

import asyncio
import aiohttp
import aiofiles
import os
import re
from typing import List, Optional


class MediaDownloader:
    """通用媒体下载器"""

    def __init__(self, output_dir: str = "./downloads"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    async def download_file(
        self, url: str, filename: Optional[str] = None, headers: Optional[dict] = None
    ) -> str:
        """下载单个文件"""
        if filename is None:
            filename = url.split("/")[-1] or "unknown"

        # 修复：清理文件名，防止路径遍历攻击
        filename = re.sub(r"[^\w\.\-]", "_", filename)
        output_path = os.path.join(self.output_dir, filename)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    # 修复：使用异步文件 I/O，不阻塞事件循环
                    async with aiofiles.open(output_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    return output_path
                else:
                    raise Exception(f"Failed to download: {response.status}")

    async def batch_download(self, urls: List[str], max_concurrent: int = 5) -> dict:
        """批量并发下载"""
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}

        async def _download_with_semaphore(url):
            async with semaphore:
                try:
                    path = await self.download_file(url)
                    return url, path
                except Exception as e:
                    return url, str(e)

        tasks = [_download_with_semaphore(url) for url in urls]
        completed = await asyncio.gather(*tasks)

        for url, result in completed:
            results[url] = result

        return results

    async def download_images(
        self, image_urls: List[str], max_concurrent: int = 5
    ) -> dict:
        """批量下载图片"""
        return await self.batch_download(image_urls, max_concurrent)

    async def download_videos(
        self, video_urls: List[str], max_concurrent: int = 2
    ) -> dict:
        """批量下载视频"""
        return await self.batch_download(video_urls, max_concurrent)

    async def download_audio(
        self, audio_urls: List[str], max_concurrent: int = 3
    ) -> dict:
        """批量下载音频"""
        return await self.batch_download(audio_urls, max_concurrent)

    def get_downloaded_files(self) -> List[str]:
        """获取已下载文件列表"""
        return os.listdir(self.output_dir)

    def clear_downloads(self):
        """清空下载目录"""
        import shutil

        for f in os.listdir(self.output_dir):
            file_path = os.path.join(self.output_dir, f)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
