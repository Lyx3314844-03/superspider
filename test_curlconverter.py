#!/usr/bin/env python3
"""
curlconverter 集成测试脚本
测试四个爬虫框架的 curlconverter 功能
"""

import os
import sys
import subprocess

def test_python_framework():
    """测试 Python 框架的 curlconverter"""
    print("=" * 60)
    print("测试 Python 框架 (pyspider)")
    print("=" * 60)
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pyspider'))
        from core.curlconverter import CurlToPythonConverter
        
        converter = CurlToPythonConverter()
        curl_cmd = 'curl -X GET "https://httpbin.org/get" -H "Accept: application/json"'
        
        result = converter.convert(curl_cmd)
        if result:
            print("✓ Python 框架转换成功")
            print("转换结果预览:")
            print(result[:200] + "..." if len(result) > 200 else result)
            return True
        else:
            print("✗ Python 框架转换失败")
            return False
    except Exception as e:
        print(f"✗ Python 框架测试出错: {e}")
        return False

def test_go_framework():
    """测试 Go 框架的 curlconverter"""
    print("\n" + "=" * 60)
    print("测试 Go 框架 (gospider)")
    print("=" * 60)
    
    go_file = os.path.join(os.path.dirname(__file__), 'gospider', 'core', 'curlconverter.go')
    if os.path.exists(go_file):
        print("✓ Go 框架 curlconverter 文件存在")
        print("文件路径:", go_file)
        return True
    else:
        print("✗ Go 框架 curlconverter 文件不存在")
        return False

def test_rust_framework():
    """测试 Rust 框架的 curlconverter"""
    print("\n" + "=" * 60)
    print("测试 Rust 框架 (rustspider)")
    print("=" * 60)
    
    rust_file = os.path.join(os.path.dirname(__file__), 'rustspider', 'src', 'curlconverter.rs')
    lib_file = os.path.join(os.path.dirname(__file__), 'rustspider', 'src', 'lib.rs')
    
    if os.path.exists(rust_file):
        print("✓ Rust 框架 curlconverter 文件存在")
        print("文件路径:", rust_file)
        
        # 检查是否已在 lib.rs 中注册
        with open(lib_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'curlconverter' in content:
                print("✓ curlconverter 模块已在 lib.rs 中注册")
                return True
            else:
                print("✗ curlconverter 模块未在 lib.rs 中注册")
                return False
    else:
        print("✗ Rust 框架 curlconverter 文件不存在")
        return False

def test_java_framework():
    """测试 Java 框架的 curlconverter"""
    print("\n" + "=" * 60)
    print("测试 Java 框架 (javaspider)")
    print("=" * 60)
    
    java_file = os.path.join(os.path.dirname(__file__), 'javaspider', 'src', 'main', 'java', 
                            'com', 'spider', 'converter', 'CurlToJavaConverter.java')
    
    if os.path.exists(java_file):
        print("✓ Java 框架 curlconverter 文件存在")
        print("文件路径:", java_file)
        return True
    else:
        print("✗ Java 框架 curlconverter 文件不存在")
        return False

def check_curlconverter_installed():
    """检查 curlconverter 是否已安装"""
    print("=" * 60)
    print("检查 curlconverter 安装状态")
    print("=" * 60)
    
    # 检查 npm 版本
    try:
        result = subprocess.run(['npx', 'curlconverter', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✓ Node.js curlconverter 已安装")
            print("版本:", result.stdout.strip())
        else:
            print("✗ Node.js curlconverter 未安装或不可用")
    except Exception as e:
        print(f"✗ 检查 Node.js curlconverter 失败: {e}")
    
    # 检查 Python 版本
    try:
        import curlconverter
        print("✓ Python curlconverter 已安装")
    except ImportError:
        print("✗ Python curlconverter 未安装")
        print("  安装命令: pip install curlconverter")

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Curlconverter 集成测试")
    print("=" * 60 + "\n")
    
    # 检查安装
    check_curlconverter_installed()
    
    # 测试各框架
    results = []
    results.append(("Python", test_python_framework()))
    results.append(("Go", test_go_framework()))
    results.append(("Rust", test_rust_framework()))
    results.append(("Java", test_java_framework()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{name:10s}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\n总计: {passed}/{total} 个框架测试通过")
    
    if passed == total:
        print("\n🎉 所有框架的 curlconverter 集成成功！")
        print("\n使用说明:")
        print("1. 确保已安装 curlconverter: npm install -g curlconverter")
        print("2. 参考 CURLCONVERTER_README.md 了解详细用法")
        print("3. 各框架的转换文件位置:")
        print("   - Python: spider/pyspider/core/curlconverter.py")
        print("   - Go:     spider/gospider/core/curlconverter.go")
        print("   - Rust:   spider/rustspider/src/curlconverter.rs")
        print("   - Java:   spider/javaspider/src/main/java/com/spider/converter/CurlToJavaConverter.java")
    else:
        print(f"\n⚠️  有 {total - passed} 个框架测试未通过，请检查")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
