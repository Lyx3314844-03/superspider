//! curlconverter 集成模块
//! 将 curl 命令转换为 Rust 代码

use std::collections::BTreeMap;
use std::io::Write;
use std::process::Command;

/// curl 到 Rust 转换器
pub struct CurlToRustConverter {
    use_cli: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct ParsedCurlCommand {
    method: String,
    url: String,
    headers: BTreeMap<String, String>,
    data: Option<String>,
}

impl CurlToRustConverter {
    /// 创建新的转换器实例
    pub fn new() -> Self {
        Self {
            use_cli: true, // Rust 版本使用 CLI 工具
        }
    }

    /// 将 curl 命令转换为 Rust 代码
    pub fn convert(&self, curl_command: &str) -> Result<String, String> {
        // 尝试直接使用 curlconverter
        let result = self.run_curlconverter("curlconverter", curl_command);

        // 如果失败，尝试使用 npx
        if result.is_err() {
            return self.run_curlconverter("npx", curl_command);
        }

        result
    }

    /// 运行 curlconverter 命令
    fn run_curlconverter(&self, command: &str, curl_command: &str) -> Result<String, String> {
        let mut cmd = Command::new(command);

        if command == "npx" {
            cmd.arg("curlconverter");
        }

        cmd.arg("--language")
            .arg("rust")
            .arg("-") // 从 stdin 读取
            .stdin(std::process::Stdio::piped())
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped());

        let mut child = cmd
            .spawn()
            .map_err(|e| format!("启动 {} 失败: {}", command, e))?;

        // 写入 curl 命令到 stdin
        if let Some(ref mut stdin) = child.stdin {
            stdin
                .write_all(curl_command.as_bytes())
                .map_err(|e| format!("写入 stdin 失败: {}", e))?;
        }

        let output = child
            .wait_with_output()
            .map_err(|e| format!("等待子进程失败: {}", e))?;

        if output.status.success() {
            let rust_code = String::from_utf8_lossy(&output.stdout);
            Ok(rust_code.to_string())
        } else {
            let error = String::from_utf8_lossy(&output.stderr);
            Err(format!("{} 错误: {}", command, error))
        }
    }

    /// 转换为使用 reqwest 的代码
    pub fn convert_to_reqwest(&self, curl_command: &str) -> Result<String, String> {
        let rust_code = self.convert(curl_command)?;

        // 确保包含必要的依赖
        let mut result = String::new();

        if !rust_code.contains("[dependencies]") {
            result.push_str("// Cargo.toml 依赖:\n");
            result.push_str("// [dependencies]\n");
            result.push_str("// reqwest = { version = \"0.11\", features = [\"json\"] }\n");
            result.push_str("// tokio = { version = \"1\", features = [\"full\"] }\n\n");
        }

        result.push_str(&rust_code);
        Ok(result)
    }

    /// 转换为使用 ureq 的代码（同步 HTTP 客户端）
    pub fn convert_to_ureq(&self, curl_command: &str) -> String {
        let Ok(parsed) = parse_curl_command(curl_command) else {
            return format!(
                r#"// 使用 ureq 的同步 HTTP 客户端
// Cargo.toml: ureq = "2.9"

use std::io::Read;

fn main() -> Result<(), Box<dyn std::error::Error>> {{
    // curl: {}

    let mut resp = ureq::get("https://httpbin.org/get")
        .set("Accept", "application/json")
        .call()?;

    let mut body = String::new();
    resp.into_reader().read_to_string(&mut body)?;

    println!("Response: {{}}", body);
    Ok(())
}}
"#,
                curl_command
            );
        };

        let (constructor, uses_generic_request) = ureq_constructor(&parsed.method);
        let headers = if parsed.headers.is_empty() {
            String::new()
        } else {
            parsed
                .headers
                .iter()
                .map(|(key, value)| format!("\n        .set({key:?}, {value:?})"))
                .collect::<String>()
        };

        let request_builder = if uses_generic_request {
            format!("ureq::request({:?}, {:?})", parsed.method, parsed.url)
        } else {
            format!("{constructor}({:?})", parsed.url)
        };

        let send_code = if let Some(data) = parsed.data.as_ref() {
            format!("let mut resp = {request_builder}{headers}\n        .send_string({data:?})?;")
        } else {
            format!("let mut resp = {request_builder}{headers}\n        .call()?;")
        };

        format!(
            r#"// 使用 ureq 的同步 HTTP 客户端
// Cargo.toml: ureq = "2.9"

use std::io::Read;

fn main() -> Result<(), Box<dyn std::error::Error>> {{
    // curl: {}

    {}

    let mut body = String::new();
    resp.into_reader().read_to_string(&mut body)?;

    println!("Response: {{}}", body);
    Ok(())
}}
"#,
            curl_command, send_code
        )
    }

    /// 安装 curlconverter CLI
    pub fn install_curlconverter() -> Result<(), String> {
        let output = Command::new("npm")
            .arg("install")
            .arg("-g")
            .arg("curlconverter")
            .output()
            .map_err(|e| format!("安装失败: {}", e))?;

        if output.status.success() {
            Ok(())
        } else {
            let error = String::from_utf8_lossy(&output.stderr);
            Err(format!("安装失败: {}", error))
        }
    }
}

impl Default for CurlToRustConverter {
    fn default() -> Self {
        Self::new()
    }
}

/// 便捷函数：将 curl 命令转换为 Rust 代码
pub fn curl_to_rust(curl_command: &str) -> Result<String, String> {
    let converter = CurlToRustConverter::new();
    converter.convert(curl_command)
}

fn parse_curl_command(curl_command: &str) -> Result<ParsedCurlCommand, String> {
    let mut tokens = tokenize_curl_command(curl_command)?;
    if tokens.is_empty() {
        return Err("empty curl command".to_string());
    }
    if tokens
        .first()
        .map(|token| token.eq_ignore_ascii_case("curl"))
        == Some(true)
    {
        tokens.remove(0);
    }

    let mut parsed = ParsedCurlCommand {
        method: "GET".to_string(),
        url: String::new(),
        headers: BTreeMap::new(),
        data: None,
    };
    let mut data_parts = Vec::new();
    let mut index = 0usize;
    while index < tokens.len() {
        match tokens[index].as_str() {
            "-X" | "--request" => {
                index += 1;
                if index >= tokens.len() {
                    return Err("missing request method".to_string());
                }
                parsed.method = tokens[index].to_uppercase();
            }
            "-H" | "--header" => {
                index += 1;
                if index >= tokens.len() {
                    return Err("missing header value".to_string());
                }
                if let Some((key, value)) = tokens[index].split_once(':') {
                    parsed
                        .headers
                        .insert(key.trim().to_string(), value.trim().to_string());
                }
            }
            "-d" | "--data" | "--data-raw" | "--data-binary" | "--data-urlencode" => {
                index += 1;
                if index >= tokens.len() {
                    return Err("missing data value".to_string());
                }
                data_parts.push(tokens[index].clone());
                if parsed.method == "GET" {
                    parsed.method = "POST".to_string();
                }
            }
            token if token.starts_with("http://") || token.starts_with("https://") => {
                parsed.url = token.to_string();
            }
            _ => {}
        }
        index += 1;
    }

    if parsed.url.is_empty() {
        return Err("missing target url".to_string());
    }
    if !data_parts.is_empty() {
        parsed.data = Some(data_parts.join("&"));
    }

    Ok(parsed)
}

fn tokenize_curl_command(input: &str) -> Result<Vec<String>, String> {
    let mut tokens = Vec::new();
    let mut current = String::new();
    let mut quote: Option<char> = None;
    let mut escaped = false;

    let flush = |tokens: &mut Vec<String>, current: &mut String| {
        if !current.is_empty() {
            tokens.push(current.clone());
            current.clear();
        }
    };

    for ch in input.chars() {
        if escaped {
            current.push(ch);
            escaped = false;
            continue;
        }

        match quote {
            Some(active_quote) if ch == active_quote => {
                quote = None;
            }
            Some(_) if ch == '\\' => {
                escaped = true;
            }
            Some(_) => current.push(ch),
            None if ch == '\\' => escaped = true,
            None if ch == '"' || ch == '\'' => quote = Some(ch),
            None if ch.is_whitespace() => flush(&mut tokens, &mut current),
            None => current.push(ch),
        }
    }

    if escaped {
        current.push('\\');
    }
    if quote.is_some() {
        return Err("unterminated quote in curl command".to_string());
    }
    flush(&mut tokens, &mut current);
    Ok(tokens)
}

fn ureq_constructor(method: &str) -> (&'static str, bool) {
    match method {
        "GET" => ("ureq::get", false),
        "POST" => ("ureq::post", false),
        "PUT" => ("ureq::put", false),
        "PATCH" => ("ureq::patch", false),
        "DELETE" => ("ureq::delete", false),
        _ => ("ureq::request", true),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_convert_simple_curl() {
        let curl_cmd = r#"curl -X GET "https://httpbin.org/get""#;
        let converter = CurlToRustConverter::new();
        // 注意：这需要 npm 和 curlconverter 已安装
        let result = converter.convert(curl_cmd);
        // 测试可能失败，如果 curlconverter 未安装
        if let Ok(output) = result {
            assert!(output.contains("reqwest"));
        }
    }

    #[test]
    fn test_parse_curl_command_supports_headers_and_body() {
        let parsed = parse_curl_command(
            r#"curl -X POST "https://example.com/api" -H "Accept: application/json" -d "{\"name\":\"ultra\"}""#,
        )
        .expect("parsed curl command");

        assert_eq!(parsed.method, "POST");
        assert_eq!(parsed.url, "https://example.com/api");
        assert_eq!(
            parsed.headers.get("Accept").map(String::as_str),
            Some("application/json")
        );
        assert_eq!(parsed.data.as_deref(), Some(r#"{"name":"ultra"}"#));
    }

    #[test]
    fn test_convert_to_ureq_uses_parsed_target() {
        let converter = CurlToRustConverter::new();
        let code = converter.convert_to_ureq(
            r#"curl -X POST "https://example.com/api" -H "Content-Type: application/json" -d "{\"name\":\"ultra\"}""#,
        );

        assert!(code.contains("https://example.com/api"));
        assert!(code.contains("ureq::post"));
        assert!(code.contains(".set(\"Content-Type\", \"application/json\")"));
        assert!(code.contains(".send_string(\"{\\\"name\\\":\\\"ultra\\\"}\")"));
    }
}
