package core

import (
	"bytes"
	"fmt"
	"os/exec"
	"sort"
	"strings"
)

// CurlToGoConverter 将 curl 命令转换为 Go 代码
type CurlToGoConverter struct {
	useCLI bool
}

type parsedCurlCommand struct {
	Method  string
	URL     string
	Headers map[string]string
	Data    string
}

// NewCurlToGoConverter 创建转换器
func NewCurlToGoConverter() *CurlToGoConverter {
	return &CurlToGoConverter{
		useCLI: true, // Go 版本主要使用 CLI 工具
	}
}

// Convert 将 curl 命令转换为 Go 代码
func (c *CurlToGoConverter) Convert(curlCommand string) (string, error) {
	// 使用 curlconverter 进行转换
	var cmd *exec.Cmd
	
	// 尝试直接使用 curlconverter（如果已全局安装）
	cmd = exec.Command("curlconverter", "--language", "go", "-")
	cmd.Stdin = strings.NewReader(curlCommand)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	if err != nil {
		// 如果失败，尝试使用 npx
		cmd = exec.Command("npx", "curlconverter", "--language", "go", "-")
		cmd.Stdin = strings.NewReader(curlCommand)
		cmd.Stdout = &stdout
		cmd.Stderr = &stderr
		stdout.Reset()
		stderr.Reset()
		
		err = cmd.Run()
		if err != nil {
			return "", fmt.Errorf("curlconverter 错误: %v, stderr: %s", err, stderr.String())
		}
	}

	return stdout.String(), nil
}

// ConvertToHTTP 转换为使用 net/http 的代码
func (c *CurlToGoConverter) ConvertToHTTP(curlCommand string) (string, error) {
	goCode, err := c.Convert(curlCommand)
	if err != nil {
		return "", err
	}
	
	// 添加必要的 import
	if !strings.Contains(goCode, "package") {
		goCode = "package main\n\n" + goCode
	}
	
	return goCode, nil
}

// ConvertToResty 转换为使用 go-resty 的代码（更简洁的 HTTP 客户端）
func (c *CurlToGoConverter) ConvertToResty(curlCommand string) string {
	parsed, err := parseCurlCommand(curlCommand)
	if err != nil {
		return fmt.Sprintf(`package main

import (
	"fmt"
	"github.com/go-resty/resty/v2"
)

func main() {
	client := resty.New()

	// 无法可靠解析 curl 命令，保留原始输入供人工调整。
	// curl: %s
	resp, err := client.R().
		Get("https://httpbin.org/get")

	if err != nil {
		fmt.Println("Error:", err)
		return
	}

	fmt.Println("Response:", resp.Status())
	fmt.Println("Body:", string(resp.Body()))
}
`, curlCommand)
	}

	var builder strings.Builder
	builder.WriteString("package main\n\n")
	builder.WriteString("import (\n")
	builder.WriteString("\t\"fmt\"\n")
	builder.WriteString("\t\"github.com/go-resty/resty/v2\"\n")
	builder.WriteString(")\n\n")
	builder.WriteString("func main() {\n")
	builder.WriteString("\tclient := resty.New()\n")
	builder.WriteString("\treq := client.R()\n")

	if len(parsed.Headers) > 0 {
		keys := make([]string, 0, len(parsed.Headers))
		for key := range parsed.Headers {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		builder.WriteString("\treq = req.SetHeaders(map[string]string{\n")
		for _, key := range keys {
			builder.WriteString(fmt.Sprintf("\t\t%q: %q,\n", key, parsed.Headers[key]))
		}
		builder.WriteString("\t})\n")
	}

	if parsed.Data != "" {
		builder.WriteString(fmt.Sprintf("\treq = req.SetBody(%q)\n", parsed.Data))
	}

	builder.WriteString(fmt.Sprintf("\tresp, err := req.Execute(%q, %q)\n", parsed.Method, parsed.URL))
	builder.WriteString("\tif err != nil {\n")
	builder.WriteString("\t\tfmt.Println(\"Error:\", err)\n")
	builder.WriteString("\t\treturn\n")
	builder.WriteString("\t}\n\n")
	builder.WriteString("\tfmt.Println(\"Response:\", resp.Status())\n")
	builder.WriteString("\tfmt.Println(\"Body:\", resp.String())\n")
	builder.WriteString("}\n")
	return builder.String()
}

// InstallCurlconverter 安装 curlconverter CLI 工具
func InstallCurlconverter() error {
	// 检查 npm 是否可用
	_, err := exec.LookPath("npm")
	if err != nil {
		return fmt.Errorf("npm 未安装: %v", err)
	}
	
	// 安装 curlconverter
	cmd := exec.Command("npm", "install", "-g", "curlconverter")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("安装失败: %v, output: %s", err, string(output))
	}
	
	return nil
}

// CurlToGo 便捷函数
func CurlToGo(curlCommand string) (string, error) {
	converter := NewCurlToGoConverter()
	return converter.Convert(curlCommand)
}

func parseCurlCommand(curlCommand string) (*parsedCurlCommand, error) {
	tokens, err := tokenizeCurlCommand(curlCommand)
	if err != nil {
		return nil, err
	}
	if len(tokens) == 0 {
		return nil, fmt.Errorf("empty curl command")
	}
	if strings.EqualFold(tokens[0], "curl") {
		tokens = tokens[1:]
	}

	parsed := &parsedCurlCommand{
		Method:  "GET",
		Headers: make(map[string]string),
	}
	var dataParts []string

	for i := 0; i < len(tokens); i++ {
		token := tokens[i]
		switch token {
		case "-X", "--request":
			if i+1 >= len(tokens) {
				return nil, fmt.Errorf("missing request method")
			}
			i++
			parsed.Method = strings.ToUpper(tokens[i])
		case "-H", "--header":
			if i+1 >= len(tokens) {
				return nil, fmt.Errorf("missing header value")
			}
			i++
			parts := strings.SplitN(tokens[i], ":", 2)
			if len(parts) == 2 {
				parsed.Headers[strings.TrimSpace(parts[0])] = strings.TrimSpace(parts[1])
			}
		case "-d", "--data", "--data-raw", "--data-binary", "--data-urlencode":
			if i+1 >= len(tokens) {
				return nil, fmt.Errorf("missing data value")
			}
			i++
			dataParts = append(dataParts, tokens[i])
			if parsed.Method == "GET" {
				parsed.Method = "POST"
			}
		default:
			if strings.HasPrefix(token, "http://") || strings.HasPrefix(token, "https://") {
				parsed.URL = token
			}
		}
	}

	if parsed.URL == "" {
		return nil, fmt.Errorf("missing target url")
	}
	if len(dataParts) > 0 {
		parsed.Data = strings.Join(dataParts, "&")
	}
	return parsed, nil
}

func tokenizeCurlCommand(input string) ([]string, error) {
	var tokens []string
	var current strings.Builder
	var quote rune
	escaped := false

	flush := func() {
		if current.Len() > 0 {
			tokens = append(tokens, current.String())
			current.Reset()
		}
	}

	for _, ch := range input {
		switch {
		case escaped:
			current.WriteRune(ch)
			escaped = false
		case ch == '\\':
			escaped = true
		case quote != 0:
			if ch == '\\' {
				escaped = true
			} else if ch == quote {
				quote = 0
			} else {
				current.WriteRune(ch)
			}
		case ch == '\'' || ch == '"':
			quote = ch
		case ch == ' ' || ch == '\t' || ch == '\n' || ch == '\r':
			flush()
		default:
			current.WriteRune(ch)
		}
	}

	if escaped {
		current.WriteRune('\\')
	}
	if quote != 0 {
		return nil, fmt.Errorf("unterminated quote in curl command")
	}
	flush()
	return tokens, nil
}
