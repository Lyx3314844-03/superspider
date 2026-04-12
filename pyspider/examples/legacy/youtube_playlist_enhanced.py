"""
pyspider YouTube 播放列表爬虫 - 增强版
使用统一的爬虫基类，支持多种输出格式

目标播放列表：https://www.youtube.com/watch?v=tr5yZ2TzXaY&list=PLRuPQZBVD6vV89UKIzUwZFUhDx9DjXLxc
"""

import sys

sys.path.insert(0, "C:/Users/Administrator/spider")

from pyspider.browser.browser import PlaywrightManager
from pyspider.parser.parser import HTMLParser
from pyspider.enhanced.youtube_spider_base import YouTubeSpiderBase, VideoItem
import time
import re
import json


class YouTubePlaylistSpider(YouTubeSpiderBase):
    """YouTube 播放列表爬虫"""

    def __init__(self, playlist_url, headless=True):
        super().__init__(playlist_url)
        self.platform = "Python/pyspider"
        self.headless = headless
        self.browser = None

    def _initialize(self):
        """初始化浏览器"""
        print("🚀 启动浏览器 (Playwright)...")
        self.browser = PlaywrightManager(headless=self.headless)
        print("   ✓ 浏览器已启动")

    def _navigate(self):
        """导航到播放列表"""
        print("🌐 正在加载播放列表页面...")
        self.browser.navigate(self.playlist_url)

        # 等待初始加载
        print("   ⏳ 等待页面加载...")
        time.sleep(5)

        # 检查是否需要验证
        html = self.browser.get_html()
        if "just a moment" in html.lower():
            print("   ⚠️  检测到验证页面，等待绕过...")
            time.sleep(10)

        print("   ✓ 页面已加载")

    def _wait_and_scroll(self):
        """滚动加载所有视频"""
        print("📜 滚动加载所有视频...")

        for i in range(10):
            # 滚动到底部
            self.browser.execute_script(
                "window.scrollTo(0, document.body.scrollHeight)"
            )
            time.sleep(1)

            # 滚动回顶部
            self.browser.execute_script("window.scrollTo(0, 0)")
            time.sleep(0.5)

            print(f"   滚动 {i+1}/10")

        # 额外等待
        time.sleep(2)
        print("   ✓ 滚动完成")

    def _extract_content(self):
        """获取页面 HTML"""
        print("📄 获取页面内容...")
        self.html = self.browser.get_html()

        # 保存 HTML 用于调试
        with open("youtube_playlist_source.html", "w", encoding="utf-8") as f:
            f.write(self.html)
        print("   ✓ HTML 已保存到：youtube_playlist_source.html")

    def _parse_videos(self):
        """解析视频列表"""
        print("🔍 解析视频信息...")

        # 方法 1: 正则解析
        self.videos = self._parse_with_regex()

        # 方法 2: 如果正则失败，尝试 JavaScript
        if len(self.videos) == 0:
            print("   尝试使用 JavaScript 提取...")
            self.videos = self._extract_with_js()

        # 方法 3: 从 JSON 解析
        if len(self.videos) == 0:
            print("   尝试从 JSON 数据解析...")
            self.videos = self._parse_from_json()

        print(f"   ✓ 共解析 {len(self.videos)} 个视频")

    def _parse_with_regex(self) -> list:
        """使用正则解析"""
        videos = []
        seen_titles = set()

        # 查找所有视频项
        pattern = r"<ytd-playlist-panel-video-renderer[^>]*>.*?</ytd-playlist-panel-video-renderer>"
        video_elements = re.findall(pattern, self.html, re.DOTALL)

        print(f"   找到 {len(video_elements)} 个视频元素")

        for i, video_elem in enumerate(video_elements):
            try:
                video = VideoItem()

                # 提取标题
                title_match = re.search(
                    r'id="video-title"[^>]*>([^<]+)</span>', video_elem
                )
                if title_match:
                    video.title = title_match.group(1).strip()

                # 提取 URL
                url_match = re.search(r'href="([^"]*watch\?v=[^"]*)"', video_elem)
                if url_match:
                    video.url = url_match.group(1).replace("&amp;", "&")

                # 提取频道
                channel_match = re.search(
                    r'id="byline"[^>]*>([^<]+)</span>', video_elem
                )
                if channel_match:
                    video.channel = channel_match.group(1).strip()

                # 跳过重复或空标题
                if not video.title or video.title in seen_titles:
                    continue
                seen_titles.add(video.title)

                video.index = len(videos) + 1
                videos.append(video)

            except Exception as e:
                continue

        return videos

    def _extract_with_js(self) -> list:
        """使用 JavaScript 提取"""
        videos = []

        try:
            js_code = """
            () => {
                const videos = [];
                const videoElements = document.querySelectorAll('ytd-playlist-panel-video-renderer');
                
                videoElements.forEach((elem, index) => {
                    const titleElem = elem.querySelector('#video-title');
                    const urlElem = elem.querySelector('a#wc-endpoint');
                    const durationElem = elem.querySelector('span.ytd-thumbnail-overlay-time-status-renderer');
                    const channelElem = elem.querySelector('#byline');
                    
                    if (titleElem || urlElem) {
                        videos.push({
                            index: index + 1,
                            title: titleElem ? titleElem.textContent.trim() : '',
                            url: urlElem ? urlElem.href : '',
                            duration: durationElem ? durationElem.textContent.trim() : '',
                            channel: channelElem ? channelElem.textContent.trim() : ''
                        });
                    }
                });
                
                return videos;
            }
            """

            video_data = self.browser.execute_script(js_code)

            if video_data:
                for data in video_data:
                    video = VideoItem()
                    video.index = data.get("index", 0)
                    video.title = data.get("title", "")
                    video.url = data.get("url", "")
                    video.duration = data.get("duration", "")
                    video.channel = data.get("channel", "")

                    if video.title:
                        videos.append(video)

        except Exception as e:
            print(f"   JavaScript 提取失败：{e}")

        return videos

    def _parse_from_json(self) -> list:
        """从 JSON 解析"""
        videos = []

        # 查找 ytInitialData
        match = re.search(r"var ytInitialData\s*=\s*({.+?});", self.html)
        if match:
            try:
                data = json.loads(match.group(1))
                self._extract_from_json_contents(data, videos)
            except Exception as e:
                print(f"   JSON 解析失败：{e}")

        return videos

    def _extract_from_json_contents(self, data: dict, videos: list):
        """从 JSON 内容提取"""

        def find_videos(obj, depth=0):
            if depth > 10:
                return

            if isinstance(obj, dict):
                if "playlistPanelVideoRenderer" in obj:
                    renderer = obj["playlistPanelVideoRenderer"]
                    try:
                        video = VideoItem()
                        video.title = renderer.get("title", {}).get("simpleText", "")

                        nav_endpoint = renderer.get("navigationEndpoint", {})
                        video_id = nav_endpoint.get("watchEndpoint", {}).get(
                            "videoId", ""
                        )
                        if video_id:
                            video.url = f"/watch?v={video_id}"

                        video.duration = renderer.get("lengthText", {}).get(
                            "simpleText", ""
                        )

                        short_byline = renderer.get("shortByline", {})
                        if "runs" in short_byline:
                            video.channel = short_byline["runs"][0].get("text", "")

                        if video.title and video.title not in [v.title for v in videos]:
                            video.index = len(videos) + 1
                            videos.append(video)
                    except Exception:
                        pass

                for key, value in obj.items():
                    find_videos(value, depth + 1)

            elif isinstance(obj, list):
                for item in obj:
                    find_videos(item, depth + 1)

        find_videos(data)

    def _cleanup(self):
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

    # 启动爬虫
    videos = spider.start()

    if videos:
        print("\n✅ 爬取完成!")

        # 保存结果
        spider.save_to_file(format="json")
        spider.save_to_file(format="txt")
        spider.save_to_file(format="csv")
    else:
        print("\n⚠️  未找到视频")


if __name__ == "__main__":
    main()
