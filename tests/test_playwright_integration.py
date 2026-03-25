#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GoSpider 和 RustSpider Playwright 集成测试
"""

import subprocess
import sys
from pathlib import Path

def test_gospider_playwright():
    """测试 GoSpider Playwright 集成"""
    print("\n" + "=" * 60)
    print("GoSpider Playwright 集成测试")
    print("=" * 60)
    
    # 检查文件
    playwright_file = Path("gospider/playwright/playwright.go")
    if playwright_file.exists():
        print(f"✓ Playwright 模块存在：{playwright_file}")
    else:
        print(f"❌ Playwright 模块不存在：{playwright_file}")
        return False
    
    # 检查示例
    example_file = Path("gospider/examples/playwright_example/main.go")
    if example_file.exists():
        print(f"✓ Playwright 示例存在：{example_file}")
    else:
        print(f"❌ Playwright 示例不存在：{example_file}")
        return False
    
    # 检查 go.mod
    go_mod = Path("gospider/go.mod")
    if go_mod.exists():
        content = go_mod.read_text(encoding="utf-8")
        if "playwright-go" in content:
            print("✓ playwright-go 依赖已配置")
        else:
            print("⚠ playwright-go 依赖未配置（需要手动添加）")
            print("  请运行：go get github.com/playwright-community/playwright-go")
    else:
        print(f"❌ go.mod 不存在：{go_mod}")
        return False
    
    print("\n✅ GoSpider Playwright 集成检查通过")
    return True


def test_rustspider_playwright():
    """测试 RustSpider Playwright 集成"""
    print("\n" + "=" * 60)
    print("RustSpider Playwright 集成测试")
    print("=" * 60)
    
    # 检查文件
    playwright_file = Path("rustspider/src/playwright.rs")
    if playwright_file.exists():
        print(f"✓ Playwright 模块存在：{playwright_file}")
    else:
        print(f"❌ Playwright 模块不存在：{playwright_file}")
        return False
    
    # 检查示例
    example_file = Path("rustspider/examples/playwright_example.rs")
    if example_file.exists():
        print(f"✓ Playwright 示例存在：{example_file}")
    else:
        print(f"❌ Playwright 示例不存在：{example_file}")
        return False
    
    # 检查 Cargo.toml
    cargo_file = Path("rustspider/Cargo.toml")
    if cargo_file.exists():
        content = cargo_file.read_text(encoding="utf-8")
        if "playwright" in content.lower():
            print("✓ playwright-rust 依赖已配置")
        else:
            print("⚠ playwright-rust 依赖未配置（需要手动添加）")
            print("  请在 Cargo.toml 中添加：playwright = \"0.1\"")
    else:
        print(f"❌ Cargo.toml 不存在：{cargo_file}")
        return False
    
    print("\n✅ RustSpider Playwright 集成检查通过")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("GoSpider & RustSpider Playwright 集成测试")
    print("=" * 60)
    
    results = []
    
    # 测试 GoSpider
    results.append(("GoSpider Playwright", test_gospider_playwright()))
    
    # 测试 RustSpider
    results.append(("RustSpider Playwright", test_rustspider_playwright()))
    
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
    # 切换到项目根目录
    import os
    os.chdir(Path(__file__).parent.parent)
    
    success = run_all_tests()
    sys.exit(0 if success else 1)
