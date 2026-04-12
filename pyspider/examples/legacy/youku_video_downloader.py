"""
优酷视频下载器 - 使用 Playwright 下载
支持下载优酷视频

目标视频：https://v.youku.com/v_show/id_XNTk4Mjg1MjEzMg==.html
"""

import sys

sys.path.insert(0, "C:/Users/Administrator/spider/pyspider")

from playwright.sync_api import sync_playwright
import time
import json
import re
import os
from datetime import datetime


def download_youku_video(video_url, output_dir, headless=True):
    """下载优酷视频"""

    print("\n" + "╔" * 40 + "╗")
    print("║" * 15 + " 优酷视频下载器 " + "║" * 15)
    print("║" * 12 + "  Playwright 版本  " + "║" * 12)
    print("╚" * 40 + "╝")
    print(f"\n📺 视频链接：{video_url}")
    print(f"📁 保存目录：{output_dir}\n")

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    video_info = {
        "title": "",
        "video_id": "",
        "download_url": "",
        "m3u8_url": "",
    }

    try:
        with sync_playwright() as p:
            # 启动浏览器
            print("🚀 启动浏览器 (Playwright)...")
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
            page = context.new_page()
            print("   ✓ 浏览器已启动")

            # 拦截网络请求，查找视频 URL
            print("🔍 拦截网络请求，查找视频资源...")
            video_urls = []

            def handle_response(response):
                try:
                    url = response.url
                    if ".m3u8" in url or "mp4" in url or "youku" in url.lower():
                        if "video" in url.lower() or "player" in url.lower():
                            video_urls.append(url)
                            print(f"   找到视频资源：{url[:100]}...")
                except:
                    pass

            page.on("response", handle_response)

            # 导航到页面
            print("🌐 正在加载视频页面...")
            try:
                page.goto(video_url, wait_until="domcontentloaded", timeout=60000)
                print("   ✓ 页面已加载")
            except Exception as e:
                print(f"   ⚠️  加载超时：{e}")

            # 等待视频播放器加载
            print("📜 等待视频播放器加载...")
            time.sleep(5)

            # 尝试点击播放按钮触发视频加载
            try:
                play_button = page.query_selector(".play-button, #play, .btn-play")
                if play_button:
                    print("   点击播放按钮...")
                    play_button.click()
                    time.sleep(3)
            except:
                pass

            # 滚动页面
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                page.evaluate("window.scrollTo(0, 0)")
            except:
                pass

            # 额外等待
            print("   等待视频资源加载...")
            time.sleep(5)

            # 获取 HTML
            print("📄 获取页面内容...")
            html = page.content()

            # 保存 HTML
            html_path = f"{output_dir}/video_source.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"   ✓ HTML 已保存到：{html_path}")

            # 解析视频信息
            print("🔍 解析视频信息...")

            # 从 JSON 解析
            parse_from_json(html, video_info)

            # 提取视频 ID
            if not video_info["video_id"]:
                match = re.search(r"id_([a-zA-Z0-9=]+)", video_url)
                if match:
                    video_info["video_id"] = match.group(1)

            # 标题
            if not video_info["title"]:
                title_match = re.search(r"<title>([^<]+)</title>", html)
                if title_match:
                    video_info["title"] = title_match.group(1).strip()
                    video_info["title"] = re.sub(
                        r"\s*-?\s*优酷\s*$", "", video_info["title"]
                    )

            # 使用默认标题
            if not video_info["title"]:
                video_info["title"] = f"youku_video_{video_info['video_id']}"

            # 关闭浏览器
            browser.close()
            print("\n🔒 关闭浏览器...")

    except Exception as e:
        print(f"\n❌ 爬取失败：{e}")
        import traceback

        traceback.print_exc()

    # 打印找到的视频 URL
    print("\n" + "═" * 60)
    print(" " * 20 + "找到的视频资源")
    print("═" * 60)

    if video_urls:
        print(f"\n共找到 {len(video_urls)} 个视频资源:")
        for i, url in enumerate(video_urls[:10], 1):
            print(f"{i}. {url}")
    else:
        print("\n⚠️  未找到视频资源 URL")

    # 打印视频信息
    print("\n" + "═" * 60)
    print(" " * 20 + "视频信息")
    print("═" * 60)

    if video_info["title"]:
        print(f"\n📺 标题：{video_info['title']}")
    if video_info["video_id"]:
        print(f"🆔 ID: {video_info['video_id']}")
    if video_info.get("m3u8_url"):
        print(f"🔗 M3U8: {video_info['m3u8_url'][:80]}...")
    if video_info.get("download_url"):
        print(f"🔗 下载：{video_info['download_url'][:80]}...")

    # 导出结果
    export_results(video_info, video_urls, output_dir)

    # 尝试使用 yt-dlp 下载
    try_download_with_ytdlp(video_url, output_dir, video_info["title"])

    return video_info, video_urls


def parse_from_json(html, video_info):
    """从 JSON 数据解析"""
    patterns = [
        r"window\.__INITIAL_DATA__\s*=\s*({.+?});",
        r"var\s+__INITIAL_DATA__\s*=\s*({.+?});",
    ]

    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            try:
                data_str = match.group(1).replace("undefined", "null")
                data = json.loads(data_str)
                extract_from_json(data, video_info)
                if video_info["title"]:
                    return
            except:
                continue


def extract_from_json(data, video_info):
    """从 JSON 数据提取"""
    if isinstance(data, dict):
        if "data" in data:
            extract_from_json(data["data"], video_info)

        if "title" in data and isinstance(data["title"], str):
            video_info["title"] = data["title"]

        if "videoUrl" in data:
            video_info["download_url"] = str(data["videoUrl"])

        if "m3u8Url" in data:
            video_info["m3u8_url"] = str(data["m3u8Url"])


def export_results(video_info, video_urls, output_dir):
    """导出结果"""
    print("\n💾 导出结果...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = f"{output_dir}/video_info_{timestamp}.json"
    data = {
        "video_info": video_info,
        "video_urls": video_urls,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"   ✓ JSON: {json_path}")

    # TXT
    txt_path = f"{output_dir}/video_info_{timestamp}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"标题：{video_info['title']}\n")
        f.write(f"ID: {video_info['video_id']}\n")
        f.write(f"\n找到的视频资源:\n")
        for url in video_urls:
            f.write(f"{url}\n")
    print(f"   ✓ TXT: {txt_path}")


def try_download_with_ytdlp(video_url, output_dir, title):
    """尝试使用 yt-dlp 下载"""
    print("\n📥 尝试使用 yt-dlp 下载...")

    try:
        import subprocess

        # 清理标题
        safe_title = re.sub(r'[<>:"/\\|？*]', "_", title) if title else "video"

        result = subprocess.run(
            [
                "yt-dlp",
                "-o",
                f"{output_dir}/{safe_title}.%(ext)s",
                "--no-playlist",
                "--write-info-json",
                video_url,
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode == 0:
            print("   ✓ 下载完成!")
            print(f"   {result.stdout}")
        else:
            print(f"   ⚠️  下载失败：{result.stderr}")

    except FileNotFoundError:
        print("   ⚠️  yt-dlp 未安装")
        print("   提示：pip install yt-dlp")
    except Exception as e:
        print(f"   ⚠️  下载出错：{e}")


def main():
    """主函数"""
    # 优酷视频链接
    video_url = "https://v.youku.com/v_show/id_XNTk4Mjg1MjEzMg==.html"

    # 输出目录
    output_dir = "C:/Users/Administrator/spider/pyspider/downloads"

    # 下载
    video_info, video_urls = download_youku_video(video_url, output_dir, headless=False)

    if video_urls:
        print("\n✅ 找到视频资源，请检查输出目录")
    else:
        print("\n⚠️  未找到视频资源，可能是版权限制或需要登录")


if __name__ == "__main__":
    main()
