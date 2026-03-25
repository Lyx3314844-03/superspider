#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GoSpider 和 RustSpider 浏览器功能测试

由于 Go 和 Rust 需要编译环境，这里提供测试框架和示例
"""

import subprocess
import sys
from pathlib import Path

def test_gospider():
    """测试 GoSpider 浏览器功能"""
    print("\n" + "=" * 60)
    print("GoSpider 浏览器功能测试")
    print("=" * 60)
    
    # 检查 Go 环境
    try:
        result = subprocess.run(["go", "version"], capture_output=True, text=True, timeout=10)
        print(f"✓ Go 环境：{result.stdout.strip()}")
    except Exception as e:
        print(f"❌ Go 环境检查失败：{e}")
        return False
    
    # 检查文件
    browser_file = Path("gospider/browser/browser.go")
    if browser_file.exists():
        print(f"✓ 浏览器模块存在：{browser_file}")
    else:
        print(f"❌ 浏览器模块不存在：{browser_file}")
        return False
    
    # 尝试编译
    print("\n尝试编译 GoSpider...")
    try:
        result = subprocess.run(
            ["go", "build", "./..."],
            cwd="gospider",
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✓ GoSpider 编译成功")
            return True
        else:
            print(f"❌ GoSpider 编译失败：{result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 编译异常：{e}")
        return False


def test_rustspider():
    """测试 RustSpider 浏览器功能"""
    print("\n" + "=" * 60)
    print("RustSpider 浏览器功能测试")
    print("=" * 60)
    
    # 检查 Rust 环境
    try:
        result = subprocess.run(["rustc", "--version"], capture_output=True, text=True, timeout=10)
        print(f"✓ Rust 环境：{result.stdout.strip()}")
    except Exception as e:
        print(f"❌ Rust 环境检查失败：{e}")
        return False
    
    # 检查文件
    browser_file = Path("rustspider/src/browser.rs")
    if browser_file.exists():
        print(f"✓ 浏览器模块存在：{browser_file}")
    else:
        print(f"❌ 浏览器模块不存在：{browser_file}")
        return False
    
    # 检查 Cargo.toml
    cargo_file = Path("rustspider/Cargo.toml")
    if cargo_file.exists():
        print(f"✓ Cargo 配置存在：{cargo_file}")
        
        # 检查是否包含 fantoccini 依赖
        content = cargo_file.read_text(encoding="utf-8")
        if "fantoccini" in content:
            print("✓ fantoccini 依赖已配置")
        else:
            print("⚠ fantoccini 依赖未配置（可选）")
    else:
        print(f"❌ Cargo 配置不存在：{cargo_file}")
        return False
    
    # 尝试编译
    print("\n尝试编译 RustSpider...")
    try:
        result = subprocess.run(
            ["cargo", "check"],
            cwd="rustspider",
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            print("✓ RustSpider 编译成功")
            return True
        else:
            print(f"❌ RustSpider 编译失败：{result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 编译异常：{e}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("GoSpider & RustSpider 浏览器功能测试")
    print("=" * 60)
    
    results = []
    
    # 测试 GoSpider
    results.append(("GoSpider", test_gospider()))
    
    # 测试 RustSpider
    results.append(("RustSpider", test_rustspider()))
    
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
