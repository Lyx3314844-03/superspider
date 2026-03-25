#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫配置生成器

功能:
- ✅ 交互式配置生成
- ✅ 模板选择
- ✅ 配置验证
- ✅ 一键生成爬虫脚本

使用:
    python config_generator.py
"""

import json
import yaml
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


class ConfigGenerator:
    """爬虫配置生成器"""
    
    # 爬虫模板
    TEMPLATES = {
        '1': {
            'name': '通用爬虫模板',
            'file': 'custom_spider_template.py',
            'description': '适合大多数网站的基础爬虫',
        },
        '2': {
            'name': '新闻网站爬虫',
            'file': 'spider_news.py',
            'description': '专门用于爬取新闻网站',
        },
        '3': {
            'name': '电商网站爬虫',
            'file': 'spider_ecommerce.py',
            'description': '用于爬取电商商品数据',
        },
        '4': {
            'name': '社交媒体爬虫',
            'file': 'spider_social.py',
            'description': '用于爬取社交媒体数据',
        },
    }
    
    def __init__(self):
        self.config = {
            'spider_name': '',
            'start_urls': [],
            'selectors': {},
            'output': {},
            'advanced': {},
        }
    
    def run(self):
        """运行配置生成器"""
        print("=" * 60)
        print("爬虫配置生成器 v1.0.0")
        print("=" * 60)
        print()
        
        # 选择模板
        self.select_template()
        
        # 基础配置
        self.input_basic_config()
        
        # 选择器配置
        self.input_selectors()
        
        # 输出配置
        self.input_output()
        
        # 高级配置
        self.input_advanced()
        
        # 生成配置
        self.generate()
        
        print("\n" + "=" * 60)
        print("配置生成完成！")
        print("=" * 60)
    
    def select_template(self):
        """选择模板"""
        print("\n请选择爬虫模板:")
        print("-" * 60)
        
        for key, template in self.TEMPLATES.items():
            print(f"{key}. {template['name']}")
            print(f"   {template['description']}")
            print()
        
        while True:
            choice = input("请输入模板编号 (1-4): ").strip()
            if choice in self.TEMPLATES:
                self.config['template'] = self.TEMPLATES[choice]
                print(f"✓ 已选择：{self.config['template']['name']}")
                break
            print("❌ 无效选择，请重新输入")
    
    def input_basic_config(self):
        """输入基础配置"""
        print("\n" + "=" * 60)
        print("基础配置")
        print("-" * 60)
        
        # 爬虫名称
        while True:
            name = input("爬虫名称 (英文): ").strip()
            if name and name.replace('_', '').isalnum():
                self.config['spider_name'] = name
                break
            print("❌ 名称只能包含英文字母、数字和下划线")
        
        # 起始 URL
        print("\n请输入起始 URL (每行一个，空行结束):")
        urls = []
        while True:
            url = input("  URL: ").strip()
            if not url:
                break
            if url.startswith('http'):
                urls.append(url)
            else:
                print("❌ URL 必须以 http 或 https 开头")
        
        self.config['start_urls'] = urls
        print(f"✓ 已添加 {len(urls)} 个起始 URL")
    
    def input_selectors(self):
        """输入选择器配置"""
        print("\n" + "=" * 60)
        print("CSS 选择器配置")
        print("-" * 60)
        print("提示：按 Enter 跳过可选字段")
        
        selectors = {}
        
        # 通用选择器
        print("\n通用选择器:")
        selectors['title'] = input("  标题选择器 (如 h1::text): ").strip()
        selectors['content'] = input("  内容选择器 (如 .content::text): ").strip()
        selectors['links'] = input("  链接选择器 (如 a::attr(href)): ").strip()
        selectors['images'] = input("  图片选择器 (如 img::attr(src)): ").strip()
        
        # 根据模板添加特定选择器
        template_name = self.config['template']['name']
        
        if '新闻' in template_name:
            print("\n新闻网站特定选择器:")
            selectors['author'] = input("  作者选择器: ").strip()
            selectors['publish_time'] = input("  发布时间选择器: ").strip()
            selectors['source'] = input("  来源选择器: ").strip()
        
        elif '电商' in template_name:
            print("\n电商网站特定选择器:")
            selectors['price'] = input("  价格选择器: ").strip()
            selectors['original_price'] = input("  原价选择器: ").strip()
            selectors['brand'] = input("  品牌选择器: ").strip()
        
        elif '社交' in template_name:
            print("\n社交媒体特定选择器:")
            selectors['username'] = input("  用户名选择器: ").strip()
            selectors['followers'] = input("  粉丝数选择器: ").strip()
            selectors['likes'] = input("  点赞数选择器: ").strip()
        
        # 过滤空值
        self.config['selectors'] = {k: v for k, v in selectors.items() if v}
        print(f"✓ 已配置 {len(self.config['selectors'])} 个选择器")
    
    def input_output(self):
        """输入输出配置"""
        print("\n" + "=" * 60)
        print("输出配置")
        print("-" * 60)
        
        output = {}
        
        # 输出格式
        print("\n选择输出格式 (可多选，用逗号分隔):")
        print("  1. JSON")
        print("  2. CSV")
        print("  3. SQLite")
        
        formats = input("  选择 (如 1,2): ").strip()
        output['save_json'] = '1' in formats
        output['save_csv'] = '2' in formats
        output['save_sqlite'] = '3' in formats
        
        # 输出目录
        output_dir = input("\n输出目录 (默认 output): ").strip()
        output['output_dir'] = output_dir or 'output'
        
        # 图片下载
        download = input("\n是否下载图片？(y/n): ").strip().lower()
        output['download_images'] = download == 'y'
        
        self.config['output'] = output
        print("✓ 输出配置完成")
    
    def input_advanced(self):
        """输入高级配置"""
        print("\n" + "=" * 60)
        print("高级配置")
        print("-" * 60)
        
        advanced = {}
        
        # 线程数
        while True:
            try:
                threads = input("\n线程数 (默认 5): ").strip()
                advanced['thread_count'] = int(threads) if threads else 5
                break
            except ValueError:
                print("❌ 请输入有效数字")
        
        # 延迟
        while True:
            try:
                delay = input("请求延迟 (秒，默认 1.0): ").strip()
                advanced['delay'] = float(delay) if delay else 1.0
                break
            except ValueError:
                print("❌ 请输入有效数字")
        
        # 最大深度
        while True:
            try:
                depth = input("最大爬取深度 (默认 3): ").strip()
                advanced['max_depth'] = int(depth) if depth else 3
                break
            except ValueError:
                print("❌ 请输入有效数字")
        
        # 反反爬
        use_antibot = input("\n是否启用反反爬？(y/n): ").strip().lower()
        advanced['use_antibot'] = use_antibot == 'y'
        
        self.config['advanced'] = advanced
        print("✓ 高级配置完成")
    
    def generate(self):
        """生成爬虫脚本"""
        print("\n正在生成爬虫脚本...")
        
        # 生成文件名
        filename = f"{self.config['spider_name']}.py"
        output_path = Path(self.config['output']['output_dir']) / filename
        
        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 生成代码
        code = self.generate_code()
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        print(f"✓ 已生成：{output_path}")
        
        # 保存配置文件
        config_path = output_path.parent / f"{self.config['spider_name']}_config.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
        
        print(f"✓ 已保存配置：{config_path}")
        
        # 显示使用说明
        self.show_usage()
    
    def generate_code(self) -> str:
        """生成爬虫代码"""
        template = self.config['template']['file']
        
        # 读取模板
        template_path = Path('pyspider/examples') / template
        if not template_path.exists():
            template_path = Path(__file__).parent / 'examples' / template
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except FileNotFoundError:
            code = self.get_default_template()
        
        # 替换配置
        code = code.replace('class NewsSpider', f"class {self.config['spider_name'].title().replace('_', '')}Spider")
        code = code.replace('name="NewsSpider"', f'name="{self.config["spider_name"]}"')
        
        # 替换起始 URL
        urls_str = json.dumps(self.config['start_urls'], indent=8)
        code = code.replace(
            'START_URLS = [\n        "https://news.example.com",\n    ]',
            f'START_URLS = {urls_str}'
        )
        
        # 替换选择器
        if self.config['selectors']:
            selectors_str = json.dumps(self.config['selectors'], indent=8, ensure_ascii=False)
            code = code.replace(
                "SELECTORS = {\n        'article_list': '.article-list .article-item',\n    }",
                f"SELECTORS = {selectors_str}"
            )
        
        # 替换高级配置
        if self.config['advanced']:
            for key, value in self.config['advanced'].items():
                if key == 'thread_count':
                    code = code.replace("'thread_count': 5", f"'thread_count': {value}")
                elif key == 'delay':
                    code = code.replace("'delay': 2.0", f"'delay': {value}")
                elif key == 'max_depth':
                    code = code.replace("'max_depth': 5", f"'max_depth': {value}")
        
        # 添加反反爬导入
        if self.config['advanced'].get('use_antibot'):
            if 'from pyspider.antibot import' not in code:
                code = code.replace(
                    'from pyspider.core import Spider, Request',
                    'from pyspider.core import Spider, Request\nfrom pyspider.antibot import AntiBotManager'
                )
        
        return code
    
    def get_default_template(self) -> str:
        """获取默认模板"""
        return '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义爬虫脚本
"""

from pyspider.core import Spider, Request

class CustomSpider(Spider):
    START_URLS = []
    
    def parse(self, page):
        # 在这里实现爬取逻辑
        title = page.response.css('title::text').get()
        links = page.response.css('a::attr(href)').getall()
        
        return {
            'title': title,
            'links': links,
        }

if __name__ == '__main__':
    spider = CustomSpider()
    spider.run()
'''
    
    def show_usage(self):
        """显示使用说明"""
        print("\n" + "=" * 60)
        print("使用说明")
        print("=" * 60)
        print(f"""
1. 运行爬虫:
   python {self.config['output']['output_dir']}/{self.config['spider_name']}.py

2. 查看配置文件:
   cat {self.config['output']['output_dir']}/{self.config['spider_name']}_config.yaml

3. 修改配置:
   - 编辑 Python 文件修改爬虫逻辑
   - 编辑 YAML 文件修改配置参数

4. 查看输出:
   - JSON: {self.config['output']['output_dir']}/results.json
   - CSV: {self.config['output']['output_dir']}/results.csv
   - SQLite: {self.config['output']['output_dir']}/results.db
""")


def main():
    """主函数"""
    generator = ConfigGenerator()
    generator.run()


if __name__ == '__main__':
    main()
