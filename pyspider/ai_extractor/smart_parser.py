"""
智能解析器

自动识别页面类型并选择合适的提取策略
吸收 scrapegraphai 的智能解析功能

@author: Lan
@version: 2.0.0
@date: 2026-03-20
"""

import re
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup


class SmartParser:
    """
    智能解析器

    自动识别页面类型（文章、商品、视频等）并提取相应数据
    """

    # 页面类型特征
    PAGE_PATTERNS = {
        "article": [
            r"<article",
            r'class="[^"]*article[^"]*"',
            r'<meta[^>]*property="og:type"[^>]*content="article"',
            r"<time[^>]*>",
            r"byline|author|published",
        ],
        "product": [
            r'class="[^"]*product[^"]*"',
            r"price|￥|\$|€",
            r'<meta[^>]*property="product:price"',
            r"add to cart|buy now|in stock",
        ],
        "video": [
            r"<video",
            r'class="[^"]*video[^"]*"',
            r'<meta[^>]*property="og:video"',
            r"youtube|vimeo|bilibili",
            r"watch|play|duration",
        ],
        "list": [
            r'<ul[^>]*class="[^"]*list[^"]*"',
            r'class="[^"]*items[^"]*"',
            r"pagination|next page|page \d+",
        ],
        "search": [
            r'<input[^>]*type="search"',
            r'class="[^"]*search[^"]*"',
            r"search results|found \d+ results",
        ],
    }

    def __init__(self):
        """初始化智能解析器"""
        self.soup = None
        self.page_type = None

    def parse(self, html: str) -> Dict[str, Any]:
        """
        智能解析 HTML

        Args:
            html: HTML 内容

        Returns:
            解析结果
        """
        self.soup = BeautifulSoup(html, "html.parser")
        self.page_type = self._detect_page_type()

        # 根据页面类型选择提取策略
        if self.page_type == "article":
            return self._extract_article()
        elif self.page_type == "product":
            return self._extract_product()
        elif self.page_type == "video":
            return self._extract_video()
        elif self.page_type == "list":
            return self._extract_list()
        else:
            return self._extract_generic()

    def _detect_page_type(self) -> str:
        """
        检测页面类型

        Returns:
            页面类型
        """
        html_text = str(self.soup).lower()
        scores = {}

        for page_type, patterns in self.PAGE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, html_text):
                    score += 1
            scores[page_type] = score

        # 返回得分最高的类型
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return "generic"

    def _extract_article(self) -> Dict[str, Any]:
        """提取文章数据"""
        result = {
            "page_type": "article",
            "title": self._extract_title(),
            "author": self._extract_author(),
            "publish_date": self._extract_date(),
            "content": self._extract_article_content(),
            "tags": self._extract_tags(),
            "category": self._extract_category(),
        }
        return result

    def _extract_product(self) -> Dict[str, Any]:
        """提取商品数据"""
        result = {
            "page_type": "product",
            "title": self._extract_title(),
            "price": self._extract_price(),
            "currency": self._extract_currency(),
            "availability": self._extract_availability(),
            "description": self._extract_description(),
            "images": self._extract_images(),
            "rating": self._extract_rating(),
            "reviews_count": self._extract_reviews_count(),
        }
        return result

    def _extract_video(self) -> Dict[str, Any]:
        """提取视频数据"""
        result = {
            "page_type": "video",
            "title": self._extract_title(),
            "video_url": self._extract_video_url(),
            "thumbnail": self._extract_thumbnail(),
            "duration": self._extract_duration(),
            "author": self._extract_author(),
            "publish_date": self._extract_date(),
            "views": self._extract_views(),
            "description": self._extract_description(),
        }
        return result

    def _extract_list(self) -> Dict[str, Any]:
        """提取列表数据"""
        items = []

        # 尝试提取列表项
        list_items = self.soup.select("ul li, ol li, .item, .list-item")
        for item in list_items[:20]:  # 限制数量
            text = item.get_text(strip=True)
            if text:
                link = item.find("a")
                items.append(
                    {
                        "text": text,
                        "link": link.get("href") if link else None,
                    }
                )

        result = {
            "page_type": "list",
            "items": items,
            "total": len(items),
            "pagination": self._extract_pagination(),
        }
        return result

    def _extract_generic(self) -> Dict[str, Any]:
        """通用提取"""
        result = {
            "page_type": "generic",
            "title": self._extract_title(),
            "description": self._extract_description(),
            "links": self._extract_all_links(),
            "images": self._extract_images(),
            "text": self._extract_main_text(),
        }
        return result

    # ========== 通用提取方法 ==========

    def _extract_title(self) -> Optional[str]:
        """提取标题"""
        # 尝试多种选择器
        selectors = [
            "h1",
            "title",
            'meta[property="og:title"]',
            ".title",
            ".article-title",
            ".product-title",
            '[itemprop="name"]',
            '[itemprop="headline"]',
        ]

        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                if element.name == "meta":
                    return element.get("content")
                return element.get_text(strip=True)

        return None

    def _extract_author(self) -> Optional[str]:
        """提取作者"""
        selectors = [
            ".author",
            ".byline",
            '[itemprop="author"]',
            'meta[name="author"]',
            'meta[property="article:author"]',
        ]

        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                if element.name == "meta":
                    return element.get("content")
                return element.get_text(strip=True)

        return None

    def _extract_date(self) -> Optional[str]:
        """提取日期"""
        selectors = [
            "time[datetime]",
            ".date",
            ".publish-date",
            '[itemprop="datePublished"]',
            'meta[property="article:published_time"]',
        ]

        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                if element.has_attr("datetime"):
                    return element.get("datetime")
                if element.name == "meta":
                    return element.get("content")
                return element.get_text(strip=True)

        return None

    def _extract_description(self) -> Optional[str]:
        """提取描述"""
        selectors = [
            'meta[name="description"]',
            'meta[property="og:description"]',
            ".description",
            ".summary",
            '[itemprop="description"]',
        ]

        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                if element.name == "meta":
                    return element.get("content")
                return element.get_text(strip=True)

        return None

    def _extract_images(self) -> List[str]:
        """提取图片"""
        images = []

        # 主图
        main_image = self.soup.select_one('meta[property="og:image"]')
        if main_image and main_image.get("content"):
            images.append(main_image.get("content"))

        # 所有图片
        for img in self.soup.find_all("img", src=True)[:10]:
            src = img.get("src")
            if src and src not in images:
                images.append(src)

        return images

    def _extract_all_links(self) -> List[Dict[str, str]]:
        """提取所有链接"""
        links = []

        for a in self.soup.find_all("a", href=True)[:20]:
            links.append(
                {
                    "text": a.get_text(strip=True),
                    "href": a.get("href"),
                }
            )

        return links

    def _extract_main_text(self) -> str:
        """提取主要文本"""
        # 尝试常见内容容器
        selectors = [
            "article",
            ".content",
            ".main-content",
            '[itemprop="articleBody"]',
            ".post-content",
        ]

        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                return element.get_text(separator="\n", strip=True)

        #  fallback 到 body
        body = self.soup.find("body")
        if body:
            return body.get_text(separator="\n", strip=True)

        return self.soup.get_text(separator="\n", strip=True)

    # ========== 特定类型提取方法 ==========

    def _extract_article_content(self) -> Optional[str]:
        """提取文章内容"""
        selectors = [
            "article",
            ".article-content",
            ".post-content",
            '[itemprop="articleBody"]',
            ".entry-content",
        ]

        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                return element.get_text(separator="\n", strip=True)

        return self._extract_main_text()

    def _extract_price(self) -> Optional[str]:
        """提取价格"""
        selectors = [
            ".price",
            '[itemprop="price"]',
            'meta[property="product:price:amount"]',
            ".product-price",
            ".sale-price",
        ]

        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                if element.name == "meta":
                    return element.get("content")
                text = element.get_text(strip=True)
                # 提取数字
                match = re.search(r"[\d,]+\.?\d*", text)
                if match:
                    return match.group()
                return text

        return None

    def _extract_currency(self) -> str:
        """提取货币符号"""
        price_element = self.soup.select_one('.price, [itemprop="price"]')
        if price_element:
            text = price_element.get_text(strip=True)
            currencies = ["￥", "$", "€", "£", "¥"]
            for currency in currencies:
                if currency in text:
                    return currency
        return "CNY"

    def _extract_availability(self) -> Optional[str]:
        """提取库存状态"""
        selectors = [
            ".availability",
            '[itemprop="availability"]',
            ".stock-status",
            ".in-stock",
        ]

        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                text = element.get_text(strip=True).lower()
                if "in stock" in text or "有货" in text:
                    return "in_stock"
                elif "out of stock" in text or "无货" in text:
                    return "out_of_stock"
                return text

        return None

    def _extract_video_url(self) -> Optional[str]:
        """提取视频 URL"""
        # 视频元素
        video = self.soup.find("video")
        if video and video.get("src"):
            return video.get("src")

        # iframe
        iframe = self.soup.find("iframe")
        if iframe and iframe.get("src"):
            return iframe.get("src")

        # meta
        meta = self.soup.select_one('meta[property="og:video"]')
        if meta and meta.get("content"):
            return meta.get("content")

        return None

    def _extract_thumbnail(self) -> Optional[str]:
        """提取缩略图"""
        selectors = [
            'meta[property="og:image"]',
            'meta[name="twitter:image"]',
            ".thumbnail img",
            ".video-thumbnail img",
        ]

        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                if element.name == "meta":
                    return element.get("content")
                if element.name == "img":
                    return element.get("src")

        return None

    def _extract_duration(self) -> Optional[str]:
        """提取时长"""
        selectors = [
            ".duration",
            '[itemprop="duration"]',
            'meta[property="video:duration"]',
        ]

        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                if element.name == "meta":
                    return element.get("content")
                return element.get_text(strip=True)

        return None

    def _extract_views(self) -> Optional[int]:
        """提取观看次数"""
        selectors = [
            ".views",
            ".view-count",
            '[itemprop="interactionCount"]',
        ]

        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                match = re.search(r"[\d,]+", text)
                if match:
                    return int(match.group().replace(",", ""))

        return None

    def _extract_tags(self) -> List[str]:
        """提取标签"""
        tags = []

        tag_elements = self.soup.select('.tag, .tags a, [itemprop="keywords"]')
        for tag in tag_elements[:10]:
            text = tag.get_text(strip=True)
            if text:
                tags.append(text)

        return tags

    def _extract_category(self) -> Optional[str]:
        """提取分类"""
        selectors = [
            ".category",
            ".categories a",
            '[itemprop="articleSection"]',
            'meta[property="article:section"]',
        ]

        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                if element.name == "meta":
                    return element.get("content")
                return element.get_text(strip=True)

        return None

    def _extract_rating(self) -> Optional[float]:
        """提取评分"""
        selectors = [
            ".rating",
            '[itemprop="ratingValue"]',
            'meta[property="product:rating:value"]',
        ]

        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                if element.name == "meta":
                    value = element.get("content")
                else:
                    value = element.get_text(strip=True)

                match = re.search(r"\d+\.?\d*", value)
                if match:
                    return float(match.group())

        return None

    def _extract_reviews_count(self) -> Optional[int]:
        """提取评论数"""
        selectors = [
            ".reviews-count",
            '[itemprop="reviewCount"]',
            'meta[property="product:review_count"]',
        ]

        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                match = re.search(r"[\d,]+", text)
                if match:
                    return int(match.group().replace(",", ""))

        return None

    def _extract_pagination(self) -> Dict[str, Optional[str]]:
        """提取分页信息"""
        result = {
            "current_page": None,
            "total_pages": None,
            "next_page": None,
            "prev_page": None,
        }

        # 当前页
        current = self.soup.select_one('.current, .active, [aria-current="page"]')
        if current:
            result["current_page"] = current.get_text(strip=True)

        # 下一页
        next_link = self.soup.select_one('.next a, a[rel="next"]')
        if next_link:
            result["next_page"] = next_link.get("href")

        # 上一页
        prev_link = self.soup.select_one('.prev a, a[rel="prev"]')
        if prev_link:
            result["prev_page"] = prev_link.get("href")

        return result


# 便捷函数
def smart_parse(html: str) -> Dict[str, Any]:
    """
    智能解析 HTML 的便捷函数

    Args:
        html: HTML 内容

    Returns:
        解析结果
    """
    parser = SmartParser()
    return parser.parse(html)
