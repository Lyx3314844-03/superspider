#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
京东 iPhone 17 价格爬虫 - PySpider 框架

使用 PySpider 框架爬取京东所有 iPhone 17 相关商品价格

运行: python spider_jd_iphone17.py [--pages 5] [--delay 3] [--proxy http://127.0.0.1:7890]
"""

import json
import csv
import sys
import re
import time
import random
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from urllib.parse import quote

# 将父目录的父目录加入 path 以便导入 pyspider
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pyspider import Spider, Request


@dataclass
class iPhone17Product:
    """iPhone 17 商品数据模型"""
    product_id: str
    name: str
    price: float
    original_price: float
    currency: str
    url: str
    image_url: str
    shop_name: str
    shop_type: str
    comment_count: int
    crawl_time: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class JDiPhone17Spider(Spider):
    """京东 iPhone 17 价格爬虫 - PySpider 版本"""

    def __init__(self, pages=5, delay=3.0, proxy=None):
        super().__init__(name="JDiPhone17Spider")
        self.max_pages = pages
        self.delay = delay
        self.proxy = proxy
        self.products: List[iPhone17Product] = []
        self.seen_ids: set = set()
        self.crawl_stats = {"pages": 0, "products": 0, "errors": 0}

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.jd.com/",
        }

        print("=" * 60)
        print("PySpider - 京东 iPhone 17 价格爬虫")
        print("=" * 60)
        print(f"爬取页数: {self.max_pages}")
        print(f"请求延迟: {self.delay}s")
        if self.proxy:
            print(f"代理: {self.proxy}")
        print("=" * 60)

        # 添加起始请求
        self.add_request(Request(
            url=self._build_search_url("iPhone 17", page=1),
            callback=self.parse_search,
            headers=self.headers,
            meta={"keyword": "iPhone 17", "page": 1},
        ))

    def _build_search_url(self, keyword: str, page: int) -> str:
        skip = (page - 1) * 30
        return f"https://search.jd.com/Search?keyword={quote(keyword)}&enc=utf-8&wq={quote(keyword)}&s={skip}&page={page}"

    def _build_price_api_url(self, skuids: List[str]) -> str:
        ids = ",".join([f"{s}" for s in skuids])
        return f"https://p.3.cn/prices/mgets?skuIds={ids}&type=1&area=1_72_4137_0"

    def parse_search(self, page):
        """解析搜索结果页"""
        keyword = page.meta.get("keyword", "iPhone 17")
        current_page = page.meta.get("page", 1)
        self.crawl_stats["pages"] += 1
        print(f"\n[PySpider] 解析第 {current_page} 页...")

        html = page.response.text
        skuids = re.findall(r'data-sku="(\d+)"', html)
        print(f"  找到 {len(skuids)} 个商品ID")

        page_products = []
        for sku_id in skuids:
            if sku_id in self.seen_ids:
                continue
            self.seen_ids.add(sku_id)

            name = ""
            name_match = re.search(rf'data-sku="{sku_id}".*?<em>(.*?)</em>', html, re.DOTALL)
            if name_match:
                name = re.sub(r'<[^>]+>', '', name_match.group(1)).strip()

            url = f"https://item.jd.com/{sku_id}.html"

            # 提取图片
            img_match = re.search(rf'data-sku="{sku_id}".*?data-lazy-img="//([^"]+)"', html, re.DOTALL)
            image_url = f"https://{img_match.group(1)}" if img_match else ""

            page_products.append(iPhone17Product(
                product_id=sku_id,
                name=name if name else f"Apple iPhone 17 (SKU: {sku_id})",
                price=0.0,
                original_price=0.0,
                currency="¥",
                url=url,
                image_url=image_url,
                shop_name="",
                shop_type="",
                comment_count=0,
                crawl_time=datetime.now().isoformat(),
            ))

        # 批量获取价格
        if page_products:
            skuids_to_fetch = [p.product_id for p in page_products]
            try:
                price_url = self._build_price_api_url(skuids_to_fetch)
                yield Request(
                    url=price_url,
                    callback=self.parse_prices,
                    headers=self.headers,
                    meta={"products": [p.to_dict() for p in page_products], "page": current_page, "keyword": keyword},
                )
            except Exception as e:
                print(f"  价格请求异常: {e}")
                for p in page_products:
                    self.products.append(p)
                    self.crawl_stats["products"] += 1

        # 下一页
        if current_page < self.max_pages:
            next_page = current_page + 1
            time.sleep(self.delay + random.uniform(0.5, 2.0))
            yield Request(
                url=self._build_search_url(keyword, next_page),
                callback=self.parse_search,
                headers=self.headers,
                meta={"keyword": keyword, "page": next_page},
            )

    def parse_prices(self, page):
        """解析价格API响应"""
        products_data = page.meta.get("products", [])
        current_page = page.meta.get("page", 1)

        try:
            prices_json = json.loads(page.response.text)
            price_map = {}
            for item in prices_json:
                sku_id = item.get("id", "")
                price = float(item.get("p", 0))
                oprice = float(item.get("op", 0))
                price_map[sku_id] = (price, oprice)

            for pd in products_data:
                sku = pd["product_id"]
                if sku in price_map:
                    pd["price"] = price_map[sku][0]
                    pd["original_price"] = price_map[sku][1]

                product = iPhone17Product(**pd)
                self.products.append(product)
                self.crawl_stats["products"] += 1
                print(f"  [价格] {product.name[:30]}... ¥{product.price}")

        except Exception as e:
            print(f"  价格解析异常: {e}")
            for pd in products_data:
                product = iPhone17Product(**pd)
                self.products.append(product)
                self.crawl_stats["products"] += 1

        print(f"\n[PySpider] 第 {current_page} 页完成, 累计 {self.crawl_stats['products']} 个商品")

    def save_results(self):
        """保存结果到 JSON 和 CSV"""
        output_dir = Path(__file__).resolve().parent.parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON
        json_path = output_dir / f"pyspider_jd_iphone17_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "framework": "PySpider (Python)",
                "total": len(self.products),
                "crawl_time": datetime.now().isoformat(),
                "products": [p.to_dict() for p in self.products],
            }, f, ensure_ascii=False, indent=2)
        print(f"\nJSON 已保存: {json_path}")

        # CSV
        csv_path = output_dir / f"pyspider_jd_iphone17_{timestamp}.csv"
        if self.products:
            fieldnames = list(self.products[0].to_dict().keys())
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for p in self.products:
                    writer.writerow(p.to_dict())
            print(f"CSV 已保存: {csv_path}")

    def print_stats(self):
        print(f"\n{'=' * 60}")
        print("PySpider 爬取统计")
        print(f"{'=' * 60}")
        print(f"商品总数: {self.crawl_stats['products']}")
        print(f"爬取页数: {self.crawl_stats['pages']}")

        prices = [p.price for p in self.products if p.price > 0]
        if prices:
            print(f"价格区间: ¥{min(prices):.2f} - ¥{max(prices):.2f}")
            print(f"平均价格: ¥{sum(prices)/len(prices):.2f}")
        print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(description="京东 iPhone 17 价格爬虫 (PySpider)")
    parser.add_argument("--pages", type=int, default=5, help="爬取页数")
    parser.add_argument("--delay", type=float, default=3.0, help="请求延迟(秒)")
    parser.add_argument("--proxy", type=str, default=None, help="代理地址")
    args = parser.parse_args()

    spider = JDiPhone17Spider(pages=args.pages, delay=args.delay, proxy=args.proxy)

    try:
        spider.start()
    except Exception as e:
        print(f"爬虫异常: {e}")
    finally:
        spider.save_results()
        spider.print_stats()


if __name__ == "__main__":
    main()
