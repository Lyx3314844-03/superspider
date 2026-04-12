"""
增强版 YouTube 播放列表爬虫
使用 pyspider 增强模块，包含反反爬虫功能

目标播放列表：https://www.youtube.com/watch?v=tr5yZ2TzXaY&list=PLRuPQZBVD6vV89UKIzUwZFUhDx9DjXLxc
"""

import sys

sys.path.insert(0, "C:/Users/Administrator/spider")

from enhanced.enhancements import (
    EnhancedSpider,
    UserAgentRotator,
    AntiBot,
    DataExporter,
    RetryHandler,
    Proxy,
)
from pyspider.browser.browser import PlaywrightManager
from pyspider.parser.parser import HTMLParser
import time
import json
from datetime import datetime
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class VideoInfo:
    """视频信息"""

    title: str
    duration: str = ""
    channel: str = ""
    url: str = ""
    thumbnail: str = ""
    views: str = ""
    published: str = ""

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "duration": self.duration,
            "channel": self.channel,
            "url": self.url,
            "thumbnail": self.thumbnail,
            "views": self.views,
            "published": self.published,
        }


class YouTubePlaylistSpider(EnhancedSpider):
    """YouTube 播放列表爬虫"""

    def __init__(self, playlist_url, headless=True):
        super().__init__(name="YouTubePlaylistSpider", use_retry=True)
        self.playlist_url = playlist_url
        self.headless = headless
        self.browser = None
        self.videos: List[VideoInfo] = []

    def start(self) -> List[VideoInfo]:
        """启动爬虫"""
        self._print_header()

        try:
            # 初始化浏览器
            self._init_browser()

            # 导航到页面
            self._navigate_to_playlist()

            # 滚动加载
            self._scroll_to_load()

            # 获取并解析内容
            html = self._get_html()
            self._parse_videos(html)

            # 输出结果
            self._print_results()
            self._export_results()
            self._print_stats()

            return self.videos

        except Exception as e:
            print(f"\n❌ 爬取失败：{e}")
            import traceback

            traceback.print_exc()
            return []

        finally:
            self._close_browser()

    def _print_header(self):
        """打印头部"""
        print("\n" + "╔" * 30 + "╗")
        print("║" * 15 + " YouTube 播放列表爬虫 " + "║" * 15)
        print("║" * 12 + "  增强版 (带反反爬虫)  " + "║" * 12)
        print("╚" * 30 + "╝")
        print(f"\n📺 播放列表：{self.playlist_url}\n")

    def _init_browser(self):
        """初始化浏览器"""
        print("🚀 启动浏览器 (Playwright)...")
        self.browser = PlaywrightManager(headless=self.headless)
        print("   ✓ 浏览器已启动")

    def _navigate_to_playlist(self):
        """导航到播放列表"""
        print("🌐 正在加载播放列表页面...")

        # 使用隐身请求头
        self.browser.page.set_extra_http_headers(AntiBot.get_stealth_headers())

        self.browser.navigate(self.playlist_url)

        # 等待初始加载
        print("   ⏳ 等待页面加载...")
        time.sleep(5)

        # 检查是否需要验证
        html = self.browser.get_html()
        if "just a moment" in html.lower() or "checking your browser" in html.lower():
            print("   ⚠️  检测到验证页面，等待绕过...")
            AntiBot.bypass_cloudflare(self.browser, timeout=30)

        print("   ✓ 页面已加载")

    def _scroll_to_load(self):
        """滚动加载所有视频"""
        print("📜 滚动加载所有视频...")

        # 使用人类行为模拟滚动
        AntiBot.human_like_scroll(self.browser, scroll_times=8, scroll_pause=1.5)

        # 额外等待
        time.sleep(AntiBot.generate_random_delay(2, 4))
        print("   ✓ 滚动完成")

    def _get_html(self) -> str:
        """获取 HTML"""
        print("📄 获取页面内容...")
        html = self.browser.get_html()

        # 保存 HTML 用于调试
        with open("youtube_playlist_source.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("   ✓ HTML 已保存到：youtube_playlist_source.html")

        return html

    def _parse_videos(self, html: str):
        """解析视频列表"""
        print("🔍 解析视频信息...")

        parser = HTMLParser(html)
        seen_titles = set()

        # 方法 1: 使用 ytd-playlist-video-renderer
        video_elements = parser.css("ytd-playlist-video-renderer")
        print(f"   找到 {len(video_elements)} 个视频元素")

        for elem in video_elements:
            try:
                video = self._extract_video_from_element(elem, parser)
                if video and video.title not in seen_titles:
                    seen_titles.add(video.title)
                    self.videos.append(video)
            except Exception as e:
                continue

        # 方法 2: 备用解析
        if len(self.videos) == 0:
            print("   使用备用解析方法...")
            self._parse_with_backup(parser, seen_titles)

        # 方法 3: 从 JSON 数据中提取
        if len(self.videos) == 0:
            print("   尝试从 JSON 数据提取...")
            self._parse_from_json(html, seen_titles)

        print(f"   ✓ 共解析 {len(self.videos)} 个视频")

    def _extract_video_from_element(self, elem, parser: HTMLParser) -> VideoInfo:
        """从元素提取视频信息"""
        video = VideoInfo(title="")

        # 标题
        title_elem = elem.querySelector("#video-title")
        if title_elem:
            video.title = title_elem.text.strip()
            video.url = title_elem.get_attribute("href", "")

        # 时长
        duration_elem = elem.querySelector(
            "span.ytd-thumbnail-overlay-time-status-renderer"
        )
        if duration_elem:
            video.duration = duration_elem.text.strip()

        # 频道
        channel_elem = elem.querySelector("#channel-name #text")
        if channel_elem:
            video.channel = channel_elem.text.strip()

        # 缩略图
        thumb_elem = elem.querySelector("img#thumbnail")
        if thumb_elem:
            video.thumbnail = thumb_elem.get_attribute("src", "")

        return video

    def _parse_with_backup(self, parser: HTMLParser, seen_titles: set):
        """备用解析方法"""
        titles = parser.css("a#video-title")
        for title in titles:
            if title and title not in seen_titles:
                seen_titles.add(title)
                self.videos.append(VideoInfo(title=title))

    def _parse_from_json(self, html: str, seen_titles: set):
        """从 JSON 数据解析"""
        import re

        # 查找 ytInitialData
        match = re.search(r"var ytInitialData\s*=\s*({.+?});", html)
        if match:
            try:
                data = json.loads(match.group(1))
                contents = data.get("contents", {})

                # 遍历播放列表内容
                self._extract_from_json_contents(contents, seen_titles)
            except:
                pass

    def _extract_from_json_contents(self, contents: Dict, seen_titles: set):
        """从 JSON 内容提取"""
        # 这里可以添加更深入的 JSON 解析逻辑
        pass

    def _print_results(self):
        """打印结果"""
        print("\n" + "═" * 60)
        print(" " * 20 + "爬取结果")
        print("═" * 60)
        print(f"共找到 {len(self.videos)} 个视频\n")

        for i, video in enumerate(self.videos[:20]):  # 只显示前 20 个
            print(f"{i+1:2d}. {video.title}")
            if video.duration:
                print(f"    ⏱️  时长：{video.duration}")
            if video.channel:
                print(f"    👤  频道：{video.channel}")
            print()

        if len(self.videos) > 20:
            print(f"... 还有 {len(self.videos) - 20} 个视频 (见导出文件)")

    def _export_results(self):
        """导出结果"""
        print("\n💾 导出结果...")

        # 转换为字典列表
        data = [v.to_dict() for v in self.videos]

        # 导出为多种格式
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        DataExporter.to_json(data, f"youtube_playlist_{timestamp}.json")
        DataExporter.to_csv(data, f"youtube_playlist_{timestamp}.csv")
        DataExporter.to_txt(data, f"youtube_playlist_{timestamp}.txt")

    def _print_stats(self):
        """打印统计信息"""
        self.print_stats()

    def _close_browser(self):
        """关闭浏览器"""
        if self.browser:
            print("\n🔒 关闭浏览器...")
            self.browser.close()
            print("   ✓ 浏览器已关闭")


def main():
    """主函数"""
    playlist_url = "https://www.youtube.com/watch?v=tr5yZ2TzXaY&list=PLRuPQZBVD6vV89UKIzUwZFUhDx9DjXLxc"

    # 创建爬虫
    spider = YouTubePlaylistSpider(playlist_url, headless=True)

    # 可选：添加代理
    # spider.add_proxy("proxy.example.com", 8080)

    # 开始爬取
    videos = spider.start()

    if videos:
        print("\n✅ 爬取完成!")
    else:
        print("\n⚠️  未找到视频，可能是页面结构变化或需要登录。")


if __name__ == "__main__":
    main()
