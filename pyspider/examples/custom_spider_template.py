#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PySpider 自定义爬虫脚本模板

使用说明:
1. 复制此模板创建新的爬虫
2. 修改 START_URLS 为目标网站
3. 实现 parse 方法定义爬取逻辑
4. 运行：python custom_spider_template.py

特性:
- ✅ 简单的类定义
- ✅ 完整的错误处理
- ✅ 数据导出 (JSON/CSV)
- ✅ 进度显示
- ✅ 统计信息

@author: Lan
@version: 1.0.0
"""

import json
import csv
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

# 导入 PySpider 核心模块
try:
    from pyspider.core import Spider, Request, Response
    from pyspider.core.models import Page
except ImportError:
    print("请先安装 PySpider: pip install -e .")
    exit(1)


# ========== 数据模型 ==========


@dataclass
class CrawlResult:
    """爬取结果数据模型"""

    url: str
    title: str
    content: str
    links: List[str]
    images: List[str]
    crawl_time: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


# ========== 爬虫类定义 ==========


class CustomSpiderTemplate(Spider):
    """
    自定义爬虫模板

    使用方法:
    1. 修改 START_URLS
    2. 实现 parse 方法
    3. 运行爬虫
    """

    # ========== 配置区域 ==========

    # 起始 URL 列表
    START_URLS = [
        "https://example.com/page1",
        "https://example.com/page2",
    ]

    # 爬虫配置
    CONFIG = {
        "thread_count": 5,  # 线程数
        "max_depth": 3,  # 最大深度
        "max_requests": 1000,  # 最大请求数
        "delay": 1.0,  # 请求延迟 (秒)
        "timeout": 30,  # 超时时间 (秒)
        "retry_times": 3,  # 重试次数
    }

    # 输出配置
    OUTPUT_CONFIG = {
        "save_json": True,  # 保存为 JSON
        "save_csv": False,  # 保存为 CSV
        "output_dir": "output",  # 输出目录
        "json_file": "results.json",
        "csv_file": "results.csv",
    }

    # ========== 构造函数 ==========

    def __init__(self):
        """初始化爬虫"""
        super().__init__(name="CustomSpider", thread_count=self.CONFIG["thread_count"])

        # 结果存储
        self.results: List[CrawlResult] = []

        # 统计信息
        self.stats = {
            "start_time": None,
            "end_time": None,
            "total_requests": 0,
            "success_requests": 0,
            "failed_requests": 0,
        }

        print("=" * 50)
        print("自定义爬虫模板")
        print("=" * 50)
        print(f"起始 URL 数：{len(self.START_URLS)}")
        print(f"线程数：{self.CONFIG['thread_count']}")
        print(f"最大深度：{self.CONFIG['max_depth']}")
        print("=" * 50)

    # ========== 核心逻辑 ==========

    def parse(self, page: Page) -> Optional[Dict[str, Any]]:
        """
        页面解析方法

        在这里定义如何提取数据

        Args:
            page: 页面对象

        Returns:
            提取的数据字典
        """
        print(f"正在处理：{page.response.url}")

        try:
            # ===== 数据提取示例 =====

            # 1. 提取标题
            title = page.response.css("title::text").get(default="")

            # 2. 提取链接
            links = page.response.css("a::attr(href)").getall()

            # 3. 提取文本内容
            content = page.response.css(".content::text").get(default="")

            # 4. 提取图片
            images = page.response.css("img::attr(src)").getall()

            # ===== 创建结果对象 =====

            result = CrawlResult(
                url=page.response.url,
                title=title,
                content=content[:500] if content else "",  # 限制长度
                links=links[:20],  # 限制数量
                images=images[:20],
                crawl_time=datetime.now().isoformat(),
            )

            # 保存结果
            self.results.append(result)

            # ===== 添加新链接 =====

            # 从当前页面提取新链接继续爬取
            for link in links:
                if self.should_crawl(link, page.response.url):
                    yield Request(
                        url=link,
                        callback=self.parse,
                        meta={"depth": page.meta.get("depth", 0) + 1},
                    )

            # 返回当前页面数据
            return result.to_dict()

        except Exception as e:
            print(f"解析失败：{page.response.url}, 错误：{e}")
            return None

    def should_crawl(self, link: str, current_url: str) -> bool:
        """
        判断链接是否应该继续爬取

        Args:
            link: 链接
            current_url: 当前页面 URL

        Returns:
            是否爬取
        """
        # 空链接检查
        if not link or not link.strip():
            return False

        # 深度检查
        depth = self.request.meta.get("depth", 0)
        if depth >= self.CONFIG["max_depth"]:
            return False

        # 域名检查 - 只爬取同域名
        from urllib.parse import urlparse

        current_domain = urlparse(current_url).netloc
        link_domain = urlparse(link).netloc

        # 允许空域名（相对 URL）
        if not link_domain:
            return True

        # 检查是否是目标域名
        return link_domain == current_domain

    # ========== 数据导出 ==========

    def save_results(self):
        """保存结果到文件"""
        output_dir = Path(self.OUTPUT_CONFIG["output_dir"])
        output_dir.mkdir(exist_ok=True)

        # 保存为 JSON
        if self.OUTPUT_CONFIG["save_json"]:
            json_path = output_dir / self.OUTPUT_CONFIG["json_file"]
            self.save_json(json_path)

        # 保存为 CSV
        if self.OUTPUT_CONFIG["save_csv"]:
            csv_path = output_dir / self.OUTPUT_CONFIG["csv_file"]
            self.save_csv(csv_path)

    def save_json(self, file_path: Path):
        """保存为 JSON 文件"""
        try:
            data = [result.to_dict() for result in self.results]

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"\n✓ 已保存 {len(data)} 条结果到：{file_path}")

        except Exception as e:
            print(f"保存 JSON 失败：{e}")

    def save_csv(self, file_path: Path):
        """保存为 CSV 文件"""
        try:
            if not self.results:
                return

            # CSV 字段
            fieldnames = ["url", "title", "content", "links", "images", "crawl_time"]

            with open(file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for result in self.results:
                    row = result.to_dict()
                    # 列表转字符串
                    row["links"] = "; ".join(row["links"])
                    row["images"] = "; ".join(row["images"])
                    writer.writerow(row)

            print(f"✓ 已保存 {len(self.results)} 条结果到：{file_path}")

        except Exception as e:
            print(f"保存 CSV 失败：{e}")

    # ========== 统计信息 ==========

    def print_stats(self):
        """打印统计信息"""
        print("\n" + "=" * 50)
        print("统计信息")
        print("=" * 50)
        print(f"总请求数：{self.stats['total_requests']}")
        print(f"成功：{self.stats['success_requests']}")
        print(f"失败：{self.stats['failed_requests']}")
        print(f"总结果数：{len(self.results)}")

        if self.stats["start_time"] and self.stats["end_time"]:
            duration = (
                self.stats["end_time"] - self.stats["start_time"]
            ).total_seconds()
            print(f"耗时：{duration:.2f}秒")

            if duration > 0:
                qps = self.stats["total_requests"] / duration
                print(f"QPS: {qps:.2f}")

        print("=" * 50)

    # ========== 运行方法 ==========

    def run(self):
        """运行爬虫"""
        print("\n开始运行爬虫...\n")

        self.stats["start_time"] = datetime.now()

        try:
            # 添加起始请求
            for url in self.START_URLS:
                self.add_request(
                    Request(url=url, callback=self.parse, meta={"depth": 0})
                )

            # 运行爬虫
            super().run()

        except Exception as e:
            print(f"爬虫运行失败：{e}")

        finally:
            self.stats["end_time"] = datetime.now()

            # 保存结果
            self.save_results()

            # 打印统计
            self.print_stats()


# ========== 主函数 ==========


def main():
    """主函数"""
    print("\n" + "=" * 50)
    print("自定义爬虫模板 v1.0.0")
    print("=" * 50 + "\n")

    # 创建爬虫实例
    spider = CustomSpiderTemplate()

    # 运行爬虫
    spider.run()

    print("\n爬虫运行完成！")


if __name__ == "__main__":
    main()
