"""
ScrapeGraphAI 示例代码
AI驱动的网页抓取，支持多种LLM
安装: pip install scrapegraphai
"""
from scrapegraphai.graphs import SmartScraperGraph

def main():
    graph_config = {
        "llm": {
            "model": "openai/gpt-4o-mini",
            "api_key": "YOUR_API_KEY",  # 替换为你的API密钥
        },
        "verbose": True,
        "headless": True,
    }

    scraper = SmartScraperGraph(
        prompt="提取网页的主要内容，包括标题和描述",
        source="https://example.com",
        config=graph_config
    )

    result = scraper.run()
    print(result)

if __name__ == "__main__":
    main()
