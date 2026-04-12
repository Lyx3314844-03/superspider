"""
YouTube 播放列表爬虫
使用 pyspider 框架爬取 YouTube 播放列表中的所有视频

目标播放列表：https://www.youtube.com/watch?v=tr5yZ2TzXaY&list=PLRuPQZBVD6vV89UKIzUwZFUhDx9DjXLxc
"""

import sys

sys.path.insert(0, "C:/Users/Administrator/spider")

from pyspider.browser.browser import PlaywrightManager
from pyspider.parser.parser import HTMLParser
import time
import json
from datetime import datetime


class VideoInfo:
    """视频信息类"""

    def __init__(self):
        self.title = ""
        self.duration = ""
        self.channel = ""
        self.url = ""
        self.thumbnail = ""
        self.views = ""

    def __str__(self):
        return f"VideoInfo(title='{self.title}', duration='{self.duration}', url='{self.url}')"


class YouTubePlaylistSpider:
    """YouTube 播放列表爬虫"""

    def __init__(self, playlist_url):
        self.playlist_url = playlist_url
        self.browser = None
        self.videos = []

    def start(self):
        """启动爬虫"""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║           YouTube 播放列表爬虫 (pyspider)                 ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        print()
        print(f"播放列表 URL: {self.playlist_url}")
        print()

        # 初始化浏览器（使用 Playwright）
        print("正在启动浏览器 (Playwright)...")
        self.browser = PlaywrightManager(headless=True)

        try:
            # 导航到播放列表
            print("正在加载播放列表页面...")
            self.browser.navigate(self.playlist_url)

            # 等待页面加载
            print("等待页面加载...")
            time.sleep(8)

            # 滚动加载所有视频
            print("滚动加载所有视频...")
            self._scroll_to_load_all()

            # 获取页面 HTML
            print("获取页面内容...")
            html = self.browser.get_html()

            # 保存到本地用于调试
            with open("youtube_page_source.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("  页面 HTML 已保存到：youtube_page_source.html")

            # 解析视频列表
            print("解析视频信息...")
            self.videos = self._parse_playlist(html)

            # 打印结果
            self._print_results()

            # 保存到文件
            self._save_to_file()

            return self.videos

        except Exception as e:
            print(f"爬取失败：{e}")
            import traceback

            traceback.print_exc()
            return []

        finally:
            # 关闭浏览器
            if self.browser:
                self.browser.close()

    def _scroll_to_load_all(self, scroll_times=10, scroll_pause=1):
        """滚动加载所有视频"""
        for i in range(scroll_times):
            # 滚动到底部
            self.browser.execute_script(
                "window.scrollTo(0, document.body.scrollHeight)"
            )
            time.sleep(scroll_pause)

            # 滚动回顶部
            self.browser.execute_script("window.scrollTo(0, 0)")
            time.sleep(0.5)

            print(f"  滚动 {i+1}/{scroll_times}")

    def _parse_playlist(self, html):
        """解析播放列表 HTML"""
        videos = []
        parser = HTMLParser(html)
        seen_titles = set()

        # 查找所有视频项
        video_elements = parser.css("ytd-playlist-video-renderer")

        print(f"  找到 {len(video_elements)} 个视频元素")

        # 提取每个视频的信息
        for i, video_elem in enumerate(video_elements):
            try:
                video = VideoInfo()

                # 提取标题
                title_elem = video_elem.querySelector("#video-title")
                if title_elem:
                    video.title = title_elem.text.strip()
                    video.url = title_elem.get_attribute("href", "")

                # 跳过重复或空标题
                if not video.title or video.title in seen_titles:
                    continue
                seen_titles.add(video.title)

                # 提取时长
                duration_elem = video_elem.querySelector(
                    "span.ytd-thumbnail-overlay-time-status-renderer"
                )
                if duration_elem:
                    video.duration = duration_elem.text.strip()

                # 提取频道名称
                channel_elem = video_elem.querySelector("#channel-name #text")
                if channel_elem:
                    video.channel = channel_elem.text.strip()

                # 提取缩略图
                thumb_elem = video_elem.querySelector("img#thumbnail")
                if thumb_elem:
                    video.thumbnail = thumb_elem.get_attribute("src", "")

                # 提取观看次数
                views_elem = video_elem.querySelector("#metadata-line span")
                if views_elem:
                    video.views = views_elem.text.strip()

                videos.append(video)

            except Exception as e:
                print(f"  解析视频 {i+1} 失败：{e}")
                continue

        # 备用方法：如果没找到视频，尝试其他选择器
        if len(videos) == 0:
            print("  使用备用选择器重新解析...")
            titles = parser.css("a#video-title")
            for title in titles:
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    video = VideoInfo()
                    video.title = title
                    videos.append(video)

        return videos

    def _print_results(self):
        """打印结果"""
        print()
        print("═══════════════════════════════════════════════════════════")
        print("                      爬取结果                              ")
        print("═══════════════════════════════════════════════════════════")
        print(f"共找到 {len(self.videos)} 个视频")
        print()

        for i, video in enumerate(self.videos):
            print(f"{i+1}. {video.title}")
            print(f"   时长：{video.duration or 'N/A'}")
            print(f"   频道：{video.channel or 'N/A'}")
            print(f"   观看：{video.views or 'N/A'}")
            print(f"   链接：{video.url}")
            print()

    def _save_to_file(self, filename="youtube_playlist_result.txt"):
        """保存到文件"""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("YouTube 播放列表视频列表\n")
                f.write(
                    "═══════════════════════════════════════════════════════════\n\n"
                )
                f.write(f"播放列表 URL: {self.playlist_url}\n")
                f.write(f"爬取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"视频总数：{len(self.videos)}\n\n")
                f.write(
                    "═══════════════════════════════════════════════════════════\n\n"
                )

                for i, video in enumerate(self.videos):
                    f.write(f"{i+1}. {video.title}\n")
                    f.write(f"   时长：{video.duration or 'N/A'}\n")
                    f.write(f"   频道：{video.channel or 'N/A'}\n")
                    f.write(f"   观看：{video.views or 'N/A'}\n")
                    f.write(f"   链接：{video.url}\n\n")

            print(f"结果已保存到：{filename}")

            # 同时保存为 JSON 格式
            json_filename = "youtube_playlist_result.json"
            with open(json_filename, "w", encoding="utf-8") as f:
                data = {
                    "playlist_url": self.playlist_url,
                    "crawl_time": datetime.now().isoformat(),
                    "total_videos": len(self.videos),
                    "videos": [
                        {
                            "title": v.title,
                            "duration": v.duration,
                            "channel": v.channel,
                            "views": v.views,
                            "url": v.url,
                            "thumbnail": v.thumbnail,
                        }
                        for v in self.videos
                    ],
                }
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"JSON 结果已保存到：{json_filename}")

        except Exception as e:
            print(f"保存文件失败：{e}")


def main():
    """主函数"""
    playlist_url = "https://www.youtube.com/watch?v=tr5yZ2TzXaY&list=PLRuPQZBVD6vV89UKIzUwZFUhDx9DjXLxc"

    spider = YouTubePlaylistSpider(playlist_url)
    videos = spider.start()

    if videos:
        print()
        print("爬取完成！")
    else:
        print()
        print("未找到视频，可能是页面结构变化或需要登录。")


if __name__ == "__main__":
    main()
