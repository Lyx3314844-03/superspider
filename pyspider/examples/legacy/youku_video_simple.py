"""
优酷视频爬虫 - 简化版
直接使用 Playwright 爬取优酷视频

目标视频：https://v.youku.com/v_show/id_XNTk4Mjg1MjEzMg==.html
"""

import sys

sys.path.insert(0, "C:/Users/Administrator/spider/pyspider")

from playwright.sync_api import sync_playwright
import time
import json
import re
from datetime import datetime


def crawl_youku_video(video_url, headless=True):
    """爬取优酷视频信息"""

    print("\n" + "╔" * 30 + "╗")
    print("║" * 15 + " 优酷视频爬虫 " + "║" * 15)
    print("║" * 15 + "  简化版 (Playwright)  " + "║" * 15)
    print("╚" * 30 + "╝")
    print(f"\n📺 视频链接：{video_url}\n")

    video_info = {
        "title": "",
        "description": "",
        "duration": "",
        "channel": "",
        "url": video_url,
        "thumbnail": "",
        "views": "",
        "published": "",
        "video_id": "",
    }

    try:
        with sync_playwright() as p:
            # 启动浏览器
            print("🚀 启动浏览器 (Playwright)...")
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()
            print("   ✓ 浏览器已启动")

            # 导航到页面
            print("🌐 正在加载视频页面...")
            try:
                page.goto(video_url, wait_until="domcontentloaded", timeout=60000)
                print("   ✓ 页面已加载")
            except Exception as e:
                print(f"   ⚠️  加载超时，尝试继续...")

            # 等待内容加载
            print("📜 等待内容加载...")
            time.sleep(5)

            # 尝试等待视频播放器
            try:
                page.wait_for_selector(
                    ".video-player, #player, .yk-player", timeout=5000
                )
                print("   ✓ 检测到视频播放器")
            except:
                print("   ⚠️  未检测到视频播放器")

            # 获取 HTML
            print("📄 获取页面内容...")
            html = page.content()

            # 保存 HTML 用于调试
            with open("youku_video_source.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("   ✓ HTML 已保存到：youku_video_source.html")

            # 解析视频信息
            print("🔍 解析视频信息...")

            # 方法 1: 从 JSON 数据解析
            parse_from_json(html, video_info)

            # 方法 2: 使用 CSS 选择器
            if not video_info["title"]:
                parse_with_css(page, video_info)

            # 方法 3: 使用正则表达式
            if not video_info["title"]:
                parse_with_regex(html, video_info)

            # 提取视频 ID
            if not video_info["video_id"]:
                match = re.search(r"id_([a-zA-Z0-9=]+)", video_url)
                if match:
                    video_info["video_id"] = match.group(1)

            # 关闭浏览器
            browser.close()
            print("\n🔒 关闭浏览器...")

    except Exception as e:
        print(f"\n❌ 爬取失败：{e}")
        import traceback

        traceback.print_exc()

    # 打印结果
    print_results(video_info)

    # 导出结果
    export_results(video_info)

    return video_info


def parse_from_json(html, video_info):
    """从 JSON 数据解析"""
    patterns = [
        r"window\.__INITIAL_DATA__\s*=\s*({.+?});",
        r"var\s+__INITIAL_DATA__\s*=\s*({.+?});",
        r'"initData"\s*:\s*({.+?})[,}]',
    ]

    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            try:
                data_str = match.group(1)
                data_str = data_str.replace("undefined", "null")
                data = json.loads(data_str)
                extract_from_json(data, video_info)
                if video_info["title"]:
                    return
            except Exception as e:
                continue


def extract_from_json(data, video_info):
    """从 JSON 数据提取信息"""
    if isinstance(data, dict):
        if "data" in data:
            extract_from_json(data["data"], video_info)

        if "title" in data and isinstance(data["title"], str):
            video_info["title"] = data["title"]

        if "description" in data:
            video_info["description"] = data["description"]

        if "channel" in data:
            video_info["channel"] = data["channel"]

        if "views" in data or "viewCount" in data:
            video_info["views"] = str(data.get("views", data.get("viewCount", "")))

        if "thumbnail" in data or "poster" in data:
            video_info["thumbnail"] = str(data.get("thumbnail", data.get("poster", "")))

        if "videoUrl" in data or "download_url" in data:
            video_info["download_url"] = str(
                data.get("videoUrl", data.get("download_url", ""))
            )


def parse_with_css(page, video_info):
    """使用 CSS 选择器解析"""
    try:
        # 标题
        title_selectors = [
            "h1#title",
            "h1.video-title",
            ".video-info-title",
            'meta[property="og:title"]',
        ]

        for selector in title_selectors:
            try:
                elem = page.query_selector(selector)
                if elem:
                    if "meta" in selector:
                        video_info["title"] = elem.get_attribute("content") or ""
                    else:
                        video_info["title"] = elem.inner_text() or ""
                    if video_info["title"]:
                        break
            except:
                continue

        # 描述
        try:
            elem = page.query_selector(
                '.video-info-detail, .summary, meta[name="description"]'
            )
            if elem:
                if "meta" in str(elem):
                    video_info["description"] = elem.get_attribute("content") or ""
                else:
                    video_info["description"] = elem.inner_text() or ""
        except:
            pass

        # 频道
        try:
            elem = page.query_selector(".channel-name, .user-name, a.channel")
            if elem:
                video_info["channel"] = elem.inner_text() or ""
        except:
            pass

        # 缩略图
        try:
            elem = page.query_selector('meta[property="og:image"]')
            if elem:
                video_info["thumbnail"] = elem.get_attribute("content") or ""
        except:
            pass

    except Exception as e:
        pass


def parse_with_regex(html, video_info):
    """使用正则表达式解析"""
    # 标题
    title_patterns = [
        r"<title>([^<]+)</title>",
        r'"title"\s*:\s*"([^"]+)"',
    ]

    for pattern in title_patterns:
        match = re.search(pattern, html)
        if match:
            video_info["title"] = match.group(1).strip()
            video_info["title"] = re.sub(r"\s*-?\s*优酷\s*$", "", video_info["title"])
            break

    # 视频 ID
    id_match = re.search(r"id_X([a-zA-Z0-9=]+)", html)
    if id_match:
        video_info["video_id"] = f"X{id_match.group(1)}"


def print_results(video_info):
    """打印结果"""
    print("\n" + "═" * 60)
    print(" " * 20 + "爬取结果")
    print("═" * 60)

    if video_info["title"]:
        print(f"\n📺 标题：{video_info['title']}")
    else:
        print("\n⚠️  未找到视频标题")

    if video_info["video_id"]:
        print(f"🆔 ID: {video_info['video_id']}")
    if video_info["description"]:
        desc = video_info["description"]
        if len(desc) > 100:
            desc = desc[:100] + "..."
        print(f"📝 描述：{desc}")
    if video_info["channel"]:
        print(f"👤 频道：{video_info['channel']}")
    if video_info["views"]:
        print(f"👁️ 观看：{video_info['views']}")
    if video_info["thumbnail"]:
        print(f"🖼️ 缩略图：{video_info['thumbnail']}")
    if video_info.get("download_url"):
        print(f"🔗 下载链接：{video_info['download_url']}")
    if video_info["url"]:
        print(f"🔗 视频链接：{video_info['url']}")


def export_results(video_info):
    """导出结果"""
    print("\n💾 导出结果...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = f"youku_video_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([video_info], f, ensure_ascii=False, indent=2)
    print(f"   ✓ JSON: {json_path}")

    # TXT
    txt_path = f"youku_video_{timestamp}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"标题：{video_info['title']}\n")
        f.write(f"ID: {video_info['video_id']}\n")
        f.write(f"描述：{video_info['description']}\n")
        f.write(f"频道：{video_info['channel']}\n")
        f.write(f"观看：{video_info['views']}\n")
        f.write(f"缩略图：{video_info['thumbnail']}\n")
        f.write(f"视频链接：{video_info['url']}\n")
    print(f"   ✓ TXT: {txt_path}")


def main():
    """主函数"""
    # 优酷视频链接
    video_url = "https://v.youku.com/v_show/id_XNTk4Mjg1MjEzMg==.html"

    # 爬取
    video_info = crawl_youku_video(video_url, headless=True)

    if video_info and video_info["title"]:
        print("\n✅ 爬取完成!")
        print(f"   视频标题：{video_info['title']}")
    else:
        print("\n⚠️  未找到视频信息，可能是页面结构变化、需要登录或视频不存在。")


if __name__ == "__main__":
    main()
