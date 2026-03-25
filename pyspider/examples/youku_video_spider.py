"""
优酷视频爬虫
使用 pyspider 增强模块，包含反反爬虫功能

目标视频：https://v.youku.com/v_show/id_XNTk4Mjg1MjEzMg==.html
"""

import sys
sys.path.insert(0, 'C:/Users/Administrator/spider/pyspider')
sys.path.insert(0, 'C:/Users/Administrator/spider')

from pyspider.enhanced.enhancements import (
    EnhancedSpider, UserAgentRotator, AntiBot,
    DataExporter, RetryHandler
)
from pyspider.browser.browser import PlaywrightManager
from pyspider.parser.parser import HTMLParser
import time
import json
import re
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class VideoInfo:
    """视频信息"""
    title: str = ""
    description: str = ""
    duration: str = ""
    channel: str = ""
    url: str = ""
    thumbnail: str = ""
    views: str = ""
    published: str = ""
    video_id: str = ""
    download_url: str = ""

    def to_dict(self) -> Dict:
        return {
            'title': self.title,
            'description': self.description,
            'duration': self.duration,
            'channel': self.channel,
            'url': self.url,
            'thumbnail': self.thumbnail,
            'views': self.views,
            'published': self.published,
            'video_id': self.video_id,
            'download_url': self.download_url,
        }


class YoukuVideoSpider(EnhancedSpider):
    """优酷视频爬虫"""

    def __init__(self, video_url, headless=True):
        super().__init__(name="YoukuVideoSpider", use_retry=True)
        self.video_url = video_url
        self.headless = headless
        self.browser = None
        self.video_info = VideoInfo()

    def start(self) -> Optional[VideoInfo]:
        """启动爬虫"""
        self._print_header()

        try:
            # 初始化浏览器
            self._init_browser()

            # 导航到页面
            self._navigate_to_video()

            # 等待内容加载
            self._wait_for_content()

            # 获取 HTML
            html = self._get_html()

            # 解析视频信息
            self._parse_video(html)

            # 输出结果
            self._print_results()
            self._export_results()

            return self.video_info

        except Exception as e:
            print(f"\n❌ 爬取失败：{e}")
            import traceback
            traceback.print_exc()
            return None

        finally:
            self._close_browser()

    def _print_header(self):
        """打印头部"""
        print("\n" + "╔"*30 + "╗")
        print("║"*15 + " 优酷视频爬虫 " + "║"*15)
        print("║"*12 + "  增强版 (带反反爬虫)  " + "║"*12)
        print("╚"*30 + "╝")
        print(f"\n📺 视频链接：{self.video_url}\n")

    def _init_browser(self):
        """初始化浏览器"""
        print("🚀 启动浏览器 (Playwright)...")
        self.browser = PlaywrightManager(headless=self.headless)
        print("   ✓ 浏览器已启动")

    def _navigate_to_video(self):
        """导航到视频页面"""
        print("🌐 正在加载视频页面...")

        # 使用隐身请求头
        self.browser.page.set_extra_http_headers(AntiBot.get_stealth_headers())

        # 尝试不同的 URL 格式
        urls_to_try = [
            self.video_url,
            self.video_url.replace("youku.tv", "youku.com"),
            f"https://v.youku.com/v_show/{self.video_info.video_id}.html" if self.video_info.video_id else None,
        ]

        for url in urls_to_try:
            if not url:
                continue
            try:
                print(f"   尝试加载：{url}")
                self.browser.navigate(url)
                break
            except Exception as e:
                print(f"   加载失败：{e}")
                continue

        # 等待初始加载
        print("   ⏳ 等待页面加载...")
        time.sleep(5)

        # 检查是否需要验证
        html = self.browser.get_html()
        if "just a moment" in html.lower() or "checking your browser" in html.lower():
            print("   ⚠️  检测到验证页面，等待绕过...")
            AntiBot.bypass_cloudflare(self.browser, timeout=30)

        print("   ✓ 页面已加载")

    def _wait_for_content(self):
        """等待内容加载"""
        print("📜 等待视频内容加载...")

        # 滚动页面触发加载
        AntiBot.human_like_scroll(
            self.browser,
            scroll_times=3,
            scroll_pause=1.0
        )

        # 额外等待
        time.sleep(AntiBot.generate_random_delay(2, 4))
        print("   ✓ 内容已加载")

    def _get_html(self) -> str:
        """获取 HTML"""
        print("📄 获取页面内容...")
        html = self.browser.get_html()

        # 保存 HTML 用于调试
        with open("youku_video_source.html", "w", encoding='utf-8') as f:
            f.write(html)
        print("   ✓ HTML 已保存到：youku_video_source.html")

        return html

    def _parse_video(self, html: str):
        """解析视频信息"""
        print("🔍 解析视频信息...")

        parser = HTMLParser(html)

        # 方法 1: 从 JSON 数据解析
        self._parse_from_json(html)

        # 方法 2: 使用 CSS 选择器
        if not self.video_info.title:
            self._parse_with_css(parser)

        # 方法 3: 使用正则表达式
        if not self.video_info.title:
            self._parse_with_regex(html)

        # 提取视频 ID
        self._extract_video_id()

        if self.video_info.title:
            print(f"   ✓ 解析成功：{self.video_info.title}")
        else:
            print("   ⚠️  未能解析到视频信息")

    def _parse_from_json(self, html: str):
        """从 JSON 数据解析"""
        # 查找 window.__INITIAL_DATA__
        patterns = [
            r'window\.__INITIAL_DATA__\s*=\s*({.+?});',
            r'var\s+__INITIAL_DATA__\s*=\s*({.+?});',
            r'"initData"\s*:\s*({.+?})',
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                try:
                    data_str = match.group(1)
                    # 尝试修复 JSON
                    data_str = data_str.replace('undefined', 'null')
                    data_str = data_str.replace('true', 'True')
                    data_str = data_str.replace('false', 'False')
                    
                    data = json.loads(data_str)
                    self._extract_from_json(data)
                    return
                except Exception as e:
                    print(f"   JSON 解析失败：{e}")
                    continue

    def _extract_from_json(self, data: Dict):
        """从 JSON 数据提取信息"""
        # 尝试不同的 JSON 结构
        if isinstance(data, dict):
            # 优酷常见的数据结构
            if 'data' in data:
                self._extract_from_json(data['data'])
            
            # 视频标题
            if 'title' in data and isinstance(data['title'], str):
                self.video_info.title = data['title']
            
            # 视频描述
            if 'description' in data:
                self.video_info.description = data['description']
            
            # 频道信息
            if 'channel' in data:
                self.video_info.channel = data['channel']
            
            # 观看次数
            if 'views' in data or 'viewCount' in data:
                self.video_info.views = str(data.get('views', data.get('viewCount', '')))
            
            # 缩略图
            if 'thumbnail' in data or 'poster' in data:
                self.video_info.thumbnail = data.get('thumbnail', data.get('poster', ''))
            
            # 视频 URL
            if 'videoUrl' in data or 'download_url' in data:
                self.video_info.download_url = data.get('videoUrl', data.get('download_url', ''))

    def _parse_with_css(self, parser: HTMLParser):
        """使用 CSS 选择器解析"""
        # 标题
        title_selectors = [
            'h1#title',
            'h1.video-title',
            '.video-info-title',
            'meta[property="og:title"]',
        ]
        
        for selector in title_selectors:
            elem = parser.css_first(selector)
            if elem:
                if elem.tag == 'meta':
                    self.video_info.title = elem.get_attribute('content', '')
                else:
                    self.video_info.title = elem.text.strip()
                break

        # 描述
        desc_selectors = [
            '.video-info-detail',
            '.summary',
            'meta[name="description"]',
        ]
        
        for selector in desc_selectors:
            elem = parser.css_first(selector)
            if elem:
                if elem.tag == 'meta':
                    self.video_info.description = elem.get_attribute('content', '')
                else:
                    self.video_info.description = elem.text.strip()
                break

        # 频道
        channel_elem = parser.css_first('.channel-name, .user-name, a.channel')
        if channel_elem:
            self.video_info.channel = channel_elem.text.strip()

        # 缩略图
        thumb_elem = parser.css_first('meta[property="og:image"]')
        if thumb_elem:
            self.video_info.thumbnail = thumb_elem.get_attribute('content', '')

    def _parse_with_regex(self, html: str):
        """使用正则表达式解析"""
        # 标题
        title_patterns = [
            r'<title>([^<]+)</title>',
            r'"title"\s*:\s*"([^"]+)"',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, html)
            if match:
                self.video_info.title = match.group(1).strip()
                # 清理标题
                self.video_info.title = re.sub(r'\s*-?\s*优酷\s*$', '', self.video_info.title)
                break

        # 视频 ID
        id_match = re.search(r'id_X([a-zA-Z0-9=]+)', html)
        if id_match:
            self.video_info.video_id = f"X{id_match.group(1)}"

    def _extract_video_id(self):
        """从 URL 提取视频 ID"""
        if not self.video_info.video_id:
            match = re.search(r'id_([a-zA-Z0-9=]+)', self.video_url)
            if match:
                self.video_info.video_id = match.group(1)

    def _print_results(self):
        """打印结果"""
        print("\n" + "═"*60)
        print(" " * 20 + "爬取结果")
        print("═"*60)

        if self.video_info.title:
            print(f"\n📺 标题：{self.video_info.title}")
        if self.video_info.video_id:
            print(f"🆔 ID: {self.video_info.video_id}")
        if self.video_info.description:
            print(f"📝 描述：{self.video_info.description[:100]}...")
        if self.video_info.channel:
            print(f"👤 频道：{self.video_info.channel}")
        if self.video_info.views:
            print(f"👁️ 观看：{self.video_info.views}")
        if self.video_info.thumbnail:
            print(f"🖼️ 缩略图：{self.video_info.thumbnail}")
        if self.video_info.download_url:
            print(f"🔗 下载链接：{self.video_info.download_url}")
        if self.video_info.url:
            print(f"🔗 视频链接：{self.video_info.url}")

    def _export_results(self):
        """导出结果"""
        print("\n💾 导出结果...")

        data = [self.video_info.to_dict()]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        DataExporter.to_json(data, f"youku_video_{timestamp}.json")
        DataExporter.to_csv(data, f"youku_video_{timestamp}.csv")
        DataExporter.to_txt(data, f"youku_video_{timestamp}.txt")

        print(f"   ✓ 结果已导出到：youku_video_{timestamp}.*")

    def _close_browser(self):
        """关闭浏览器"""
        if self.browser:
            print("\n🔒 关闭浏览器...")
            self.browser.close()
            print("   ✓ 浏览器已关闭")


def main():
    """主函数"""
    # 优酷视频链接
    video_url = "https://v.youku.com/v_show/id_XNTk4Mjg1MjEzMg==.html"

    # 创建爬虫
    spider = YoukuVideoSpider(video_url, headless=True)

    # 开始爬取
    video_info = spider.start()

    if video_info and video_info.title:
        print("\n✅ 爬取完成!")
        print(f"   视频标题：{video_info.title}")
    else:
        print("\n⚠️  未找到视频信息，可能是页面结构变化或需要登录。")


if __name__ == "__main__":
    main()
