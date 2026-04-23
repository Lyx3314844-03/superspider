#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
京东 iPhone 17 价格爬虫 (Playwright 版)

使用 Playwright 模拟真实浏览器爬取京东平台上所有 iPhone 17 相关商品信息
包括：商品名称、价格、店铺、评价数、商品链接等

使用方法:
    python spider_jd_iphone17_playwright.py
"""

import json
import csv
import time
import re
import random
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from playwright.async_api import async_playwright, Browser, BrowserContext, Page


# ========== 数据模型 ==========


@dataclass
class Product:
    """商品数据模型"""
    
    product_id: str
    name: str
    price: float
    original_price: float
    currency: str
    url: str
    image_url: str
    shop_name: str
    shop_type: str  # 自营/第三方
    comment_count: int
    good_rate: float  # 好评率
    brand: str
    category: str
    tags: List[str]
    crawl_time: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ========== 爬虫类 ==========


class JDiPhone17SpiderPlaywright:
    """京东 iPhone 17 商品爬虫 (Playwright 版)"""

    # 搜索关键词列表
    KEYWORDS = ["iPhone 17", "苹果17", "Apple iPhone 17"]

    CONFIG = {
        "max_pages": 5,     # 爬取页数
        "delay": 2.0,       # 请求间隔（秒）
        "timeout": 30000,   # 页面加载超时（毫秒）
    }

    OUTPUT_CONFIG = {
        "save_json": True,
        "save_csv": True,
        "output_dir": "output/jd_iphone17",
    }

    def __init__(self):
        # 结果存储
        self.products: List[Product] = []
        self.seen_ids: set = set()  # 去重

        # 统计信息
        self.stats = {
            "products": 0,
            "pages": 0,
            "errors": 0,
        }

        # 输出目录
        self.output_dir = Path(self.OUTPUT_CONFIG["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        print("=" * 60)
        print("京东 iPhone 17 价格爬虫 (Playwright 版)")
        print("=" * 60)
        print(f"延迟：{self.CONFIG['delay']}秒")
        print(f"最大页数：{self.CONFIG['max_pages']}")
        print(f"关键词数：{len(self.KEYWORDS)}")
        print("=" * 60)

    async def init_browser(self) -> BrowserContext:
        """初始化浏览器"""
        playwright = await async_playwright().start()
        
        # 启动浏览器（带更多反反爬配置）
        browser = await playwright.chromium.launch(
            headless=True,  # 无头模式
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )
        
        # 创建浏览器上下文
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
        )
        
        # 隐藏 webdriver 特征
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // 修改 chrome 对象
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // 修改 plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // 修改 languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
        """)
        
        return context, browser

    async def search_and_parse(self, context: BrowserContext, keyword: str, page_num: int) -> List[Product]:
        """搜索并解析结果"""
        products = []
        
        page = await context.new_page()
        
        try:
            # 构建搜索 URL
            skip = (page_num - 1) * 30 + 1
            url = f"https://search.jd.com/Search?keyword={keyword}&enc=utf-8&wq={keyword}&s={skip}"
            
            print(f"  正在访问: {url[:80]}...")
            
            # 访问页面
            await page.goto(url, wait_until='networkidle', timeout=self.CONFIG['timeout'])
            
            # 等待商品列表加载
            await page.wait_for_selector('#J_goodsList .gl-item', timeout=10000)
            
            # 等待一下让动态内容加载
            await page.wait_for_timeout(2000)
            
            # 滚动页面加载更多内容
            await page.evaluate("""
                window.scrollTo(0, document.body.scrollHeight / 2);
            """)
            await page.wait_for_timeout(1000)
            await page.evaluate("""
                window.scrollTo(0, document.body.scrollHeight);
            """)
            await page.wait_for_timeout(1000)
            
            # 获取商品列表
            goods_items = await page.query_selector_all('#J_goodsList .gl-item')
            
            if not goods_items:
                print(f"  未找到商品列表")
                return products
            
            print(f"  找到 {len(goods_items)} 个商品")
            
            for item in goods_items:
                try:
                    # 提取商品ID
                    product_id = await item.get_attribute('data-pid')
                    
                    if not product_id:
                        # 尝试从链接提取
                        link_elem = await item.query_selector('.p-name a')
                        if link_elem:
                            href = await link_elem.get_attribute('href')
                            if href:
                                match = re.search(r'(\d+)\.html', href)
                                product_id = match.group(1) if match else None
                    
                    if not product_id:
                        continue
                    
                    # 去重
                    if product_id in self.seen_ids:
                        continue
                    
                    # 提取商品名称
                    name = ""
                    name_elem = await item.query_selector('.p-name em') or await item.query_selector('.p-name a')
                    if name_elem:
                        name = await name_elem.inner_text()
                        name = name.strip()
                    
                    # 过滤非 iPhone 17 相关商品
                    name_lower = name.lower()
                    if not any(kw.lower() in name_lower for kw in ['iphone 17', 'iphone17', '苹果17', 'apple 17']):
                        continue
                    
                    # 提取价格
                    price = 0.0
                    price_elem = await item.query_selector('.p-price strong') or await item.query_selector('.p-price')
                    if price_elem:
                        price_text = await price_elem.inner_text()
                        price_text = price_text.strip()
                        match = re.search(r'[\d.]+', price_text)
                        if match:
                            price = float(match.group())
                    
                    # 提取链接
                    link = f'https://item.jd.com/{product_id}.html'
                    link_elem = await item.query_selector('.p-name a')
                    if link_elem:
                        href = await link_elem.get_attribute('href')
                        if href:
                            if href.startswith('//'):
                                link = 'https:' + href
                            elif href.startswith('http'):
                                link = href
                    
                    # 提取店铺名称
                    shop_name = ""
                    shop_elem = await item.query_selector('.p-shop a') or await item.query_selector('.p-shop span')
                    if shop_elem:
                        shop_name = await shop_elem.inner_text()
                        shop_name = shop_name.strip()
                    
                    # 判断是否自营
                    shop_text = ""
                    shop_parent = await item.query_selector('.p-shop')
                    if shop_parent:
                        shop_text = await shop_parent.inner_text()
                    shop_type = "自营" if "自营" in shop_text else "第三方"
                    
                    # 提取评论数
                    comment_count = 0
                    comment_elem = await item.query_selector('.p-commit strong a')
                    if comment_elem:
                        comment_text = await comment_elem.inner_text()
                        comment_count = self.parse_number(comment_text)
                    
                    # 提取图片
                    image_url = ""
                    img_elem = await item.query_selector('.p-img img')
                    if img_elem:
                        image_url = await img_elem.get_attribute('data-lazy-img') or await img_elem.get_attribute('src') or ""
                    if image_url and image_url.startswith('//'):
                        image_url = 'https:' + image_url
                    
                    # 提取标签
                    tags = []
                    tag_elems = await item.query_selector_all('.p-icons i')
                    for tag_elem in tag_elems:
                        tag_text = await tag_elem.inner_text()
                        if tag_text.strip():
                            tags.append(tag_text.strip())
                    
                    self.seen_ids.add(product_id)
                    
                    product = Product(
                        product_id=product_id,
                        name=name,
                        price=price,
                        original_price=0.0,
                        currency="¥",
                        url=link,
                        image_url=image_url,
                        shop_name=shop_name,
                        shop_type=shop_type,
                        comment_count=comment_count,
                        good_rate=0.0,
                        brand="Apple",
                        category="手机通讯",
                        tags=tags,
                        crawl_time=datetime.now().isoformat(),
                    )
                    
                    products.append(product)
                    
                except Exception as e:
                    print(f"  解析商品失败: {e}")
                    self.stats["errors"] += 1
            
        except Exception as e:
            print(f"  搜索页面访问失败: {e}")
            self.stats["errors"] += 1
        finally:
            await page.close()
        
        return products

    def parse_number(self, text: str) -> int:
        """解析数字字符串（如 '10万+' -> 100000）"""
        if not text:
            return 0
        
        match = re.search(r'[\d.]+', text)
        if not match:
            return 0
        
        number = float(match.group())
        
        if '万' in text:
            number *= 10000
        elif '亿' in text:
            number *= 100000000
        
        return int(number)

    async def run(self):
        """运行爬虫"""
        print("\n开始爬取...")
        
        # 初始化浏览器
        context, browser = await self.init_browser()
        
        try:
            # 先访问京东首页获取 cookie
            print("\n正在初始化浏览器...")
            page = await context.new_page()
            await page.goto('https://www.jd.com', wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            await page.close()
            print("已获取京东 cookie")
            
            for keyword in self.KEYWORDS:
                print(f"\n{'=' * 40}")
                print(f"搜索关键词: {keyword}")
                print(f"{'=' * 40}")
                
                for page_num in range(1, self.CONFIG["max_pages"] + 1):
                    print(f"\n  爬取第 {page_num} 页...")
                    
                    # 搜索并解析
                    products = await self.search_and_parse(context, keyword, page_num)
                    
                    if not products:
                        print(f"  第 {page_num} 页未找到 iPhone 17 相关商品")
                        break
                    
                    # 保存结果
                    for p in products:
                        self.products.append(p)
                        self.stats["products"] += 1
                    
                    self.stats["pages"] += 1
                    
                    print(f"  第 {page_num} 页: 新增 {len(products)} 个商品，累计 {self.stats['products']} 个")
                    
                    # 随机延迟
                    delay = self.CONFIG["delay"] + random.uniform(1.0, 3.0)
                    print(f"  等待 {delay:.1f} 秒...")
                    await asyncio.sleep(delay)
        
        finally:
            await browser.close()

    def save_results(self):
        """保存结果"""
        print(f"\n{'=' * 60}")
        print(f"保存 {len(self.products)} 个商品数据...")
        print(f"{'=' * 60}")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存商品
        if self.OUTPUT_CONFIG["save_json"]:
            filepath = self.output_dir / f"jd_iphone17_{timestamp}.json"
            json_data = [item.to_dict() for item in self.products]
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ 已保存 JSON: {filepath}")

        if self.OUTPUT_CONFIG["save_csv"]:
            filepath = self.output_dir / f"jd_iphone17_{timestamp}.csv"
            
            if self.products:
                fieldnames = list(self.products[0].to_dict().keys())
                
                with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for item in self.products:
                        row = item.to_dict()
                        # 列表转字符串
                        if "tags" in row:
                            row["tags"] = "; ".join(row["tags"])
                        writer.writerow(row)
                
                print(f"✓ 已保存 CSV: {filepath}")

    def print_stats(self):
        """打印统计信息"""
        print(f"\n{'=' * 60}")
        print("爬取统计信息")
        print(f"{'=' * 60}")
        print(f"商品总数：{self.stats['products']}")
        print(f"爬取页数：{self.stats['pages']}")
        print(f"错误次数：{self.stats['errors']}")

        # 价格统计
        if self.products:
            prices = [p.price for p in self.products if p.price > 0]
            if prices:
                print(f"\n价格统计:")
                print(f"  最低价：¥{min(prices):.2f}")
                print(f"  最高价：¥{max(prices):.2f}")
                print(f"  平均价：¥{sum(prices)/len(prices):.2f}")
            
            # 店铺统计
            shops = set(p.shop_name for p in self.products if p.shop_name)
            print(f"\n店铺统计:")
            print(f"  店铺总数：{len(shops)}")
            
            self_count = sum(1 for p in self.products if p.shop_type == "自营")
            third_count = sum(1 for p in self.products if p.shop_type == "第三方")
            print(f"  自营商品：{self_count}")
            print(f"  第三方商品：{third_count}")
            
            # 评论统计
            comments = [p.comment_count for p in self.products if p.comment_count > 0]
            if comments:
                print(f"\n评论统计:")
                print(f"  最多评论：{max(comments)}")
                print(f"  平均评论：{sum(comments)/len(comments):.0f}")
            
            # 打印价格前10的商品
            print(f"\n价格最低的10个商品:")
            sorted_products = sorted(self.products, key=lambda x: x.price if x.price > 0 else float('inf'))
            for i, p in enumerate(sorted_products[:10], 1):
                price_str = f"¥{p.price:.2f}" if p.price > 0 else "价格未知"
                print(f"  {i}. {price_str} - {p.name[:50]} ({p.shop_type})")
        else:
            print("\n未获取到商品数据。")

        print(f"{'=' * 60}")


# ========== 主函数 ==========


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("京东 iPhone 17 价格爬虫 v3.0.0 (Playwright)")
    print("目标：爬取京东所有苹果17的价格信息")
    print("=" * 60 + "\n")

    # 创建爬虫
    spider = JDiPhone17SpiderPlaywright()

    # 运行爬虫
    try:
        await spider.run()
    except KeyboardInterrupt:
        print("\n用户中断爬取")
    except Exception as e:
        print(f"爬虫运行失败：{e}")
        import traceback
        traceback.print_exc()
    finally:
        # 保存结果
        spider.save_results()
        
        # 打印统计
        spider.print_stats()

    print("\n爬虫运行完成！")


if __name__ == "__main__":
    asyncio.run(main())
