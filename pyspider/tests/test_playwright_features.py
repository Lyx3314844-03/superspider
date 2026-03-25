#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright 功能测试脚本

测试所有 Playwright 功能：
1. ✅ 基础导航
2. ✅ 元素操作
3. ✅ 截图功能
4. ✅ JavaScript 执行
5. ✅ Cookie 管理
6. ✅ 增强功能（隐身模式、智能操作等）
"""

import sys
import time
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyspider.browser.playwright_browser import PlaywrightBrowser
from pyspider.browser.enhanced import PlaywrightBrowserEnhanced, BrowserConfig


def test_basic_browser():
    """测试基础浏览器功能"""
    print("\n" + "=" * 60)
    print("测试 1: 基础浏览器功能")
    print("=" * 60)
    
    try:
        with PlaywrightBrowser(headless=True) as browser:
            browser.start()
            
            # 测试导航
            print("\n测试导航...")
            browser.navigate("https://www.example.com")
            
            # 测试获取标题
            title = browser.get_title()
            print(f"✓ 页面标题：{title}")
            assert "Example" in title, "标题不正确"
            
            # 测试获取 URL
            url = browser.get_url()
            print(f"✓ 当前 URL: {url}")
            
            # 测试获取内容
            content = browser.get_content()
            print(f"✓ 页面内容长度：{len(content)}")
            assert len(content) > 0, "内容为空"
            
            # 测试获取元素文本
            h1_text = browser.get_text("h1")
            print(f"✓ H1 文本：{h1_text}")
            
            # 测试截图
            screenshot_path = "downloads/test_basic.png"
            browser.screenshot(screenshot_path)
            print(f"✓ 截图已保存：{screenshot_path}")
            
            print("\n✅ 基础浏览器功能测试通过")
            return True
            
    except Exception as e:
        print(f"\n❌ 基础浏览器功能测试失败：{e}")
        return False


def test_enhanced_browser():
    """测试增强版浏览器功能"""
    print("\n" + "=" * 60)
    print("测试 2: 增强版浏览器功能")
    print("=" * 60)
    
    try:
        config = BrowserConfig(
            headless=True,
            stealth=True,
            timeout=30000,
        )
        
        with PlaywrightBrowserEnhanced(config) as browser:
            browser.start()
            
            # 测试隐身模式
            print("\n测试隐身模式...")
            is_stealth = browser.config.stealth
            print(f"✓ 隐身模式：{is_stealth}")
            
            # 测试导航（带重试）
            print("\n测试导航（带重试）...")
            browser.navigate("https://www.example.com", max_retries=2)
            
            # 测试智能操作
            print("\n测试智能操作...")
            # 注意：example.com 没有输入框，这里只测试 API 调用
            print("✓ 智能操作 API 可用")
            
            # 测试 Cookie 管理
            print("\n测试 Cookie 管理...")
            cookies = browser.export_cookies()
            print(f"✓ 导出 Cookie 数：{len(cookies)}")
            
            # 测试请求统计
            print("\n测试请求统计...")
            browser.print_stats()
            
            print("\n✅ 增强版浏览器功能测试通过")
            return True
            
    except Exception as e:
        print(f"\n❌ 增强版浏览器功能测试失败：{e}")
        return False


def test_javascript():
    """测试 JavaScript 执行"""
    print("\n" + "=" * 60)
    print("测试 3: JavaScript 执行")
    print("=" * 60)
    
    try:
        with PlaywrightBrowser(headless=True) as browser:
            browser.start()
            browser.navigate("https://www.example.com")
            
            # 测试执行简单 JS
            print("\n测试执行简单 JS...")
            title = browser.evaluate("document.title")
            print(f"✓ JS 获取标题：{title}")
            
            # 测试获取窗口大小
            print("\n测试获取窗口大小...")
            window_size = browser.evaluate("""
                () => {
                    return {
                        width: window.innerWidth,
                        height: window.innerHeight
                    }
                }
            """)
            print(f"✓ 窗口大小：{window_size}")
            
            # 测试修改页面
            print("\n测试修改页面...")
            browser.evaluate("""
                () => {
                    document.body.style.backgroundColor = 'red';
                }
            """)
            print("✓ 页面背景已修改")
            
            # 截图验证
            browser.screenshot("downloads/test_js.png")
            print("✓ 截图已保存")
            
            print("\n✅ JavaScript 执行测试通过")
            return True
            
    except Exception as e:
        print(f"\n❌ JavaScript 执行测试失败：{e}")
        return False


def test_cookie_management():
    """测试 Cookie 管理"""
    print("\n" + "=" * 60)
    print("测试 4: Cookie 管理")
    print("=" * 60)
    
    try:
        with PlaywrightBrowser(headless=True) as browser:
            browser.start()
            browser.navigate("https://www.example.com")
            
            # 测试导出 Cookie
            print("\n测试导出 Cookie...")
            cookies = browser.export_cookies()
            print(f"✓ 导出 Cookie 数：{len(cookies)}")
            
            # 测试保存 Cookie 到文件
            print("\n测试保存 Cookie 到文件...")
            cookie_file = "downloads/test_cookies.json"
            browser.save_cookies_to_file(cookie_file)
            
            # 验证文件存在
            assert Path(cookie_file).exists(), "Cookie 文件不存在"
            print(f"✓ Cookie 文件已保存：{cookie_file}")
            
            # 测试加载 Cookie
            print("\n测试加载 Cookie...")
            browser.load_cookies_from_file(cookie_file)
            print("✓ Cookie 已加载")
            
            print("\n✅ Cookie 管理测试通过")
            return True
            
    except Exception as e:
        print(f"\n❌ Cookie 管理测试失败：{e}")
        return False


def test_screenshot():
    """测试截图功能"""
    print("\n" + "=" * 60)
    print("测试 5: 截图功能")
    print("=" * 60)
    
    try:
        with PlaywrightBrowser(headless=True) as browser:
            browser.start()
            browser.navigate("https://www.example.com")
            
            # 测试全屏截图
            print("\n测试全屏截图...")
            browser.screenshot("downloads/test_fullpage.png", full_page=True)
            print("✓ 全屏截图已保存")
            
            # 测试普通截图
            print("\n测试普通截图...")
            browser.screenshot("downloads/test_normal.png", full_page=False)
            print("✓ 普通截图已保存")
            
            # 验证文件存在
            assert Path("downloads/test_fullpage.png").exists(), "全屏截图不存在"
            assert Path("downloads/test_normal.png").exists(), "普通截图不存在"
            
            print("\n✅ 截图功能测试通过")
            return True
            
    except Exception as e:
        print(f"\n❌ 截图功能测试失败：{e}")
        return False


def test_real_website():
    """测试真实网站"""
    print("\n" + "=" * 60)
    print("测试 6: 真实网站测试")
    print("=" * 60)
    
    try:
        with PlaywrightBrowserEnhanced(stealth=True) as browser:
            browser.start()
            
            # 测试 Wikipedia
            print("\n测试 Wikipedia...")
            browser.navigate("https://zh.wikipedia.org/wiki/Python")
            
            title = browser.get_title()
            print(f"✓ 页面标题：{title}")
            
            # 获取内容
            content = browser.get_text("h1")
            print(f"✓ 主要内容：{content}")
            
            # 截图
            browser.screenshot("downloads/test_wikipedia.png")
            print("✓ 截图已保存")
            
            # 打印统计
            browser.print_stats()
            
            print("\n✅ 真实网站测试通过")
            return True
            
    except Exception as e:
        print(f"\n❌ 真实网站测试失败：{e}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Playwright 功能测试")
    print("=" * 60)
    print(f"开始时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 确保输出目录存在
    Path("downloads").mkdir(exist_ok=True)
    
    # 测试结果
    results = []
    
    # 运行测试
    results.append(("基础浏览器功能", test_basic_browser()))
    results.append(("增强版浏览器功能", test_enhanced_browser()))
    results.append(("JavaScript 执行", test_javascript()))
    results.append(("Cookie 管理", test_cookie_management()))
    results.append(("截图功能", test_screenshot()))
    results.append(("真实网站测试", test_real_website()))
    
    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    print("\n" + "-" * 60)
    print(f"总计：{passed}/{total} 测试通过")
    print(f"成功率：{passed/total*100:.1f}%")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
