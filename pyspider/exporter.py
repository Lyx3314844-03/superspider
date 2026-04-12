#!/usr/bin/env python3
"""
PySpider 数据导出模块 - 支持 JSON、CSV、Excel、Markdown 导出
"""

import os
import json
import csv
from typing import List, Dict
from datetime import datetime


class Exporter:
    """数据导出器"""

    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export_json(self, data: List[Dict], filename: str) -> str:
        """导出为 JSON"""
        if not filename.endswith(".json"):
            filename += ".json"

        filepath = os.path.join(self.output_dir, filename)

        # 添加时间戳
        output = {
            "schema_version": 1,
            "runtime": "python",
            "exported_at": datetime.now().isoformat(),
            "item_count": len(data),
            "items": data,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        return filepath

    def export_csv(self, data: List[Dict], filename: str) -> str:
        """导出为 CSV"""
        if not filename.endswith(".csv"):
            filename += ".csv"

        filepath = os.path.join(self.output_dir, filename)

        if not data:
            return filepath

        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

        return filepath

    def export_md(self, data: List[Dict], filename: str) -> str:
        """导出为 Markdown"""
        if not filename.endswith(".md"):
            filename += ".md"

        filepath = os.path.join(self.output_dir, filename)

        content = "# 爬虫数据导出\n\n"
        content += f"**导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"**数据条目**: {len(data)}\n\n---\n\n"

        for i, item in enumerate(data, 1):
            content += f"## {i}. {item.get('title', 'N/A')}\n\n"
            content += f"- **URL**: {item.get('url', 'N/A')}\n"
            content += f"- **来源**: {item.get('source', 'N/A')}\n"
            content += f"- **摘要**: {item.get('snippet', 'N/A')}\n\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath

    def export_xlsx(self, data: List[Dict], filename: str) -> str:
        """导出为 Excel (需要 openpyxl)"""
        try:
            import openpyxl
        except ImportError:
            return "请安装 openpyxl: pip install openpyxl"

        if not filename.endswith(".xlsx"):
            filename += ".xlsx"

        filepath = os.path.join(self.output_dir, filename)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Data"

        # 写入表头
        if data:
            headers = list(data[0].keys())
            ws.append(headers)

            # 写入数据
            for item in data:
                ws.append([item.get(h, "") for h in headers])

        wb.save(filepath)

        return filepath


def show_export_menu():
    """显示导出菜单"""
    print("\n📊 数据导出功能:")
    print("  export json <filename> - 导出为 JSON")
    print("  export csv <filename>   - 导出为 CSV")
    print("  export md <filename>    - 导出为 Markdown")
    print("  export xlsx <filename>  - 导出为 Excel")


if __name__ == "__main__":
    # 测试导出功能
    exporter = Exporter()

    test_data = [
        {
            "title": "测试1",
            "url": "https://example.com/1",
            "source": "Google",
            "snippet": "测试摘要1",
        },
        {
            "title": "测试2",
            "url": "https://example.com/2",
            "source": "Bing",
            "snippet": "测试摘要2",
        },
    ]

    print("测试 JSON 导出...")
    print(exporter.export_json(test_data, "test"))

    print("测试 CSV 导出...")
    print(exporter.export_csv(test_data, "test"))

    print("测试 Markdown 导出...")
    print(exporter.export_md(test_data, "test"))

    show_export_menu()
