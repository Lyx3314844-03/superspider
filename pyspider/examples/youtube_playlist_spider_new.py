"""
YouTube 播放列表爬虫 - 更新版
使用 pyspider 框架爬取 YouTube 播放列表中的所有视频

目标播放列表：https://www.youtube.com/watch?v=tr5yZ2TzXaY&list=PLRuPQZBVD6vV89UKIzUwZFUhDx9DjXLxc
"""

import sys
sys.path.insert(0, 'C:/Users/Administrator/spider')

from pyspider.browser.browser import PlaywrightManager
import time
import json
import re
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
        self.index = 0

    def to_dict(self):
        return {
            "index": self.index,
            "title": self.title,
            "duration": self.duration,
            "channel": self.channel,
            "url": self.url,
            "thumbnail": self.thumbnail,
            "views": self.views
        }

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
        print("║        YouTube 播放列表爬虫 (pyspider) - 更新版          ║")
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

            # 方法 1: 解析 HTML
            print("解析视频信息 (HTML 解析)...")
            self.videos = self._parse_playlist(html)

            # 方法 2: 如果 HTML 解析失败，尝试从 JSON 数据解析
            if len(self.videos) == 0:
                print("HTML 解析未找到视频，尝试从 JSON 数据解析...")
                self.videos = self._parse_from_json(html)

            # 方法 3: 使用 JavaScript 直接提取
            if len(self.videos) == 0:
                print("JSON 解析未找到视频，尝试使用 JavaScript 提取...")
                self.videos = self._extract_with_js()

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
            self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(scroll_pause)

            # 滚动回顶部
            self.browser.execute_script("window.scrollTo(0, 0)")
            time.sleep(0.5)

            print(f"  滚动 {i+1}/{scroll_times}")

    def _parse_playlist(self, html):
        """解析播放列表 HTML"""
        videos = []
        seen_titles = set()

        # 查找所有视频项 - 使用 ytd-playlist-panel-video-renderer
        pattern = r'<ytd-playlist-panel-video-renderer[^>]*>.*?</ytd-playlist-panel-video-renderer>'
        video_elements = re.findall(pattern, html, re.DOTALL)

        print(f"  找到 {len(video_elements)} 个视频元素")

        # 提取每个视频的信息
        for i, video_elem in enumerate(video_elements):
            try:
                video = VideoInfo()

                # 提取标题
                title_match = re.search(r'id="video-title"[^>]*>([^<]+)</span>', video_elem)
                if title_match:
                    video.title = title_match.group(1).strip()

                # 提取 URL
                url_match = re.search(r'href="([^"]*watch\?v=[^"]*)"', video_elem)
                if url_match:
                    video.url = url_match.group(1).replace('&amp;', '&')

                # 提取时长
                duration_match = re.search(r'aria-label="([^"]*分钟[^"]*|[^"]*:[^"]*)"', video_elem)
                if duration_match:
                    video.duration = duration_match.group(1).strip()

                # 提取频道名称
                channel_match = re.search(r'id="byline"[^>]*>([^<]+)</span>', video_elem)
                if channel_match:
                    video.channel = channel_match.group(1).strip()

                # 跳过重复或空标题
                if not video.title or video.title in seen_titles:
                    continue
                seen_titles.add(video.title)

                video.index = i + 1
                videos.append(video)

            except Exception as e:
                print(f"  解析视频 {i+1} 失败：{e}")
                continue

        print(f"  成功解析 {len(videos)} 个视频")
        return videos

    def _parse_from_json(self, html):
        """从 JSON 数据解析"""
        videos = []

        # 查找 ytInitialData
        match = re.search(r'var ytInitialData\s*=\s*({.+?});', html)
        if match:
            try:
                data = json.loads(match.group(1))
                contents = data.get('contents', {})

                # 遍历播放列表内容
                self._extract_from_json_contents(contents, videos)

                print(f"  从 JSON 解析到 {len(videos)} 个视频")
            except Exception as e:
                print(f"  JSON 解析失败：{e}")

        return videos

    def _extract_from_json_contents(self, contents: dict, videos: list):
        """从 JSON 内容提取"""
        # 查找 playlistPanelVideoRenderer 或 playlistPanelVideoLockedRenderer
        def find_videos(obj, depth=0):
            if depth > 10:
                return

            if isinstance(obj, dict):
                # 检查是否是视频对象
                if 'playlistPanelVideoRenderer' in obj or 'playlistPanelVideoLockedRenderer' in obj:
                    renderer = obj.get('playlistPanelVideoRenderer') or obj.get('playlistPanelVideoLockedRenderer')
                    if renderer:
                        try:
                            video = VideoInfo()
                            video.title = renderer.get('title', {}).get('simpleText', '')
                            
                            # 获取 URL
                            nav_endpoint = renderer.get('navigationEndpoint', {})
                            video.url = nav_endpoint.get('watchEndpoint', {}).get('url', '')
                            if not video.url and 'videoId' in nav_endpoint.get('watchEndpoint', {}):
                                video_id = nav_endpoint['watchEndpoint']['videoId']
                                video.url = f'/watch?v={video_id}'
                            
                            # 获取时长
                            video.duration = renderer.get('lengthText', {}).get('simpleText', '')
                            
                            # 获取频道
                            short_byline = renderer.get('shortByline', {})
                            if 'runs' in short_byline:
                                video.channel = short_byline['runs'][0].get('text', '')
                            
                            if video.title and video.title not in [v.title for v in videos]:
                                video.index = len(videos) + 1
                                videos.append(video)
                        except Exception:
                            pass

                # 递归查找
                for key, value in obj.items():
                    find_videos(value, depth + 1)

            elif isinstance(obj, list):
                for item in obj:
                    find_videos(item, depth + 1)

        find_videos(contents)

    def _extract_with_js(self):
        """使用 JavaScript 直接提取"""
        videos = []

        try:
            # 使用 JavaScript 获取播放列表视频
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
                    video = VideoInfo()
                    video.index = data.get('index', 0)
                    video.title = data.get('title', '')
                    video.url = data.get('url', '')
                    video.duration = data.get('duration', '')
                    video.channel = data.get('channel', '')

                    if video.title:
                        videos.append(video)

                print(f"  使用 JavaScript 提取到 {len(videos)} 个视频")

        except Exception as e:
            print(f"  JavaScript 提取失败：{e}")

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
            print(f"{video.index:2d}. {video.title}")
            if video.duration:
                print(f"    时长：{video.duration}")
            if video.channel:
                print(f"    频道：{video.channel}")
            if video.url:
                print(f"    链接：{video.url}")
            print()

    def _save_to_file(self):
        """保存到文件"""
        try:
            # 保存为 TXT 格式
            txt_filename = "youtube_playlist_result.txt"
            with open(txt_filename, 'w', encoding='utf-8') as f:
                f.write("YouTube 播放列表视频列表\n")
                f.write("═══════════════════════════════════════════════════════════\n\n")
                f.write(f"播放列表 URL: {self.playlist_url}\n")
                f.write(f"爬取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"视频总数：{len(self.videos)}\n\n")
                f.write("═══════════════════════════════════════════════════════════\n\n")

                for video in self.videos:
                    f.write(f"{video.index}. {video.title}\n")
                    if video.duration:
                        f.write(f"   时长：{video.duration}\n")
                    if video.channel:
                        f.write(f"   频道：{video.channel}\n")
                    if video.url:
                        f.write(f"   链接：{video.url}\n")
                    f.write("\n")

            print(f"结果已保存到：{txt_filename}")

            # 保存为 JSON 格式
            json_filename = "youtube_playlist_result.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                data = {
                    "playlist_url": self.playlist_url,
                    "crawl_time": datetime.now().isoformat(),
                    "total_videos": len(self.videos),
                    "videos": [v.to_dict() for v in self.videos]
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
