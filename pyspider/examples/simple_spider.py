#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PySpider 简单爬虫示例

最简单的爬虫脚本，适合初学者

运行：python simple_spider.py
"""

from pyspider.core import Spider, Request


class SimpleSpider(Spider):
    """简单爬虫"""
    
    def __init__(self):
        super().__init__(name="SimpleSpider")
        
        # 添加起始 URL
        self.add_request(
            Request(
                url="https://example.com",
                callback=self.parse
            )
        )
    
    def parse(self, page):
        """解析页面"""
        # 提取标题
        title = page.response.css('title::text').get()
        
        # 提取所有链接
        links = page.response.css('a::attr(href)').getall()
        
        # 输出结果
        print(f"\n标题：{title}")
        print(f"链接数：{len(links)}")
        
        # 返回数据
        return {
            'url': page.response.url,
            'title': title,
            'links_count': len(links),
        }


if __name__ == '__main__':
    spider = SimpleSpider()
    spider.run()
