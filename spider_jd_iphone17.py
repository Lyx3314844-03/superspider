#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
京东 iPhone 17 价格爬虫

使用 requests + BeautifulSoup 爬取京东平台上所有 iPhone 17 相关商品信息
包括：商品名称、价格、店铺、评价数、商品链接等

使用方法:
    python spider_jd_iphone17.py
"""

import json
import csv
import time
import re
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

import requests
from bs4 import BeautifulSoup


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


class JDiPhone17Spider:
    """京东 iPhone 17 商品爬虫"""

    # 搜索关键词列表
    KEYWORDS = ["iPhone 17", "iPhone17", "苹果17", "Apple iPhone 17"]
    
    # 价格 API
    PRICE_API = "https://p.3.cn/prices/mgets"
    
    # 搜索 API (移动端)
    SEARCH_API = "https://api.m.jd.com/api"

    CONFIG = {
        "max_pages": 5,     # 爬取页数
        "delay": 2.0,       # 请求间隔（秒）
        "timeout": 15,
        "retry": 2,         # 重试次数
    }

    OUTPUT_CONFIG = {
        "save_json": True,
        "save_csv": True,
        "output_dir": "output/jd_iphone17",
    }

    # 请求头配置 - 模拟移动端
    HEADERS_MOBILE = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://so.m.jd.com/",
    }

    # 请求头配置 - 模拟PC浏览器
    HEADERS_PC = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.jd.com/",
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

        # Session
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS_PC)
        
        # 先访问京东首页获取 cookie
        self._init_cookies()

        print("=" * 60)
        print("京东 iPhone 17 价格爬虫")
        print("=" * 60)
        print(f"延迟：{self.CONFIG['delay']}秒")
        print(f"最大页数：{self.CONFIG['max_pages']}")
        print(f"关键词数：{len(self.KEYWORDS)}")
        print("=" * 60)

    def _init_cookies(self):
        """初始化 cookies"""
        try:
            # 访问多个页面获取完整 cookie
            urls = [
                "https://www.jd.com",
                "https://search.jd.com",
            ]
            for url in urls:
                self.session.get(url, timeout=10)
            print("已获取京东 cookie")
        except Exception as e:
            print(f"获取 cookie 失败: {e}")

    def search_jd_mobile(self, keyword: str, page: int = 1) -> Optional[str]:
        """使用移动端搜索获取结果"""
        url = "https://so.m.jd.com/ware/search.action"
        params = {
            "keyword": keyword,
            "page": page,
            "sort_type": "sort_totalsales15_desc",
        }
        
        try:
            # 切换到移动端 headers
            old_headers = self.session.headers.get("User-Agent")
            self.session.headers.update(self.HEADERS_MOBILE)
            
            response = self.session.get(url, params=params, timeout=self.CONFIG["timeout"])
            response.raise_for_status()
            
            # 恢复 PC headers
            if old_headers:
                self.session.headers["User-Agent"] = old_headers
                
            return response.text
        except Exception as e:
            print(f"  移动端搜索失败: {e}")
            return None
        finally:
            # 确保恢复 PC headers
            self.session.headers.update(self.HEADERS_PC)

    def get_prices(self, sk_ids: List[str]) -> Dict[str, float]:
        """批量获取商品价格"""
        if not sk_ids:
            return {}
        
        # 分批获取（每批最多50个）
        all_prices = {}
        batch_size = 50
        
        for i in range(0, len(sk_ids), batch_size):
            batch = sk_ids[i:i + batch_size]
            try:
                params = {
                    "type": 1,
                    "area": "1_72_4137_0",
                    "skuIds": ",".join(batch),
                }
                response = self.session.get(
                    self.PRICE_API,
                    params=params,
                    timeout=self.CONFIG["timeout"]
                )
                response.raise_for_status()
                
                for item in response.json():
                    sku_id = item.get("id", "")
                    # 价格可能是 p 或 m 字段
                    price_str = item.get("p", item.get("m", "0"))
                    try:
                        price = float(price_str) if price_str else 0.0
                    except (ValueError, TypeError):
                        price = 0.0
                    all_prices[sku_id] = price
                    
                # 批次间延迟
                time.sleep(0.5)
            except Exception as e:
                print(f"  获取价格批次失败: {e}")
                self.stats["errors"] += 1
        
        return all_prices

    def parse_mobile_page(self, html: str) -> List[Product]:
        """解析移动端搜索结果页"""
        products = []
        soup = BeautifulSoup(html, "html.parser")
        
        # 移动端商品列表选择器
        goods_list = soup.select('.ware-item') or soup.select('.J_pinglan')
        
        if not goods_list:
            # 尝试更多选择器
            goods_list = soup.select('[class*="ware"]') or soup.select('[class*="item"]')
        
        if not goods_list:
            print("  未找到商品列表")
            return products

        print(f"  找到 {len(goods_list)} 个商品")

        # 收集所有商品ID用于批量获取价格
        sk_ids = []
        product_data = []
        
        for item in goods_list:
            try:
                # 提取商品ID
                sk_id = ""
                
                # 方法1: data-sku 属性
                sk_id = item.get("data-sku", "")
                
                # 方法2: 从链接提取
                if not sk_id:
                    link_elem = item.select_one('a')
                    if link_elem:
                        href = link_elem.get("href", "")
                        match = re.search(r'(\d+)\.html', href)
                        sk_id = match.group(1) if match else ""
                
                # 方法3: 从 class 提取
                if not sk_id:
                    match = re.search(r'ware-item-(\d+)', item.get("class", [""])[0] if item.get("class") else "")
                    sk_id = match.group(1) if match else ""
                
                if not sk_id or not sk_id.isdigit():
                    continue
                    
                sk_ids.append(sk_id)
                product_data.append(item)
            except Exception as e:
                print(f"  提取商品ID失败: {e}")
                self.stats["errors"] += 1

        # 批量获取价格
        prices = self.get_prices(sk_ids)

        # 解析每个商品
        for i, item in enumerate(product_data):
            try:
                sk_id = sk_ids[i] if i < len(sk_ids) else ""
                
                # 去重
                if sk_id in self.seen_ids:
                    continue
                self.seen_ids.add(sk_id)

                # 提取商品名称
                name = ""
                name_elem = item.select_one('.p-name') or item.select_one('[class*="name"]') or item.select_one('a')
                if name_elem:
                    name = name_elem.get_text(strip=True)
                
                # 过滤非 iPhone 17 相关商品
                name_lower = name.lower()
                if not any(kw.lower() in name_lower for kw in ['iphone 17', 'iphone17', '苹果17', 'apple 17', 'apple/苹果']):
                    continue

                # 提取价格（从API获取）
                price = prices.get(sk_id, 0.0)
                original_price = 0.0

                # 提取商品链接
                link = ""
                link_elem = item.select_one('a')
                if link_elem:
                    link = link_elem.get("href", "")
                if link and link.startswith('//'):
                    link = 'https:' + link
                elif link and not link.startswith('http'):
                    link = f'https://item.jd.com/{sk_id}.html'
                if not link:
                    link = f'https://item.jd.com/{sk_id}.html'

                # 提取店铺名称
                shop_name = ""
                shop_elem = item.select_one('.p-shop') or item.select_one('[class*="shop"]') or item.select_one('[class*="store"]')
                if shop_elem:
                    shop_name = shop_elem.get_text(strip=True)

                # 判断是否自营
                shop_text = item.get_text()
                shop_type = "自营" if "自营" in shop_text else "第三方"

                # 提取评论数
                comment_count = 0
                comment_elem = item.select_one('.p-commit') or item.select_one('[class*="comment"]') or item.select_one('[class*="pinglun"]')
                if comment_elem:
                    comment_text = comment_elem.get_text(strip=True)
                    comment_count = self.parse_number(comment_text)

                # 提取图片
                image_url = ""
                img_elem = item.select_one('img')
                if img_elem:
                    image_url = img_elem.get("data-lazy-img", "") or img_elem.get("data-src", "") or img_elem.get("src", "")
                if image_url and image_url.startswith('//'):
                    image_url = 'https:' + image_url

                # 提取标签
                tags = []
                for tag_elem in item.select('.p-icons i') or item.select('[class*="icon"]'):
                    tag_text = tag_elem.get_text(strip=True)
                    if tag_text:
                        tags.append(tag_text)

                product = Product(
                    product_id=sk_id,
                    name=name,
                    price=price,
                    original_price=original_price,
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

    def run(self):
        """运行爬虫"""
        print("\n开始爬取...")
        
        for keyword in self.KEYWORDS:
            print(f"\n{'=' * 40}")
            print(f"搜索关键词: {keyword}")
            print(f"{'=' * 40}")
            
            for page in range(1, self.CONFIG["max_pages"] + 1):
                print(f"\n  爬取第 {page} 页...")
                
                # 获取页面 (使用移动端搜索)
                html = self.search_jd_mobile(keyword, page)
                if not html:
                    print(f"  第 {page} 页获取失败")
                    break
                
                # 解析页面
                products = self.parse_mobile_page(html)
                
                if not products:
                    print(f"  第 {page} 页未找到 iPhone 17 相关商品")
                    break
                
                # 保存结果
                new_count = 0
                for p in products:
                    if p.product_id not in self.seen_ids:
                        self.products.append(p)
                        self.stats["products"] += 1
                        new_count += 1
                
                self.stats["pages"] += 1
                
                print(f"  第 {page} 页: 新增 {new_count} 个商品，累计 {self.stats['products']} 个")
                
                # 随机延迟
                delay = self.CONFIG["delay"] + random.uniform(1.0, 2.0)
                print(f"  等待 {delay:.1f} 秒...")
                time.sleep(delay)

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
            print("提示：京东有较强的反爬机制，可能需要：")
            print("  1. 手动登录后将 cookie 添加到代码中")
            print("  2. 使用代理 IP")
            print("  3. 使用 Selenium/Playwright 模拟真实浏览器")

        print(f"{'=' * 60}")


# ========== 主函数 ==========


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("京东 iPhone 17 价格爬虫 v2.1.0")
    print("目标：爬取京东所有苹果17的价格信息")
    print("=" * 60 + "\n")

    # 创建爬虫
    spider = JDiPhone17Spider()

    # 运行爬虫
    try:
        spider.run()
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
    main()
