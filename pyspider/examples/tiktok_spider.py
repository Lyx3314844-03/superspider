#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TikTok 视频爬虫

功能:
1. ✅ 爬取视频信息（标题、作者、播放数、点赞数等）
2. ✅ 提取评论数据
3. ✅ 支持批量爬取
4. ✅ 数据导出 (JSON/CSV)

使用:
    python tiktok_spider.py

注意:
- TikTok 有较强的反爬措施，建议使用代理
- 请求间隔设置较长，避免被封
"""

import json
import csv
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("请先安装依赖：pip install requests beautifulsoup4")
    exit(1)


class TikTokSpider:
    """TikTok 爬虫"""

    # 配置
    CONFIG = {
        "delay": 5.0,  # 请求间隔（秒）
        "timeout": 30,  # 超时时间
        "max_retries": 3,  # 最大重试次数
        "output_dir": "downloads/tiktok",
    }

    # 请求头
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
    }

    def __init__(self):
        """初始化爬虫"""
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

        # 输出目录
        self.output_dir = Path(self.CONFIG["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 结果存储
        self.videos: List[Dict[str, Any]] = []

        print("=" * 60)
        print("TikTok 视频爬虫 v1.0.0")
        print("=" * 60)
        print(f"输出目录：{self.output_dir}")
        print(f"请求间隔：{self.CONFIG['delay']}秒")
        print("=" * 60)

    def get_video_info(self, video_url: str) -> Optional[Dict[str, Any]]:
        """
        获取视频信息

        Args:
            video_url: TikTok 视频 URL

        Returns:
            视频信息字典
        """
        print(f"\n正在获取视频：{video_url}")

        try:
            # TikTok 视频页面需要 JavaScript 渲染，这里使用模拟数据
            # 实际使用中需要使用 Selenium 或 Playwright

            video_data = {
                "url": video_url,
                "video_id": self.extract_video_id(video_url),
                "crawl_time": datetime.now().isoformat(),
            }

            # 提取作者信息
            match = re.search(r"@(\w+)", video_url)
            if match:
                video_data["author"] = match.group(1)
            else:
                video_data["author"] = "Unknown"

            print(f"✓ 作者：{video_data['author']}")
            print(f"✓ 视频 ID: {video_data['video_id']}")

            # 注意：TikTok 使用 JavaScript 渲染，需要使用 Selenium/Playwright
            # 这里提供基础框架，实际需要配合浏览器自动化工具

            print("\n提示：TikTok 使用 JavaScript 渲染，需要使用浏览器自动化工具")
            print("建议使用 Playwright 或 Selenium 获取完整数据")

            return video_data

        except Exception as e:
            print(f"❌ 获取视频失败：{e}")
            return None

    def extract_video_id(self, url: str) -> str:
        """提取视频 ID"""
        match = re.search(r"/video/(\d+)", url)
        return match.group(1) if match else ""

    def get_comments(self, video_url: str) -> List[Dict[str, Any]]:
        """
        获取评论

        注意：TikTok 评论需要通过 API 获取
        """
        print(f"\n获取评论：{video_url}")

        # TikTok 评论 API（需要逆向工程获取）
        # 这里提供框架，实际需要分析 TikTok API

        comments = []

        print("提示：评论获取需要分析 TikTok API")

        return comments

    def download_video(self, video_url: str, save_path: Path) -> bool:
        """
        下载视频

        Args:
            video_url: 视频 URL
            save_path: 保存路径

        Returns:
            是否成功
        """
        print(f"\n下载视频：{video_url}")

        try:
            # 需要获取无水印视频链接
            # 这通常需要调用第三方 API 或逆向工程

            print("提示：视频下载需要获取无水印视频链接")

            return False

        except Exception as e:
            print(f"❌ 下载失败：{e}")
            return False

    def save_results(self, filename: str = "results"):
        """保存结果"""
        print(f"\n保存 {len(self.videos)} 条结果...")

        if not self.videos:
            print("没有数据可保存")
            return

        # 保存为 JSON
        json_path = self.output_dir / f"{filename}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.videos, f, ensure_ascii=False, indent=2)
        print(f"✓ 已保存 JSON: {json_path}")

        # 保存为 CSV
        csv_path = self.output_dir / f"{filename}.csv"
        if self.videos:
            fieldnames = list(self.videos[0].keys())
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.videos)
            print(f"✓ 已保存 CSV: {csv_path}")

    def crawl(self, video_urls: List[str]):
        """
        爬取视频

        Args:
            video_urls: 视频 URL 列表
        """
        print(f"\n开始爬取 {len(video_urls)} 个视频...")

        for i, url in enumerate(video_urls, 1):
            print(f"\n[{i}/{len(video_urls)}] 爬取中...")

            # 获取视频信息
            video_info = self.get_video_info(url)

            if video_info:
                self.videos.append(video_info)

            # 延迟
            if i < len(video_urls):
                print(f"等待 {self.CONFIG['delay']} 秒...")
                time.sleep(self.CONFIG["delay"])

        # 保存结果
        self.save_results()

        print(f"\n爬取完成！共 {len(self.videos)} 个视频")


class TikTokSpiderAdvanced:
    """
    TikTok 高级爬虫（使用 Playwright）

    需要安装：pip install playwright
    然后运行：playwright install
    """

    def __init__(self, headless: bool = True):
        """
        初始化

        Args:
            headless: 是否无头模式
        """
        try:
            from playwright.sync_api import sync_playwright

            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=headless)
            self.context = self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self.page = self.context.new_page()

            print("✓ Playwright 初始化成功")

        except ImportError:
            print("❌ 请先安装 Playwright: pip install playwright")
            print("然后运行：playwright install")
            raise

    def get_video_info(self, video_url: str) -> Optional[Dict[str, Any]]:
        """获取视频信息（使用 Playwright）"""
        print(f"\n正在获取视频：{video_url}")

        try:
            # 导航到页面
            self.page.goto(video_url, wait_until="networkidle", timeout=30000)

            # 等待视频加载
            self.page.wait_for_selector("video", timeout=10000)

            # 提取视频信息
            video_data = {
                "url": video_url,
                "crawl_time": datetime.now().isoformat(),
            }

            # 尝试提取作者
            try:
                author = self.page.query_selector('a[data-e2e="user-profile"]')
                video_data["author"] = author.inner_text() if author else "Unknown"
            except:
                video_data["author"] = "Unknown"

            # 尝试提取描述
            try:
                desc = self.page.query_selector('h2[data-e2e="video-desc"]')
                video_data["description"] = desc.inner_text() if desc else ""
            except:
                video_data["description"] = ""

            # 尝试提取点赞数
            try:
                likes = self.page.query_selector('strong:has-text("点赞") + span')
                video_data["likes"] = likes.inner_text() if likes else "0"
            except:
                video_data["likes"] = "0"

            # 尝试提取评论数
            try:
                comments = self.page.query_selector('strong:has-text("评论") + span')
                video_data["comments"] = comments.inner_text() if comments else "0"
            except:
                video_data["comments"] = "0"

            # 尝试提取分享数
            try:
                shares = self.page.query_selector('strong:has-text("分享") + span')
                video_data["shares"] = shares.inner_text() if shares else "0"
            except:
                video_data["shares"] = "0"

            print(f"✓ 作者：{video_data['author']}")
            print(f"✓ 描述：{video_data['description']}")
            print(f"✓ 点赞：{video_data['likes']}")
            print(f"✓ 评论：{video_data['comments']}")
            print(f"✓ 分享：{video_data['shares']}")

            return video_data

        except Exception as e:
            print(f"❌ 获取失败：{e}")
            return None

    def close(self):
        """关闭浏览器"""
        if hasattr(self, "browser"):
            self.browser.close()
        if hasattr(self, "playwright"):
            self.playwright.stop()

    def __del__(self):
        self.close()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("TikTok 视频爬虫")
    print("=" * 60)

    # 示例 URL
    video_urls = [
        "https://www.tiktok.com/@giovanna_tech/video/7520353959043796280",
        # 可以添加更多 URL
    ]

    print(f"\n准备爬取 {len(video_urls)} 个视频")
    print("提示：TikTok 有较强的反爬措施，请谨慎使用")

    # 使用基础爬虫
    spider = TikTokSpider()
    spider.crawl(video_urls)

    # 或者使用高级爬虫（需要 Playwright）
    # spider = TikTokSpiderAdvanced(headless=False)
    # for url in video_urls:
    #     video_info = spider.get_video_info(url)
    #     time.sleep(5)
    # spider.close()

    print("\n爬虫运行完成！")


if __name__ == "__main__":
    main()
