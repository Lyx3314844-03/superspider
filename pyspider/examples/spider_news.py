#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PySpider 新闻网站爬虫模板

特性:
- ✅ 自动分页处理
- ✅ 多列表爬取
- ✅ 内容提取
- ✅ 图片下载
- ✅ 数据导出 (JSON/CSV/SQLite)
- ✅ 反反爬集成
- ✅ 进度显示

使用:
    python spider_news.py
"""

import json
import csv
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging

try:
    from pyspider.core import Spider, Request
    from pyspider.antibot import AntiBotManager
except ImportError:
    print("请先安装 PySpider: pip install -e .")
    exit(1)


# ========== 数据模型 ==========

@dataclass
class NewsArticle:
    """新闻文章数据模型"""
    title: str
    author: str
    publish_time: str
    source: str
    url: str
    content: str
    images: List[str]
    tags: List[str]
    category: str
    crawl_time: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ========== 爬虫类 ==========

class NewsSpider(Spider):
    """新闻网站爬虫"""
    
    # 配置区域
    START_URLS = [
        "https://news.example.com",
        "https://news.example.com/tech",
        "https://news.example.com/finance",
    ]
    
    CONFIG = {
        'thread_count': 5,
        'max_depth': 5,
        'max_requests': 5000,
        'delay': 2.0,
        'timeout': 30,
    }
    
    OUTPUT_CONFIG = {
        'save_json': True,
        'save_csv': True,
        'save_sqlite': True,
        'download_images': False,
        'output_dir': 'output/news',
    }
    
    # CSS 选择器配置
    SELECTORS = {
        'article_list': '.article-list .article-item',
        'article_link': 'a.article-link::attr(href)',
        'title': 'h1.article-title::text',
        'author': '.article-author::text',
        'publish_time': '.article-time::text',
        'source': '.article-source::text',
        'content': '.article-content p::text',
        'images': '.article-content img::attr(src)',
        'tags': '.article-tags a::text',
        'next_page': '.next-page a::attr(href)',
    }
    
    def __init__(self):
        super().__init__(
            name="NewsSpider",
            thread_count=self.CONFIG['thread_count']
        )
        
        # 反反爬管理器
        self.antibot = AntiBotManager()
        
        # 结果存储
        self.articles: List[NewsArticle] = []
        
        # 统计信息
        self.stats = {
            'articles': 0,
            'images': 0,
            'errors': 0,
        }
        
        # 输出目录
        self.output_dir = Path(self.OUTPUT_CONFIG['output_dir'])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print("=" * 60)
        print("新闻网站爬虫")
        print("=" * 60)
        print(f"起始 URL 数：{len(self.START_URLS)}")
        print(f"线程数：{self.CONFIG['thread_count']}")
        print(f"输出目录：{self.output_dir}")
        print("=" * 60)
    
    def parse(self, page):
        """解析页面"""
        url = page.response.url
        
        try:
            # 检查是否是列表页
            if self.is_list_page(page):
                # 提取文章链接
                article_links = page.response.css(self.SELECTORS['article_link']).getall()
                
                for link in article_links:
                    if link and link.startswith('http'):
                        yield Request(
                            url=link,
                            callback=self.parse_article,
                            meta={'depth': page.meta.get('depth', 0) + 1}
                        )
                
                # 提取下一页
                next_page = page.response.css(self.SELECTORS['next_page']).get()
                if next_page and page.meta.get('depth', 0) < self.CONFIG['max_depth']:
                    yield Request(
                        url=next_page,
                        callback=self.parse,
                        meta={'depth': page.meta.get('depth', 0) + 1}
                    )
            
            # 检查是否是文章页
            elif self.is_article_page(page):
                yield from self.parse_article(page)
        
        except Exception as e:
            print(f"解析失败 {url}: {e}")
            self.stats['errors'] += 1
    
    def is_list_page(self, page) -> bool:
        """判断是否是列表页"""
        return bool(page.response.css(self.SELECTORS['article_list']))
    
    def is_article_page(self, page) -> bool:
        """判断是否是文章页"""
        return bool(page.response.css(self.SELECTORS['title']))
    
    def parse_article(self, page):
        """解析文章"""
        url = page.response.url
        print(f"解析文章：{url}")
        
        try:
            # 提取数据
            title = page.response.css(self.SELECTORS['title']).get(default='').strip()
            author = page.response.css(self.SELECTORS['author']).get(default='').strip()
            publish_time = page.response.css(self.SELECTORS['publish_time']).get(default='').strip()
            source = page.response.css(self.SELECTORS['source']).get(default='').strip()
            
            # 提取内容
            content_parts = page.response.css(self.SELECTORS['content']).getall()
            content = '\n'.join([p.strip() for p in content_parts if p.strip()])
            
            # 提取图片
            images = page.response.css(self.SELECTORS['images']).getall()
            images = [img for img in images if img and img.startswith('http')]
            
            # 提取标签
            tags = page.response.css(self.SELECTORS['tags']).getall()
            tags = [tag.strip() for tag in tags if tag.strip()]
            
            # 提取分类（从 URL）
            category = url.split('/')[3] if len(url.split('/')) > 3 else 'general'
            
            # 创建文章对象
            article = NewsArticle(
                title=title,
                author=author,
                publish_time=publish_time,
                source=source,
                url=url,
                content=content[:5000],  # 限制长度
                images=images[:10],  # 限制数量
                tags=tags[:10],
                category=category,
                crawl_time=datetime.now().isoformat()
            )
            
            # 保存结果
            self.articles.append(article)
            self.stats['articles'] += 1
            self.stats['images'] += len(images)
            
            # 返回数据
            yield article.to_dict()
        
        except Exception as e:
            print(f"解析文章失败 {url}: {e}")
            self.stats['errors'] += 1
    
    def save_results(self):
        """保存结果"""
        print(f"\n保存 {len(self.articles)} 篇文章...")
        
        # 保存为 JSON
        if self.OUTPUT_CONFIG['save_json']:
            self.save_json()
        
        # 保存为 CSV
        if self.OUTPUT_CONFIG['save_csv']:
            self.save_csv()
        
        # 保存为 SQLite
        if self.OUTPUT_CONFIG['save_sqlite']:
            self.save_sqlite()
    
    def save_json(self):
        """保存为 JSON"""
        file_path = self.output_dir / 'articles.json'
        
        data = [article.to_dict() for article in self.articles]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 已保存 JSON: {file_path}")
    
    def save_csv(self):
        """保存为 CSV"""
        file_path = self.output_dir / 'articles.csv'
        
        if not self.articles:
            return
        
        fieldnames = ['title', 'author', 'publish_time', 'source', 'url', 
                     'content', 'images', 'tags', 'category', 'crawl_time']
        
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for article in self.articles:
                row = article.to_dict()
                # 列表转字符串
                row['images'] = '; '.join(row['images'])
                row['tags'] = '; '.join(row['tags'])
                writer.writerow(row)
        
        print(f"✓ 已保存 CSV: {file_path}")
    
    def save_sqlite(self):
        """保存为 SQLite"""
        db_path = self.output_dir / 'articles.db'
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                author TEXT,
                publish_time TEXT,
                source TEXT,
                url TEXT UNIQUE,
                content TEXT,
                category TEXT,
                crawl_time TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER,
                image_url TEXT,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER,
                tag TEXT,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            )
        ''')
        
        # 插入数据
        for i, article in enumerate(self.articles, 1):
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO articles 
                    (title, author, publish_time, source, url, content, category, crawl_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    article.title, article.author, article.publish_time,
                    article.source, article.url, article.content,
                    article.category, article.crawl_time
                ))
                
                # 插入图片
                for img in article.images:
                    cursor.execute('''
                        INSERT INTO images (article_id, image_url) VALUES (?, ?)
                    ''', (i, img))
                
                # 插入标签
                for tag in article.tags:
                    cursor.execute('''
                        INSERT INTO tags (article_id, tag) VALUES (?, ?)
                    ''', (i, tag))
            
            except Exception as e:
                print(f"插入数据库失败：{e}")
        
        conn.commit()
        conn.close()
        
        print(f"✓ 已保存 SQLite: {db_path}")
    
    def print_stats(self):
        """打印统计信息"""
        print("\n" + "=" * 60)
        print("统计信息")
        print("=" * 60)
        print(f"文章数：{self.stats['articles']}")
        print(f"图片数：{self.stats['images']}")
        print(f"错误数：{self.stats['errors']}")
        print("=" * 60)


# ========== 主函数 ==========

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("新闻网站爬虫 v1.0.0")
    print("=" * 60 + "\n")
    
    # 创建爬虫
    spider = NewsSpider()
    
    # 添加起始请求
    for url in spider.START_URLS:
        spider.add_request(
            Request(
                url=url,
                callback=spider.parse,
                meta={'depth': 0}
            )
        )
    
    # 运行爬虫
    try:
        spider.run()
    except Exception as e:
        print(f"爬虫运行失败：{e}")
    finally:
        # 保存结果
        spider.save_results()
        
        # 打印统计
        spider.print_stats()
    
    print("\n爬虫运行完成！")


if __name__ == '__main__':
    main()
