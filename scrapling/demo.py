"""
Scrapling 示例代码
隐身高性能爬虫，集成反爬机制
安装: pip install scrapling
"""
from scrapling import Fetcher

def main():
    fetcher = Fetcher()
    page = fetcher.fetch('https://example.com')
    
    # 使用CSS选择器提取数据
    title = page.css_first('title')
    if title:
        print("标题:", title.text())
    
    # 提取所有链接
    links = page.css('a')
    print(f"找到 {len(links)} 个链接")

if __name__ == "__main__":
    main()
