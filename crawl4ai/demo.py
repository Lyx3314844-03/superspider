"""
Crawl4AI 示例代码
AI驱动的网页爬虫，支持动态JS渲染
安装: pip install crawl4ai
"""
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://example.com",
        )
        print("标题:", result.markdown[:200])
        print("状态:", result.success)

if __name__ == "__main__":
    asyncio.run(main())
