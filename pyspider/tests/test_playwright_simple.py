#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright 功能测试脚本（简化版）

直接测试 Playwright 核心功能
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def test_playwright():
    """测试 Playwright 核心功能"""
    print("\n" + "=" * 60)
    print("Playwright 功能测试")
    print("=" * 60)
    
    results = []
    
    try:
        # 确保输出目录存在
        Path("downloads").mkdir(exist_ok=True)
        
        with sync_playwright() as p:
            # 测试 1: 启动浏览器
            print("\n测试 1: 启动浏览器...")
            browser = p.chromium.launch(headless=True)
            print("✓ 浏览器启动成功")
            results.append(("启动浏览器", True))
            
            # 测试 2: 创建页面
            print("\n测试 2: 创建页面...")
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()
            print("✓ 页面创建成功")
            results.append(("创建页面", True))
            
            # 测试 3: 导航
            print("\n测试 3: 导航到页面...")
            page.goto("https://www.example.com", wait_until="networkidle")
            print(f"✓ 导航成功，标题：{page.title()}")
            results.append(("页面导航", True))
            
            # 测试 4: 获取内容
            print("\n测试 4: 获取页面内容...")
            title = page.title()
            h1_text = page.query_selector("h1").text_content()
            print(f"✓ 页面标题：{title}")
            print(f"✓ H1 文本：{h1_text}")
            results.append(("获取内容", True))
            
            # 测试 5: JavaScript 执行
            print("\n测试 5: JavaScript 执行...")
            window_size = page.evaluate("""
                () => {
                    return {
                        width: window.innerWidth,
                        height: window.innerHeight
                    }
                }
            """)
            print(f"✓ 窗口大小：{window_size}")
            results.append(("JavaScript 执行", True))
            
            # 测试 6: 截图
            print("\n测试 6: 截图...")
            page.screenshot(path="downloads/test_example.png", full_page=True)
            print("✓ 截图已保存：downloads/test_example.png")
            results.append(("截图功能", True))
            
            # 测试 7: Cookie 管理
            print("\n测试 7: Cookie 管理...")
            cookies = context.cookies()
            print(f"✓ Cookie 数：{len(cookies)}")
            
            # 保存 Cookie
            import json
            with open("downloads/test_cookies.json", "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            print("✓ Cookie 已保存到：downloads/test_cookies.json")
            results.append(("Cookie 管理", True))
            
            # 测试 8: 隐身模式
            print("\n测试 8: 隐身模式测试...")
            stealth_page = context.new_page()
            stealth_page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            stealth_page.goto("https://www.example.com")
            print("✓ 隐身模式应用成功")
            results.append(("隐身模式", True))
            
            # 关闭
            browser.close()
            
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        results.append(("测试执行", False))
    
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
    if total > 0:
        print(f"成功率：{passed/total*100:.1f}%")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    import sys
    success = test_playwright()
    sys.exit(0 if success else 1)
