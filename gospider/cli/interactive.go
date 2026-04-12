package cli

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

// InteractiveCLI 交互式命令行
type InteractiveCLI struct {
	// spider 字段暂时保留，待爬虫逻辑集成时使用
}

// NewInteractiveCLI 创建交互式 CLI
func NewInteractiveCLI() *InteractiveCLI {
	return &InteractiveCLI{}
}

// Run 运行交互式模式
func (cli *InteractiveCLI) Run() {
	fmt.Println("🕷️  GoSpider Interactive Mode")
	fmt.Println("=============================")

	reader := bufio.NewReader(os.Stdin)

	for {
		fmt.Print("\n> ")
		input, err := reader.ReadString('\n')
		if err != nil {
			// EOF 或 stdin 关闭时退出
			fmt.Println("\n👋 Goodbye!")
			return
		}
		input = strings.TrimSpace(input)

		switch {
		case input == "help":
			cli.showHelp()
		case strings.HasPrefix(input, "crawl "):
			url := strings.TrimPrefix(input, "crawl ")
			cli.startCrawl(url)
		case strings.HasPrefix(input, "config "):
			key, value := cli.parseConfig(input)
			cli.setConfig(key, value)
		case input == "status":
			cli.showStatus()
		case input == "quit" || input == "exit":
			fmt.Println("👋 Goodbye!")
			return
		default:
			fmt.Println("Unknown command. Type 'help' for commands.")
		}
	}
}

func (cli *InteractiveCLI) showHelp() {
	fmt.Println(`Available Commands:
  crawl <url>      - Start crawling a URL
  config <k> <v>   - Set configuration
  status           - Show current status
  help             - Show this help
  quit/exit        - Exit`)
}

func (cli *InteractiveCLI) startCrawl(url string) {
	fmt.Printf("🚀 Starting crawl: %s\n", url)
	// Actual crawl logic here
}

func (cli *InteractiveCLI) parseConfig(input string) (string, string) {
	parts := strings.SplitN(strings.TrimPrefix(input, "config "), " ", 2)
	if len(parts) == 2 {
		return parts[0], parts[1]
	}
	return "", ""
}

func (cli *InteractiveCLI) setConfig(key, value string) {
	fmt.Printf("⚙️  Set %s = %s\n", key, value)
}

func (cli *InteractiveCLI) showStatus() {
	fmt.Println("📊 Status: Idle")
}
