from __future__ import annotations

import re
from urllib.parse import urljoin

DEFAULT_SITE_FAMILY = "jd"

SITE_PROFILES = {
    "jd": {
        "family": "jd",
        "catalog_url": "https://search.jd.com/Search?keyword=iphone",
        "detail_url": "https://item.jd.com/100000000000.html",
        "review_url": "https://club.jd.com/comment/productPageComments.action?productId=100000000000",
        "runner": "browser",
        "detail_link_keywords": ["item.jd.com", "sku=", "wareId=", "item.htm", "detail"],
        "next_link_keywords": ["page=", "pn-next", "next"],
        "review_link_keywords": ["comment", "review", "club.jd.com"],
        "price_patterns": [
            r'"p"\s*:\s*"([0-9]+(?:\.[0-9]{1,2})?)"',
            r"(?:price|jdPrice|promotionPrice)[\"'=:\\s]+([0-9]+(?:\\.[0-9]{1,2})?)",
            r"(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)",
        ],
        "item_id_patterns": [
            r"(?:skuId|sku|wareId|productId)[\"'=:\\s]+([A-Za-z0-9_-]+)",
        ],
        "shop_patterns": [
            r"(?:shopName|venderName|storeName)[\"'=:\\s]+([^\"'\\n<,}]+)",
        ],
        "review_count_patterns": [
            r"(?:commentCount|comment_num|reviewCount)[\"'=:\\s]+([0-9]+)",
        ],
        "rating_patterns": [
            r"(?:score|rating)[\"'=:\\s]+([0-9]+(?:\.[0-9])?)",
        ],
    },
    "taobao": {
        "family": "taobao",
        "catalog_url": "https://s.taobao.com/search?q=iphone",
        "detail_url": "https://item.taobao.com/item.htm?id=100000000000",
        "review_url": "https://rate.taobao.com/detailCommon.htm?id=100000000000",
        "runner": "browser",
        "detail_link_keywords": ["item.taobao.com", "item.htm", "id=", "detail"],
        "next_link_keywords": ["page=", "next"],
        "review_link_keywords": ["review", "rate.taobao.com", "comment"],
        "price_patterns": [
            r"(?:price|promotionPrice|minPrice)[\"'=:\\s]+([0-9]+(?:\\.[0-9]{1,2})?)",
            r"(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)",
        ],
        "item_id_patterns": [
            r"(?:itemId|item_id|id)[\"'=:\\s]+([A-Za-z0-9_-]+)",
        ],
        "shop_patterns": [
            r"(?:shopName|sellerNick|nick)[\"'=:\\s]+([^\"'\\n<,}]+)",
        ],
        "review_count_patterns": [
            r"(?:reviewCount|commentCount|rateTotal)[\"'=:\\s]+([0-9]+)",
        ],
        "rating_patterns": [
            r"(?:score|rating)[\"'=:\\s]+([0-9]+(?:\.[0-9])?)",
        ],
    },
    "tmall": {
        "family": "tmall",
        "catalog_url": "https://list.tmall.com/search_product.htm?q=iphone",
        "detail_url": "https://detail.tmall.com/item.htm?id=100000000000",
        "review_url": "https://rate.tmall.com/list_detail_rate.htm?itemId=100000000000",
        "runner": "browser",
        "detail_link_keywords": ["detail.tmall.com", "item.htm", "id=", "detail"],
        "next_link_keywords": ["page=", "next"],
        "review_link_keywords": ["review", "rate.tmall.com", "comment"],
        "price_patterns": [
            r"(?:price|promotionPrice|minPrice)[\"'=:\\s]+([0-9]+(?:\\.[0-9]{1,2})?)",
            r"(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)",
        ],
        "item_id_patterns": [
            r"(?:itemId|item_id|id)[\"'=:\\s]+([A-Za-z0-9_-]+)",
        ],
        "shop_patterns": [
            r"(?:shopName|sellerNick|shop)[\"'=:\\s]+([^\"'\\n<,}]+)",
        ],
        "review_count_patterns": [
            r"(?:reviewCount|commentCount|rateTotal)[\"'=:\\s]+([0-9]+)",
        ],
        "rating_patterns": [
            r"(?:score|rating)[\"'=:\\s]+([0-9]+(?:\.[0-9])?)",
        ],
    },
    "pinduoduo": {
        "family": "pinduoduo",
        "catalog_url": "https://mobile.yangkeduo.com/search_result.html?search_key=iphone",
        "detail_url": "https://mobile.yangkeduo.com/goods.html?goods_id=100000000000",
        "review_url": "https://mobile.yangkeduo.com/proxy/api/reviews/100000000000",
        "runner": "browser",
        "detail_link_keywords": ["goods.html", "goods_id=", "product", "detail"],
        "next_link_keywords": ["page=", "next"],
        "review_link_keywords": ["review", "comment"],
        "price_patterns": [
            r"(?:minPrice|price|groupPrice)[\"'=:\\s]+([0-9]+(?:\\.[0-9]{1,2})?)",
            r"(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)",
        ],
        "item_id_patterns": [
            r"(?:goods_id|goodsId|skuId)[\"'=:\\s]+([A-Za-z0-9_-]+)",
        ],
        "shop_patterns": [
            r"(?:mall_name|storeName|shopName)[\"'=:\\s]+([^\"'\\n<,}]+)",
        ],
        "review_count_patterns": [
            r"(?:reviewCount|commentCount)[\"'=:\\s]+([0-9]+)",
        ],
        "rating_patterns": [
            r"(?:score|rating)[\"'=:\\s]+([0-9]+(?:\.[0-9])?)",
        ],
    },
    "amazon": {
        "family": "amazon",
        "catalog_url": "https://www.amazon.com/s?k=iphone",
        "detail_url": "https://www.amazon.com/dp/B0EXAMPLE00",
        "review_url": "https://www.amazon.com/product-reviews/B0EXAMPLE00",
        "runner": "browser",
        "detail_link_keywords": ["/dp/", "/gp/product/", "/product/", "asin"],
        "next_link_keywords": ["page=", "next"],
        "review_link_keywords": ["review", "product-reviews"],
        "price_patterns": [
            r"(?:priceToPay|displayPrice|priceAmount)[\"'=:\\s]+([0-9]+(?:\\.[0-9]{1,2})?)",
            r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)",
        ],
        "item_id_patterns": [
            r"(?:asin|parentAsin|sku)[\"'=:\\s]+([A-Za-z0-9_-]+)",
        ],
        "shop_patterns": [
            r"(?:seller|merchantName|bylineInfo)[\"'=:\\s]+([^\"'\\n<,}]+)",
        ],
        "review_count_patterns": [
            r"(?:reviewCount|totalReviewCount)[\"'=:\\s]+([0-9]+)",
        ],
        "rating_patterns": [
            r"(?:averageRating|rating)[\"'=:\\s]+([0-9]+(?:\.[0-9])?)",
        ],
    },
}


def get_profile(site_family: str | None = None) -> dict:
    family = (site_family or DEFAULT_SITE_FAMILY).lower()
    return SITE_PROFILES.get(family, SITE_PROFILES[DEFAULT_SITE_FAMILY])


def first_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        matched = re.search(pattern, text, flags=re.IGNORECASE)
        if matched:
            return matched.group(1).strip()
    return ""


def collect_matches(text: str, patterns: list[str], limit: int = 10) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        for matched in re.findall(pattern, text, flags=re.IGNORECASE):
            value = matched[0] if isinstance(matched, tuple) else matched
            value = str(value).strip()
            if value and value not in seen:
                seen.add(value)
                values.append(value)
            if len(values) >= limit:
                return values
    return values


def normalize_links(base_url: str, links: list[str]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for link in links:
        absolute = urljoin(base_url, link.strip())
        if not absolute.startswith(("http://", "https://")):
            continue
        if absolute not in seen:
            seen.add(absolute)
            values.append(absolute)
    return values


def collect_product_links(base_url: str, links: list[str], profile: dict, limit: int = 20) -> list[str]:
    keywords = tuple(profile.get("detail_link_keywords", []))
    matches: list[str] = []
    for link in normalize_links(base_url, links):
        lowered = link.lower()
        if any(keyword.lower() in lowered for keyword in keywords):
            matches.append(link)
        if len(matches) >= limit:
            break
    return matches


def collect_image_links(base_url: str, links: list[str], limit: int = 10) -> list[str]:
    matches: list[str] = []
    for link in normalize_links(base_url, links):
        lowered = link.lower()
        if any(lowered.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")) or "image" in lowered:
            matches.append(link)
        if len(matches) >= limit:
            break
    return matches


def first_link_with_keywords(base_url: str, links: list[str], keywords: list[str]) -> str:
    for link in normalize_links(base_url, links):
        lowered = link.lower()
        if any(keyword.lower() in lowered for keyword in keywords):
            return link
    return ""


def best_title(selector) -> str:
    return (
        selector.title()
        or selector.css_first("h1")
        or selector.css_attr_first("meta[property='og:title']", "content")
        or ""
    ).strip()


def text_excerpt(text: str, limit: int = 800) -> str:
    return re.sub(r"\s+", " ", text).strip()[:limit]
