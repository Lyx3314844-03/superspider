# Curlconverter 集成说明

本目录下的四个爬虫框架都已集成 curlconverter 功能，可以将 curl 命令转换为对应语言的代码。

## 什么是 curlconverter？

curlconverter 是一个强大的工具，可以将 curl 命令转换为多种编程语言的代码，包括：
- Python (requests, aiohttp)
- Go (net/http, go-resty)
- Rust (reqwest, ureq)
- Java (HttpURLConnection, OkHttp, Apache HttpClient)

## 安装依赖

在使用之前，需要安装 curlconverter CLI 工具：

```bash
# 使用 npm 全局安装（推荐）
npm install -g curlconverter

# Windows 用户可以运行安装脚本
cd C:\Users\Administrator\spider
install_curlconverter.bat
```

## 已修复的问题

在代码审查过程中，我们修复了以下问题：

1. **Python 框架**：
   - ✅ 修复了逻辑运算符优先级错误
   - ✅ 移除了未使用的 import
   - ✅ 优化了 Windows 平台兼容性

2. **Go 框架**：
   - ✅ 添加了 `-` 参数以从 stdin 读取
   - ✅ 实现了回退机制（直接调用 -> npx）

3. **Rust 框架**：
   - ✅ 添加了 `-` 参数以从 stdin 读取
   - ✅ 实现了回退机制
   - ✅ 修复了 encrypted/crawler.rs 中的编译错误

4. **Java 框架**：
   - ✅ 添加了 `-` 参数以从 stdin 读取
   - ✅ 实现了回退机制
   - ✅ 优化了错误处理

## 各框架使用说明

### 1. Python 框架 (pyspider)

**文件位置**: `spider/pyspider/core/curlconverter.py`

**使用示例**:

```python
from core.curlconverter import CurlToPythonConverter

# 创建转换器
converter = CurlToPythonConverter()

# 转换 curl 命令
curl_cmd = 'curl -X GET "https://httpbin.org/get" -H "Accept: application/json"'
python_code = converter.convert(curl_cmd)

print(python_code)

# 或者使用便捷函数
from core.curlconverter import curl_to_python_requests
code = curl_to_python_requests(curl_cmd)
```

**功能**:
- `convert()`: 基本转换功能
- `convert_to_requests()`: 转换为 requests 代码
- `convert_to_aiohttp()`: 转换为 aiohttp 异步代码
- `install_curlconverter()`: 安装依赖

---

### 2. Go 框架 (gospider)

**文件位置**: `spider/gospider/core/curlconverter.go`

**使用示例**:

```go
package main

import (
    "fmt"
    "your-project/core"
)

func main() {
    // 创建转换器
    converter := core.NewCurlToGoConverter()
    
    // 转换 curl 命令
    curlCmd := `curl -X GET "https://httpbin.org/get" -H "Accept: application/json"`
    
    goCode, err := converter.Convert(curlCmd)
    if err != nil {
        fmt.Println("转换失败:", err)
        return
    }
    
    fmt.Println(goCode)
    
    // 或者使用便捷函数
    code, _ := core.CurlToGo(curlCmd)
    fmt.Println(code)
}
```

**功能**:
- `Convert()`: 基本转换功能
- `ConvertToHTTP()`: 转换为 net/http 代码
- `ConvertToResty()`: 转换为 go-resty 代码
- `InstallCurlconverter()`: 安装 CLI 工具

---

### 3. Rust 框架 (rustspider)

**文件位置**: `spider/rustspider/src/curlconverter.rs`

**使用示例**:

```rust
use rustspider::curlconverter::{CurlToRustConverter, curl_to_rust};

fn main() {
    // 创建转换器
    let converter = CurlToRustConverter::new();
    
    // 转换 curl 命令
    let curl_cmd = r#"curl -X GET "https://httpbin.org/get" -H "Accept: application/json""#;
    
    match converter.convert(curl_cmd) {
        Ok(rust_code) => println!("{}", rust_code),
        Err(e) => eprintln!("转换失败: {}", e),
    }
    
    // 或者使用便捷函数
    match curl_to_rust(curl_cmd) {
        Ok(code) => println!("{}", code),
        Err(e) => eprintln!("转换失败: {}", e),
    }
    
    // 转换为 reqwest 代码
    match converter.convert_to_reqwest(curl_cmd) {
        Ok(code) => println!("{}", code),
        Err(e) => eprintln!("转换失败: {}", e),
    }
    
    // 转换为 ureq 代码（同步）
    let ureq_code = converter.convert_to_ureq(curl_cmd);
    println!("{}", ureq_code);
}
```

**功能**:
- `convert()`: 基本转换功能
- `convert_to_reqwest()`: 转换为 reqwest 异步代码
- `convert_to_ureq()`: 转换为 ureq 同步代码
- `install_curlconverter()`: 安装 CLI 工具

---

### 4. Java 框架 (javaspider)

**文件位置**: `spider/javaspider/src/main/java/com/spider/converter/CurlToJavaConverter.java`

**使用示例**:

```java
import com.spider.converter.CurlToJavaConverter;

public class Main {
    public static void main(String[] args) {
        // 创建转换器
        CurlToJavaConverter converter = new CurlToJavaConverter();
        
        // 转换 curl 命令
        String curlCmd = "curl -X GET \"https://httpbin.org/get\" -H \"Accept: application/json\"";
        
        try {
            // 基本转换
            String javaCode = converter.convert(curlCmd);
            System.out.println(javaCode);
            
            // 转换为 HttpURLConnection
            String httpURLCode = converter.convertToHttpURLConnection(curlCmd);
            System.out.println(httpURLCode);
            
            // 转换为 OkHttp
            String okHttpCode = converter.convertToOkHttp(curlCmd);
            System.out.println(okHttpCode);
            
            // 转换为 Apache HttpClient
            String apacheCode = converter.convertToApacheHttpClient(curlCmd);
            System.out.println(apacheCode);
            
        } catch (IOException e) {
            e.printStackTrace();
        }
        
        // 或者使用便捷函数
        String code = CurlToJavaConverter.curlToJava(curlCmd);
        System.out.println(code);
    }
}
```

**功能**:
- `convert()`: 基本转换功能
- `convertToHttpURLConnection()`: 转换为 HttpURLConnection
- `convertToOkHttp()`: 转换为 OkHttp
- `convertToApacheHttpClient()`: 转换为 Apache HttpClient
- `installCurlconverter()`: 安装 CLI 工具

---

## 支持的 curl 选项

所有框架都支持以下 curl 选项的转换：

- `-X, --request`: HTTP 方法 (GET, POST, PUT, DELETE 等)
- `-H, --header`: 请求头
- `-d, --data`: 请求体数据
- `-F, --form`: 表单数据
- `-u, --user`: 基本认证
- `-b, --cookie`: Cookie
- `-c, --cookie-jar`: Cookie 保存
- `--compressed`: 压缩
- `-L, --location`: 跟随重定向
- `-k, --insecure`: 跳过 SSL 验证
- `-A, --user-agent`: User-Agent
- `-e, --referer`: Referer
- `-o, --output`: 输出到文件
- `-O, --remote-name`: 远程文件名

## 示例转换

### GET 请求

```bash
curl -X GET "https://api.example.com/users" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer token123"
```

### POST 请求

```bash
curl -X POST "https://api.example.com/users" \
  -H "Content-Type: application/json" \
  -d '{"name": "John", "email": "john@example.com"}'
```

### 带认证和 Cookie

```bash
curl -X GET "https://api.example.com/protected" \
  -u "username:password" \
  -b "session=abc123" \
  -H "Accept: application/json"
```

## 注意事项

1. **依赖安装**: 确保已安装 `curlconverter` CLI 工具 (`npm install -g curlconverter`)
2. **网络要求**: 首次使用可能需要下载依赖
3. **复杂命令**: 某些复杂的 curl 选项可能不完全支持，需要手动调整
4. **错误处理**: 转换失败时会返回错误信息，请检查 curl 命令格式
5. **代码优化**: 转换后的代码可能需要根据具体场景进行优化

## 常见问题

### Q: 转换失败怎么办？

A: 检查以下几点：
- 是否安装了 curlconverter (`npm list -g curlconverter`)
- curl 命令格式是否正确
- 是否有网络连接

### Q: 支持哪些 HTTP 客户端库？

A:
- **Python**: requests, aiohttp
- **Go**: net/http, go-resty
- **Rust**: reqwest, ureq
- **Java**: HttpURLConnection, OkHttp, Apache HttpClient

### Q: 可以批量转换吗？

A: 可以，在代码中循环调用转换函数即可。

## 贡献

如果你发现转换有问题，或者想添加更多功能，欢迎提交 PR！

---

**更新时间**: 2026-04-07
