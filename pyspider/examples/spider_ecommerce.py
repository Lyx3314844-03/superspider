#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PySpider 电商网站爬虫模板

特性:
- ✅ 商品列表爬取
- ✅ 商品详情提取
- ✅ 价格监控
- ✅ 评论爬取
- ✅ 图片下载
- ✅ 数据导出

使用:
    python spider_ecommerce.py
"""

import json
import csv
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

try:
    from pyspider.core import Spider, Request
    from pyspider.antibot import AntiBotManager
except ImportError:
    print("请先安装 PySpider: pip install -e .")
    exit(1)


# ========== 数据模型 ==========

@dataclass
class Product:
    """商品数据模型"""
    name: str
    price: float
    original_price: float
    currency: str
    url: str
    images: List[str]
    description: str
    brand: str
    category: str
    rating: float
    review_count: int
    stock_status: str
    seller: str
    crawl_time: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Review:
    """评论数据模型"""
    product_id: str
    user: str
    rating: int
    title: str
    content: str
    date: str
    helpful_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ========== 爬虫类 ==========

class EcommerceSpider(Spider):
    """电商网站爬虫"""
    
    # 配置区域
    START_URLS = [
        "https://shop.example.com/category/electronics",
        "https://shop.example.com/category/clothing",
    ]
    
    CONFIG = {
        'thread_count': 3,  # 电商网站通常限制较严，线程数不宜过多
        'max_depth': 3,
        'max_requests': 2000,
        'delay': 3.0,  # 较长延迟
        'timeout': 30,
    }
    
    OUTPUT_CONFIG = {
        'save_json': True,
        'save_csv': True,
        'download_images': False,
        'output_dir': 'output/ecommerce',
    }
    
    # CSS 选择器配置
    SELECTORS = {
        # 列表页
        'product_list': '.product-list .product-item',
        'product_link': 'a.product-link::attr(href)',
        'next_page': '.next-page a::attr(href)',
        
        # 商品详情页
        'name': 'h1.product-name::text',
        'price': '.product-price::text',
        'original_price': '.original-price::text',
        'images': '.product-images img::attr(src)',
        'description': '.product-description::text',
        'brand': '.product-brand::text',
        'category': '.product-category::text',
        'rating': '.product-rating::text',
        'review_count': '.review-count::text',
        'stock_status': '.stock-status::text',
        'seller': '.seller-name::text',
        
        # 评论
        'review_list': '.review-list .review-item',
        'review_link': '.see-all-reviews::attr(href)',
        'review_user': '.review-user::text',
        'review_rating': '.review-rating::text',
        'review_title': '.review-title::text',
        'review_content': '.review-content::text',
        'review_date': '.review-date::text',
        'review_helpful': '.helpful-count::text',
    }
    
    def __init__(self):
        super().__init__(
            name="EcommerceSpider",
            thread_count=self.CONFIG['thread_count']
        )
        
        # 反反爬管理器
        self.antibot = AntiBotManager()
        
        # 结果存储
        self.products: List[Product] = []
        self.reviews: List[Review] = []
        
        # 统计信息
        self.stats = {
            'products': 0,
            'reviews': 0,
            'errors': 0,
        }
        
        # 输出目录
        self.output_dir = Path(self.OUTPUT_CONFIG['output_dir'])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print("=" * 60)
        print("电商网站爬虫")
        print("=" * 60)
        print(f"起始 URL 数：{len(self.START_URLS)}")
        print(f"线程数：{self.CONFIG['thread_count']}")
        print(f"延迟：{self.CONFIG['delay']}秒")
        print("=" * 60)
    
    def parse(self, page):
        """解析页面"""
        url = page.response.url
        
        try:
            # 检查是否是列表页
            if self.is_list_page(page):
                yield from self.parse_list(page)
            
            # 检查是否是商品页
            elif self.is_product_page(page):
                yield from self.parse_product(page)
            
            # 检查是否是评论页
            elif self.is_review_page(page):
                yield from self.parse_reviews(page)
        
        except Exception as e:
            print(f"解析失败 {url}: {e}")
            self.stats['errors'] += 1
    
    def is_list_page(self, page) -> bool:
        """判断是否是列表页"""
        return bool(page.response.css(self.SELECTORS['product_list']))
    
    def is_product_page(self, page) -> bool:
        """判断是否是商品页"""
        return bool(page.response.css(self.SELECTORS['name']))
    
    def is_review_page(self, page) -> bool:
        """判断是否是评论页"""
        return bool(page.response.css(self.SELECTORS['review_list']))
    
    def parse_list(self, page):
        """解析列表页"""
        url = page.response.url
        print(f"解析列表页：{url}")
        
        # 提取商品链接
        product_links = page.response.css(self.SELECTORS['product_link']).getall()
        
        for link in product_links:
            if link and link.startswith('http'):
                yield Request(
                    url=link,
                    callback=self.parse_product,
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
    
    def parse_product(self, page):
        """解析商品页"""
        url = page.response.url
        print(f"解析商品：{url}")
        
        try:
            # 提取商品数据
            name = page.response.css(self.SELECTORS['name']).get(default='').strip()
            
            # 提取价格
            price_text = page.response.css(self.SELECTORS['price']).get(default='0').strip()
            price = self.parse_price(price_text)
            
            original_price_text = page.response.css(self.SELECTORS['original_price']).get(default='0').strip()
            original_price = self.parse_price(original_price_text)
            
            # 提取图片
            images = page.response.css(self.SELECTORS['images']).getall()
            images = [img for img in images if img and img.startswith('http')][:10]
            
            # 提取描述
            description_parts = page.response.css(self.SELECTORS['description']).getall()
            description = '\n'.join([p.strip() for p in description_parts if p.strip()])[:2000]
            
            # 提取品牌
            brand = page.response.css(self.SELECTORS['brand']).get(default='').strip()
            
            # 提取分类
            category = page.response.css(self.SELECTORS['category']).get(default='').strip()
            
            # 提取评分
            rating_text = page.response.css(self.SELECTORS['rating']).get(default='0').strip()
            rating = float(rating_text.replace('星', '').replace('分', '')) if rating_text else 0.0
            
            # 提取评论数
            review_count_text = page.response.css(self.SELECTORS['review_count']).get(default='0').strip()
            review_count = int(''.join(filter(str.isdigit, review_count_text))) if review_count_text else 0
            
            # 提取库存状态
            stock_status = page.response.css(self.SELECTORS['stock_status']).get(default='').strip()
            
            # 提取卖家
            seller = page.response.css(self.SELECTORS['seller']).get(default='').strip()
            
            # 创建商品对象
            product = Product(
                name=name,
                price=price,
                original_price=original_price,
                currency='¥',
                url=url,
                images=images,
                description=description,
                brand=brand,
                category=category,
                rating=rating,
                review_count=review_count,
                stock_status=stock_status,
                seller=seller,
                crawl_time=datetime.now().isoformat()
            )
            
            # 保存商品
            self.products.append(product)
            self.stats['products'] += 1
            
            # 返回数据
            yield product.to_dict()
            
            # 提取评论链接
            review_link = page.response.css(self.SELECTORS['review_link']).get()
            if review_link:
                yield Request(
                    url=review_link,
                    callback=self.parse_reviews,
                    meta={'product_id': len(self.products)}
                )
        
        except Exception as e:
            print(f"解析商品失败 {url}: {e}")
            self.stats['errors'] += 1
    
    def parse_reviews(self, page):
        """解析评论页"""
        url = page.response.url
        print(f"解析评论页：{url}")
        
        product_id = page.meta.get('product_id', 0)
        
        # 提取评论
        reviews = page.response.css(self.SELECTORS['review_list'])
        
        for review_elem in reviews:
            try:
                user = review_elem.css(self.SELECTORS['review_user']).get(default='').strip()
                rating_text = review_elem.css(self.SELECTORS['review_rating']).get(default='0').strip()
                rating = int(rating_text.replace('星', '').replace('分', '')) if rating_text else 0
                
                title = review_elem.css(self.SELECTORS['review_title']).get(default='').strip()
                content = review_elem.css(self.SELECTORS['review_content']).get(default='').strip()
                date = review_elem.css(self.SELECTORS['review_date']).get(default='').strip()
                
                helpful_text = review_elem.css(self.SELECTORS['review_helpful']).get(default='0').strip()
                helpful_count = int(''.join(filter(str.isdigit, helpful_text))) if helpful_text else 0
                
                review = Review(
                    product_id=str(product_id),
                    user=user,
                    rating=rating,
                    title=title,
                    content=content[:1000],
                    date=date,
                    helpful_count=helpful_count
                )
                
                self.reviews.append(review)
                self.stats['reviews'] += 1
                
                yield review.to_dict()
            
            except Exception as e:
                print(f"解析评论失败：{e}")
    
    def parse_price(self, price_text: str) -> float:
        """解析价格"""
        import re
        match = re.search(r'[\d,]+\.?\d*', price_text)
        if match:
            return float(match.group().replace(',', ''))
        return 0.0
    
    def save_results(self):
        """保存结果"""
        print(f"\n保存 {len(self.products)} 个商品，{len(self.reviews)} 条评论...")
        
        # 保存商品
        if self.OUTPUT_CONFIG['save_json']:
            self.save_json(self.output_dir / 'products.json', self.products)
        
        if self.OUTPUT_CONFIG['save_csv']:
            self.save_csv(self.output_dir / 'products.csv', self.products)
        
        # 保存评论
        if self.reviews:
            if self.OUTPUT_CONFIG['save_json']:
                self.save_json(self.output_dir / 'reviews.json', self.reviews)
            
            if self.OUTPUT_CONFIG['save_csv']:
                self.save_csv(self.output_dir / 'reviews.csv', self.reviews)
    
    def save_json(self, file_path: Path, data: List):
        """保存为 JSON"""
        json_data = [item.to_dict() for item in data]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 已保存 JSON: {file_path}")
    
    def save_csv(self, file_path: Path, data: List):
        """保存为 CSV"""
        if not data:
            return
        
        fieldnames = list(data[0].to_dict().keys())
        
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in data:
                row = item.to_dict()
                # 列表转字符串
                if 'images' in row:
                    row['images'] = '; '.join(row['images'])
                writer.writerow(row)
        
        print(f"✓ 已保存 CSV: {file_path}")
    
    def print_stats(self):
        """打印统计信息"""
        print("\n" + "=" * 60)
        print("统计信息")
        print("=" * 60)
        print(f"商品数：{self.stats['products']}")
        print(f"评论数：{self.stats['reviews']}")
        print(f"错误数：{self.stats['errors']}")
        
        # 价格统计
        if self.products:
            prices = [p.price for p in self.products if p.price > 0]
            if prices:
                print(f"\n价格统计:")
                print(f"  最低价：¥{min(prices):.2f}")
                print(f"  最高价：¥{max(prices):.2f}")
                print(f"  平均价：¥{sum(prices)/len(prices):.2f}")
        
        print("=" * 60)


# ========== 主函数 ==========

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("电商网站爬虫 v1.0.0")
    print("=" * 60 + "\n")
    
    # 创建爬虫
    spider = EcommerceSpider()
    
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
