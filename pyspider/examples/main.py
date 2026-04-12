"""
pyspider 使用示例
"""

from pyspider.core.spider import Spider
from pyspider.core.models import Page
from pyspider.parser.parser import HTMLParser


def main():
    # 创建爬虫
    spider = (
        Spider("ExampleSpider")
        .set_start_urls("https://www.example.com")
        .set_thread_count(3)
        .add_pipeline(process_page)
    )

    # 启动爬虫
    spider.start()


def process_page(page: Page):
    """处理页面"""
    # 解析 HTML
    html_parser = HTMLParser(page.response.text)

    title = html_parser.title()
    links = html_parser.links()

    page.set_data("title", title)
    page.set_data("links", len(links))

    print(f"Title: {title}")
    print(f"Links: {len(links)}")


if __name__ == "__main__":
    main()
