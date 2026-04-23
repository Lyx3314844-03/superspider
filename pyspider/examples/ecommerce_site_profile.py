from __future__ import annotations

import json
import re
from urllib.parse import urljoin

DEFAULT_SITE_FAMILY = "jd"

SITE_PROFILES = {
    "generic": {
        "family": "generic",
        "catalog_url": "https://shop.example.com/search?q=demo",
        "detail_url": "https://shop.example.com/product/demo-item",
        "review_url": "https://shop.example.com/product/demo-item/reviews",
        "runner": "browser",
        "detail_link_keywords": ["/product", "/item", "/goods", "/sku", "detail", "productId", "itemId"],
        "next_link_keywords": ["page=", "next", "pagination", "load-more"],
        "review_link_keywords": ["review", "reviews", "comment", "comments", "rating"],
        "price_patterns": [
            r"(?:price|salePrice|currentPrice|finalPrice|minPrice|maxPrice|offerPrice)[\"'=:\\s]+([0-9]+(?:\\.[0-9]{1,2})?)",
            r"(?:￥|¥|\\$|€|£)\s*([0-9]+(?:\.[0-9]{1,2})?)",
        ],
        "item_id_patterns": [
            r"(?:skuId|sku|wareId|productId|itemId|goods_id|goodsId|asin)[\"'=:\\s]+([A-Za-z0-9_-]+)",
        ],
        "shop_patterns": [
            r"(?:shopName|seller|sellerNick|storeName|merchantName|vendor|brand)[\"'=:\\s]+([^\"'\\n<,}]+)",
        ],
        "review_count_patterns": [
            r"(?:reviewCount|commentCount|comments|ratingsTotal|totalReviewCount)[\"'=:\\s]+([0-9]+)",
        ],
        "rating_patterns": [
            r"(?:rating|score|ratingValue|averageRating)[\"'=:\\s]+([0-9]+(?:\.[0-9])?)",
        ],
    },
    "jd": {
        "family": "jd",
        "catalog_url": "https://search.jd.com/Search?keyword=iphone",
        "detail_url": "https://item.jd.com/100000000000.html",
        "review_url": "https://club.jd.com/comment/productPageComments.action?productId=100000000000&score=0&sortType=5&page=0&pageSize=10&isShadowSku=0&fold=1",
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
    return SITE_PROFILES.get(family, SITE_PROFILES["generic"] if family not in SITE_PROFILES and family != DEFAULT_SITE_FAMILY else SITE_PROFILES[DEFAULT_SITE_FAMILY])


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


def clean_html_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", value or "")).strip()


def build_jd_price_api_url(sku_ids: list[str]) -> str:
    ids = ",".join(str(sku).strip() for sku in sku_ids if str(sku).strip())
    return f"https://p.3.cn/prices/mgets?skuIds={ids}&type=1&area=1_72_4137_0"


def build_jd_review_api_url(product_id: str, page: int = 0, page_size: int = 10) -> str:
    return (
        "https://club.jd.com/comment/productPageComments.action"
        f"?productId={product_id}&score=0&sortType=5&page={page}&pageSize={page_size}"
        "&isShadowSku=0&fold=1"
    )


def extract_jd_item_id(url: str, html: str) -> str:
    match = re.search(r"/(\d+)\.html", url)
    if match:
        return match.group(1)
    return first_match(
        html,
        [
            r"(?:skuId|sku|wareId|productId)[\"'=:\\s]+([A-Za-z0-9_-]+)",
            r'"sku"\s*:\s*"(\d+)"',
        ],
    )


def extract_jd_catalog_products(html: str) -> list[dict]:
    products: list[dict] = []
    seen: set[str] = set()
    for sku_id in re.findall(r'data-sku="(\d+)"', html):
        if sku_id in seen:
            continue
        seen.add(sku_id)

        name_match = re.search(
            rf'data-sku="{sku_id}"[\s\S]*?<em[^>]*>(.*?)</em>',
            html,
            flags=re.IGNORECASE,
        )
        image_match = re.search(
            rf'data-sku="{sku_id}"[\s\S]*?(?:data-lazy-img|src)="//([^"]+)"',
            html,
            flags=re.IGNORECASE,
        )
        comment_match = re.search(
            rf'data-sku="{sku_id}"[\s\S]*?(?:comment-count|J_comment).*?(\d+)',
            html,
            flags=re.IGNORECASE,
        )

        products.append(
            {
                "product_id": sku_id,
                "name": clean_html_text(name_match.group(1)) if name_match else f"JD Product {sku_id}",
                "url": f"https://item.jd.com/{sku_id}.html",
                "image_url": f"https://{image_match.group(1)}" if image_match else "",
                "comment_count": int(comment_match.group(1)) if comment_match else 0,
            }
        )

    return products


def safe_json_loads(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None


def collect_video_links(base_url: str, links: list[str], limit: int = 10) -> list[str]:
    matches: list[str] = []
    for link in normalize_links(base_url, links):
        lowered = link.lower()
        if any(lowered.endswith(ext) for ext in (".mp4", ".m3u8", ".webm", ".mov")) or "video" in lowered:
            matches.append(link)
        if len(matches) >= limit:
            break
    return matches


def extract_embedded_json_blocks(text: str, limit: int = 5, max_chars: int = 2000) -> list[str]:
    patterns = [
        r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        r'(?is)__NEXT_DATA__\s*=\s*(\{.*?\})\s*;</script>',
        r'(?is)__NUXT__\s*=\s*(\{.*?\})\s*;',
        r'(?is)__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;',
        r'(?is)__PRELOADED_STATE__\s*=\s*(\{.*?\})\s*;',
        r'(?is)__APOLLO_STATE__\s*=\s*(\{.*?\})\s*;',
    ]
    values: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        for matched in re.findall(pattern, text):
            block = text_excerpt(str(matched), max_chars)
            if block and block not in seen:
                seen.add(block)
                values.append(block)
            if len(values) >= limit:
                return values
    return values


def extract_api_candidates(text: str, limit: int = 20) -> list[str]:
    patterns = [
        r'https?://[^"\'\s<>]+',
        r'/(?:api|comment|comments|review|reviews|detail|item|items|sku|price|search)[^"\'\s<>]+',
    ]
    keywords = ("api", "comment", "review", "detail", "item", "sku", "price", "search")
    values: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        for matched in re.findall(pattern, text, flags=re.IGNORECASE):
            candidate = str(matched).strip()
            lowered = candidate.lower()
            if not any(keyword in lowered for keyword in keywords):
                continue
            if candidate not in seen:
                seen.add(candidate)
                values.append(candidate)
            if len(values) >= limit:
                return values
    return values


def _iter_json_nodes(payload):
    if isinstance(payload, dict):
        yield payload
        for value in payload.values():
            yield from _iter_json_nodes(value)
    elif isinstance(payload, list):
        for value in payload:
            yield from _iter_json_nodes(value)


def extract_json_ld_products(text: str, limit: int = 5) -> list[dict]:
    values: list[dict] = []
    for matched in re.findall(r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text):
        payload = safe_json_loads(matched)
        if payload is None:
            continue
        for node in _iter_json_nodes(payload):
            node_type = node.get("@type")
            types = node_type if isinstance(node_type, list) else [node_type]
            if not any(str(value).lower() == "product" for value in types if value):
                continue
            values.append(
                {
                    "name": node.get("name", ""),
                    "sku": node.get("sku", ""),
                    "brand": node.get("brand", {}).get("name", "") if isinstance(node.get("brand"), dict) else node.get("brand", ""),
                    "category": node.get("category", ""),
                    "url": node.get("url", ""),
                    "image": (
                        node.get("image", [""])[0]
                        if isinstance(node.get("image"), list) and node.get("image")
                        else node.get("image", "")
                    ),
                    "price": (
                        node.get("offers", {}).get("price", "")
                        if isinstance(node.get("offers"), dict)
                        else ""
                    ),
                    "currency": (
                        node.get("offers", {}).get("priceCurrency", "")
                        if isinstance(node.get("offers"), dict)
                        else ""
                    ),
                    "rating": (
                        node.get("aggregateRating", {}).get("ratingValue", "")
                        if isinstance(node.get("aggregateRating"), dict)
                        else ""
                    ),
                    "review_count": (
                        node.get("aggregateRating", {}).get("reviewCount", "")
                        if isinstance(node.get("aggregateRating"), dict)
                        else ""
                    ),
                }
            )
            if len(values) >= limit:
                return values
    return values
