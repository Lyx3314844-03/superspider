from __future__ import annotations

import json
import re
from urllib.parse import urljoin

DEFAULT_SITE_FAMILY = "jd"

API_REPLAY_KEYWORDS = (
    "api",
    "graphql",
    "comment",
    "comments",
    "review",
    "reviews",
    "detail",
    "item",
    "items",
    "sku",
    "price",
    "search",
    "product",
    "goods",
    "inventory",
)

STATIC_RESOURCE_SUFFIXES = (
    ".css",
    ".js",
    ".mjs",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp4",
    ".webm",
    ".m3u8",
    ".ts",
    ".map",
)

SENSITIVE_REPLAY_HEADERS = {
    "authorization",
    "cookie",
    "proxy-authorization",
    "set-cookie",
}

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
    "xiaohongshu": {
        "family": "xiaohongshu",
        "catalog_url": "https://www.xiaohongshu.com/search_result?keyword=iphone",
        "detail_url": "https://www.xiaohongshu.com/explore/660000000000000000000000",
        "review_url": "https://edith.xiaohongshu.com/api/sns/web/v2/comment/page",
        "runner": "browser",
        "detail_link_keywords": ["/explore/", "/discovery/item/", "note_id=", "goods_id=", "item/"],
        "next_link_keywords": ["page=", "cursor=", "note_id=", "load-more"],
        "review_link_keywords": ["comment", "comments", "edith.xiaohongshu.com", "note_id="],
        "price_patterns": [
            r"(?:price|salePrice|currentPrice|minPrice|maxPrice)[\"'=:\\s]+([0-9]+(?:\\.[0-9]{1,2})?)",
            r"(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)",
        ],
        "item_id_patterns": [
            r"(?:noteId|note_id|itemId|item_id|goodsId|goods_id|skuId|sku)[\"'=:\\s]+([A-Za-z0-9_-]+)",
        ],
        "shop_patterns": [
            r"(?:shopName|seller|sellerNick|storeName|merchantName|brand)[\"'=:\\s]+([^\"'\\n<,}]+)",
        ],
        "review_count_patterns": [
            r"(?:commentCount|comments|reviewCount|interactCount)[\"'=:\\s]+([0-9]+)",
        ],
        "rating_patterns": [
            r"(?:rating|score|ratingValue|averageRating)[\"'=:\\s]+([0-9]+(?:\.[0-9])?)",
        ],
    },
    "douyin-shop": {
        "family": "douyin-shop",
        "catalog_url": "https://www.douyin.com/search/iphone?type=commodity",
        "detail_url": "https://haohuo.jinritemai.com/views/product/item2?id=100000000000",
        "review_url": "https://www.jinritemai.com/ecommerce/trade/comment/list?id=100000000000",
        "runner": "browser",
        "detail_link_keywords": ["/product/", "/item", "item2", "product_id=", "detail", "commodity"],
        "next_link_keywords": ["page=", "cursor=", "offset=", "load-more"],
        "review_link_keywords": ["comment", "comments", "review", "jinritemai.com"],
        "price_patterns": [
            r"(?:price|salePrice|currentPrice|minPrice|maxPrice|promotionPrice)[\"'=:\\s]+([0-9]+(?:\\.[0-9]{1,2})?)",
            r"(?:￥|¥)\s*([0-9]+(?:\.[0-9]{1,2})?)",
        ],
        "item_id_patterns": [
            r"(?:productId|product_id|itemId|item_id|goodsId|goods_id|skuId|sku)[\"'=:\\s]+([A-Za-z0-9_-]+)",
        ],
        "shop_patterns": [
            r"(?:shopName|seller|sellerNick|storeName|merchantName|authorName|brand)[\"'=:\\s]+([^\"'\\n<,}]+)",
        ],
        "review_count_patterns": [
            r"(?:commentCount|comments|reviewCount|soldCount|sales)[\"'=:\\s]+([0-9]+)",
        ],
        "rating_patterns": [
            r"(?:rating|score|ratingValue|averageRating)[\"'=:\\s]+([0-9]+(?:\.[0-9])?)",
        ],
    },
}


def get_profile(site_family: str | None = None) -> dict:
    family = (site_family or DEFAULT_SITE_FAMILY).lower()
    if family in SITE_PROFILES:
        return SITE_PROFILES[family]
    if site_family is None:
        return SITE_PROFILES[DEFAULT_SITE_FAMILY]
    return SITE_PROFILES["generic"]


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
        r'(?is)<script[^>]+type=["\']application/json["\'][^>]*>(.*?)</script>',
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
    for raw_payload in _raw_embedded_json_payloads(text):
        payload = safe_json_loads(raw_payload)
        if payload is None:
            continue
        for node in _iter_json_nodes(payload):
            if isinstance(node, dict):
                for value in node.values():
                    candidate = _api_candidate_from_json_value(value)
                    if candidate and candidate not in seen:
                        seen.add(candidate)
                        values.append(candidate)
                    if len(values) >= limit:
                        return values
    return values


def normalize_network_entries(artifact, limit: int = 50) -> list[dict]:
    """Normalize browser listen_network, HAR, and trace-like artifacts."""
    raw_entries = _raw_network_entries(artifact, limit=limit * 4)
    values: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for raw_entry, source in raw_entries:
        entry = _normalize_network_entry(raw_entry, source)
        if not entry:
            continue
        fingerprint = (
            entry.get("method", "GET"),
            entry.get("url", ""),
            entry.get("post_data", ""),
        )
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        values.append(entry)
        if len(values) >= limit:
            break
    return values


def extract_network_api_candidates(artifact, limit: int = 20) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for entry in normalize_network_entries(artifact, limit=limit * 4):
        if not _is_replayable_network_entry(entry):
            continue
        url = str(entry.get("url") or "").strip()
        if url and url not in seen:
            seen.add(url)
            values.append(url)
        if len(values) >= limit:
            break
    return values


def build_network_replay_job_templates(
    base_url: str,
    site_family: str,
    network_artifact,
    limit: int = 10,
) -> list[dict]:
    family = (site_family or "generic").strip() or "generic"
    templates: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for entry in normalize_network_entries(network_artifact, limit=limit * 4):
        if not _is_replayable_network_entry(entry):
            continue
        method = str(entry.get("method") or "GET").upper()
        url = str(entry.get("url") or "").strip()
        post_data = str(entry.get("post_data") or "")
        fingerprint = (method, url, post_data)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)

        target = {
            "url": url,
            "method": method,
            "headers": _safe_replay_headers(entry.get("request_headers", {}), base_url),
        }
        if method not in {"GET", "HEAD"} and post_data:
            target["body"] = post_data
        templates.append(
            {
                "name": f"{family}-network-api-{len(templates) + 1}",
                "runtime": "http",
                "target": target,
                "output": {"format": "json"},
                "metadata": {
                    "site_family": family,
                    "source_url": base_url,
                    "source": entry.get("source", "network_artifact"),
                    "status": entry.get("status"),
                    "resource_type": entry.get("resource_type", ""),
                    "content_type": entry.get("content_type", ""),
                },
            }
        )
        if len(templates) >= limit:
            break
    return templates


def merge_api_job_templates(*template_groups: list[dict], limit: int = 20) -> list[dict]:
    values: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for group in template_groups:
        for template in group or []:
            target = template.get("target", {}) if isinstance(template, dict) else {}
            key = (
                str(target.get("method") or "GET").upper(),
                str(target.get("url") or ""),
                str(target.get("body") or ""),
            )
            if not key[1] or key in seen:
                continue
            seen.add(key)
            values.append(template)
            if len(values) >= limit:
                return values
    return values


def get_response_network_artifact(response):
    request = getattr(response, "request", None)
    meta = getattr(request, "meta", {}) or {}
    direct = _first_artifact_value(meta)
    if direct is not None:
        return direct
    browser_meta = meta.get("browser")
    if isinstance(browser_meta, dict):
        direct = _first_artifact_value(browser_meta)
        if direct is not None:
            return direct
    for attr_name in ("network_entries", "network_events", "network", "har", "trace"):
        if hasattr(response, attr_name):
            value = getattr(response, attr_name)
            if value not in (None, "", [], {}):
                return value
    return None


def append_unique_strings(*groups: list[str], limit: int = 20) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for raw_value in group or []:
            value = str(raw_value or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            values.append(value)
            if len(values) >= limit:
                return values
    return values


def _raw_network_entries(artifact, limit: int = 200) -> list[tuple[dict, str]]:
    payload = _network_payload_from_artifact(artifact)
    values: list[tuple[dict, str]] = []
    if isinstance(payload, str):
        for url in re.findall(r'https?://[^\s"\'<>]+', payload):
            values.append(({"url": url, "method": "GET"}, "network_text"))
            if len(values) >= limit:
                return values
        return values
    _collect_network_entries(payload, values, "network_artifact", limit)
    return values


def _network_payload_from_artifact(artifact):
    if artifact in (None, "", [], {}):
        return None
    if isinstance(artifact, (list, dict)):
        return artifact
    if isinstance(artifact, bytes):
        artifact = artifact.decode("utf-8", errors="ignore")
    if isinstance(artifact, str):
        text = artifact.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            return text
    return artifact


def _collect_network_entries(payload, values: list[tuple[dict, str]], source: str, limit: int) -> None:
    if len(values) >= limit or payload in (None, "", [], {}):
        return
    if isinstance(payload, list):
        for item in payload:
            _collect_network_entries(item, values, source, limit)
            if len(values) >= limit:
                return
        return
    if not isinstance(payload, dict):
        return

    if _looks_like_network_entry(payload):
        values.append((payload, source))
        return

    har_entries = payload.get("log", {}).get("entries") if isinstance(payload.get("log"), dict) else None
    if isinstance(har_entries, list):
        for item in har_entries:
            if isinstance(item, dict):
                values.append((item, "har"))
            if len(values) >= limit:
                return

    for key, nested_source in (
        ("network_events", "network_events"),
        ("networkEntries", "network_entries"),
        ("network_entries", "network_entries"),
        ("requests", "requests"),
        ("entries", "entries"),
        ("events", "events"),
    ):
        nested = payload.get(key)
        if isinstance(nested, list):
            for item in nested:
                if isinstance(item, dict):
                    values.append((item, nested_source))
                if len(values) >= limit:
                    return

    extract = payload.get("extract")
    if isinstance(extract, dict):
        for value in extract.values():
            if isinstance(value, list):
                _collect_network_entries(value, values, "listen_network", limit)
                if len(values) >= limit:
                    return

    fetched = payload.get("fetched")
    if isinstance(fetched, dict) and fetched.get("final_url"):
        values.append(
            (
                {
                    "url": fetched.get("final_url"),
                    "method": "GET",
                    "status": fetched.get("status"),
                },
                "trace",
            )
        )


def _looks_like_network_entry(value: dict) -> bool:
    if not isinstance(value, dict):
        return False
    request = value.get("request") if isinstance(value.get("request"), dict) else {}
    return bool(
        value.get("url")
        or value.get("name")
        or value.get("request_url")
        or request.get("url")
    )


def _normalize_network_entry(raw: dict, source: str) -> dict | None:
    request = raw.get("request") if isinstance(raw.get("request"), dict) else {}
    response = raw.get("response") if isinstance(raw.get("response"), dict) else {}
    url = (
        _text_value(raw.get("url"))
        or _text_value(raw.get("name"))
        or _text_value(raw.get("request_url"))
        or _text_value(request.get("url"))
    )
    if not url:
        return None
    method = (
        _text_value(raw.get("method"))
        or _text_value(request.get("method"))
        or "GET"
    ).upper()
    request_headers = _header_map(
        raw.get("request_headers")
        or raw.get("requestHeaders")
        or request.get("headers")
        or {}
    )
    response_headers = _header_map(
        raw.get("response_headers")
        or raw.get("responseHeaders")
        or response.get("headers")
        or {}
    )
    content_type = (
        _text_value(raw.get("content_type"))
        or _text_value(raw.get("mimeType"))
        or _text_value(response.get("content", {}).get("mimeType") if isinstance(response.get("content"), dict) else "")
        or _header_lookup(response_headers, "content-type")
    )
    return {
        "url": url,
        "method": method,
        "status": _int_value(raw.get("status") or response.get("status")),
        "resource_type": _text_value(raw.get("resource_type") or raw.get("resourceType") or raw.get("type")),
        "content_type": content_type,
        "source": source,
        "request_headers": request_headers,
        "response_headers": response_headers,
        "post_data": _post_data(raw, request),
    }


def _is_replayable_network_entry(entry: dict) -> bool:
    url = str(entry.get("url") or "").strip()
    method = str(entry.get("method") or "GET").upper()
    if not url.startswith(("http://", "https://")) or method == "OPTIONS":
        return False
    lowered_url = url.lower().split("?", 1)[0]
    if any(lowered_url.endswith(suffix) for suffix in STATIC_RESOURCE_SUFFIXES):
        return False
    content_type = str(entry.get("content_type") or "").lower()
    resource_type = str(entry.get("resource_type") or "").lower()
    return (
        method not in {"GET", "HEAD"}
        or "json" in content_type
        or "graphql" in content_type
        or "event-stream" in content_type
        or resource_type in {"fetch", "xhr", "eventsource"}
        or any(keyword in url.lower() for keyword in API_REPLAY_KEYWORDS)
    )


def _safe_replay_headers(headers, base_url: str) -> dict[str, str]:
    values: dict[str, str] = {}
    if isinstance(headers, dict):
        for key, value in headers.items():
            header = str(key or "").strip()
            if not header:
                continue
            lowered = header.lower()
            if lowered in SENSITIVE_REPLAY_HEADERS:
                continue
            text = _text_value(value)
            if text:
                values[header] = text
    if base_url and not any(key.lower() == "referer" for key in values):
        values["Referer"] = base_url
    return values


def _first_artifact_value(mapping: dict):
    for key in (
        "network_artifact",
        "network_entries",
        "network_events",
        "listen_network",
        "network",
        "har",
        "trace",
    ):
        value = mapping.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _header_map(value) -> dict[str, str]:
    headers: dict[str, str] = {}
    if isinstance(value, dict):
        for key, raw in value.items():
            text = _text_value(raw)
            if text:
                headers[str(key)] = text
        return headers
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            name = _text_value(item.get("name") or item.get("key"))
            text = _text_value(item.get("value"))
            if name and text:
                headers[name] = text
    return headers


def _header_lookup(headers: dict[str, str], key: str) -> str:
    lowered = key.lower()
    for header, value in headers.items():
        if header.lower() == lowered:
            return value
    return ""


def _post_data(raw: dict, request: dict) -> str:
    for value in (
        raw.get("post_data"),
        raw.get("postData"),
        raw.get("body"),
        request.get("postData"),
        request.get("body"),
    ):
        if isinstance(value, dict):
            text = _text_value(value.get("text"))
            if text:
                return text
        text = _text_value(value)
        if text:
            return text
    return ""


def _text_value(value) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, (str, int, float)):
        return str(value).strip()
    return ""


def _int_value(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _api_candidate_from_json_value(value) -> str:
    if not isinstance(value, str):
        return ""
    candidate = value.strip()
    lowered = candidate.lower()
    keywords = ("api", "comment", "comments", "review", "reviews", "detail", "item", "items", "sku", "price", "search")
    if not any(keyword in lowered for keyword in keywords):
        return ""
    if candidate.startswith(("http://", "https://", "/")):
        return candidate
    if any(lowered.startswith(prefix) for prefix in ("api/", "comment", "review", "detail", "item/", "items/", "search", "price")):
        return candidate
    return ""


def normalize_api_candidates(base_url: str, candidates: list[str], limit: int = 20) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for raw_candidate in candidates:
        candidate = str(raw_candidate or "").strip()
        if not candidate:
            continue
        absolute = candidate if candidate.startswith(("http://", "https://")) else urljoin(base_url, candidate)
        if not absolute.startswith(("http://", "https://")):
            continue
        if absolute not in seen:
            seen.add(absolute)
            values.append(absolute)
        if len(values) >= limit:
            break
    return values


def build_api_job_templates(
    base_url: str,
    site_family: str,
    api_candidates: list[str],
    item_ids: list[str] | None = None,
    limit: int = 10,
) -> list[dict]:
    values: list[str] = []
    family = (site_family or "generic").strip() or "generic"
    clean_item_ids = [str(item_id).strip() for item_id in (item_ids or []) if str(item_id).strip()]

    if family == "jd" and clean_item_ids:
        values.append(build_jd_price_api_url(clean_item_ids[:3]))
        values.append(build_jd_review_api_url(clean_item_ids[0]))

    values.extend(normalize_api_candidates(base_url, api_candidates, limit=limit * 2))

    templates: list[dict] = []
    seen: set[str] = set()
    for index, url in enumerate(values, start=1):
        if url in seen:
            continue
        seen.add(url)
        templates.append(
            {
                "name": f"{family}-api-{len(templates) + 1}",
                "runtime": "http",
                "target": {
                    "url": url,
                    "method": "GET",
                    "headers": {"Referer": base_url},
                },
                "output": {"format": "json"},
                "metadata": {
                    "site_family": family,
                    "source_url": base_url,
                    "candidate_index": index,
                },
            }
        )
        if len(templates) >= limit:
            break
    return templates


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


def _raw_embedded_json_payloads(text: str):
    patterns = [
        r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        r'(?is)<script[^>]+type=["\']application/json["\'][^>]*>(.*?)</script>',
        r'(?is)__NEXT_DATA__\s*=\s*(\{.*?\})\s*;</script>',
        r'(?is)__NUXT__\s*=\s*(\{.*?\})\s*;',
        r'(?is)__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;',
        r'(?is)__PRELOADED_STATE__\s*=\s*(\{.*?\})\s*;',
        r'(?is)__APOLLO_STATE__\s*=\s*(\{.*?\})\s*;',
    ]
    for pattern in patterns:
        for matched in re.findall(pattern, text):
            yield str(matched).strip()


def _first_non_empty(node: dict, keys: list[str]):
    for key in keys:
        value = node.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _nested_first(node: dict, paths: list[tuple[str, ...]]):
    for path in paths:
        value = node
        for key in path:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _as_text(value) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, (str, int, float)):
        return str(value).strip()
    return ""


def _as_image(value) -> str:
    if isinstance(value, list) and value:
        return _as_text(value[0])
    return _as_text(value)


def _normalize_bootstrap_product(node: dict) -> dict | None:
    if not isinstance(node, dict):
        return None

    name = _as_text(
        _first_non_empty(
            node,
            ["name", "title", "itemName", "productName", "goodsName", "noteTitle", "note_title"],
        )
    )
    sku = _as_text(
        _first_non_empty(
            node,
            ["sku", "skuId", "itemId", "item_id", "productId", "product_id", "goodsId", "goods_id", "noteId", "note_id", "asin", "id"],
        )
    )
    url = _as_text(
        _first_non_empty(node, ["url", "detailUrl", "itemUrl", "shareUrl", "jumpUrl", "link"])
    )
    image = _as_image(
        _first_non_empty(node, ["image", "imageUrl", "imageURL", "pic", "picUrl", "cover", "coverUrl", "mainImage", "img"])
    )
    price = _as_text(
        _first_non_empty(node, ["price", "salePrice", "currentPrice", "finalPrice", "minPrice", "maxPrice", "promotionPrice", "groupPrice", "jdPrice", "priceToPay", "displayPrice", "priceAmount"])
        or _nested_first(node, [("offers", "price"), ("offers", "lowPrice"), ("priceInfo", "price"), ("currentSku", "price"), ("product", "price")])
    )
    currency = _as_text(
        _first_non_empty(node, ["currency", "priceCurrency"]) or _nested_first(node, [("offers", "priceCurrency"), ("priceInfo", "currency")])
    )
    brand = _as_text(
        _first_non_empty(node, ["brand", "brandName"]) or _nested_first(node, [("brand", "name"), ("brandInfo", "name")])
    )
    category = _as_text(_first_non_empty(node, ["category", "categoryName"]))
    rating = _as_text(
        _first_non_empty(node, ["rating", "score", "ratingValue", "averageRating"])
        or _nested_first(node, [("aggregateRating", "ratingValue"), ("ratings", "average")])
    )
    review_count = _as_text(
        _first_non_empty(node, ["reviewCount", "commentCount", "comments", "ratingsTotal", "totalReviewCount", "soldCount", "sales", "interactCount"])
        or _nested_first(node, [("aggregateRating", "reviewCount"), ("aggregateRating", "ratingCount")])
    )
    shop = _as_text(
        _first_non_empty(node, ["shopName", "seller", "sellerNick", "storeName", "merchantName", "vendor", "authorName", "mall_name"])
    )

    score = 0
    score += 1 if (name or sku) else 0
    score += 1 if price else 0
    score += 1 if (image or url) else 0
    score += 1 if (shop or rating or review_count) else 0
    if score < 2:
        return None

    return {
        "name": name,
        "sku": sku,
        "brand": brand,
        "category": category,
        "url": url,
        "image": image,
        "price": price,
        "currency": currency,
        "rating": rating,
        "review_count": review_count,
        "shop": shop,
    }


def extract_bootstrap_products(text: str, limit: int = 5) -> list[dict]:
    values: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()
    for raw_payload in _raw_embedded_json_payloads(text):
        payload = safe_json_loads(raw_payload)
        if payload is None:
            continue
        for node in _iter_json_nodes(payload):
            product = _normalize_bootstrap_product(node)
            if not product:
                continue
            fingerprint = (
                product.get("sku", ""),
                product.get("url", ""),
                product.get("name", ""),
                product.get("price", ""),
            )
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            values.append(product)
            if len(values) >= limit:
                return values
    return values


# ═══════════════════════════════════════════════════════════════════════
# Enhanced Data Extraction Functions (v2.0 upgrade)
# - SKU/Variant extraction
# - Image gallery extraction
# - Parameter/spec table extraction
# - Coupon/promotion detection
# - Stock/availability monitoring
# ═══════════════════════════════════════════════════════════════════════

# ── SKU Variant Extraction ────────────────────────────────────────────────

SKU_VARIANT_SELECTORS = [
    # Common CSS class/attribute patterns for variant selectors
    r'class="[^"]*sku[^"]*"',
    r'class="[^"]*variant[^"]*"',
    r'class="[^"]*spec[^"]*select[^"]*"',
    r'class="[^"]*option[^"]*item[^"]*"',
    r'class="[^"]*color[^"]*item[^"]*"',
    r'class="[^"]*size[^"]*item[^"]*"',
    r'data-sku',
    r'data-variant-id',
    r'data-spec-value',
    r'data-attr-value',
]

VARIANT_KEY_PATTERNS = [
    r'"(colo[u]?r|\u989c\u8272|\u989c\u8272)"\s*:\s*"([^"]+)"',
    r'"(size|\u5c3a\u7801|\u5c3a\u5bf8)"\s*:\s*"([^"]+)"',
    r'"(storage|\u5b58\u50a8|\u5185\u5b58)"\s*:\s*"([^"]+)"',
    r'"(style|\u6b3e\u5f0f)"\s*:\s*"([^"]+)"',
    r'"(version|\u7248\u672c|\u89c4\u683c)"\s*:\s*"([^"]+)"',
]


def extract_sku_variants(html: str, selector=None) -> list:
    """Extract SKU variant/specification options from product page.

    Returns list of dicts with keys: name, values, sku_id (if found)
    """
    variants = []

    # Strategy 1: Extract from JSON-LD / structured data
    json_ld_variants = _extract_variants_from_structured_data(html)
    if json_ld_variants:
        variants.extend(json_ld_variants)

    # Strategy 2: Extract from embedded JSON (bootstrap / __NEXT_DATA__)
    bootstrap_variants = _extract_variants_from_bootstrap(html)
    if bootstrap_variants:
        variants.extend(bootstrap_variants)

    # Strategy 3: Regex-based extraction from HTML
    if not variants:
        regex_variants = _extract_variants_by_regex(html)
        if regex_variants:
            variants.extend(regex_variants)

    # Strategy 4: CSS selector-based (if selector available)
    if selector and not variants:
        css_variants = _extract_variants_from_css(html, selector)
        if css_variants:
            variants.extend(css_variants)

    return variants


def _extract_variants_from_structured_data(html: str) -> list:
    """Extract variants from JSON-LD or schema.org data."""
    variants = []
    # Look for offers with different SKU/price combinations
    json_ld_products = extract_json_ld_products(html)
    seen_names = set()
    for product in json_ld_products:
        offers = product.get("offers", {})
        if isinstance(offers, list):
            for offer in offers:
                variant_name = offer.get("name", "") or offer.get("sku", "")
                if variant_name and variant_name not in seen_names:
                    seen_names.add(variant_name)
                    variants.append({
                        "name": offer.get("name", ""),
                        "sku": offer.get("sku", ""),
                        "price": offer.get("price", ""),
                        "availability": offer.get("availability", ""),
                        "color": offer.get("color", ""),
                        "size": offer.get("size", ""),
                    })
        elif isinstance(offers, dict):
            # Single offer - check for variant indicators
            sku = offers.get("sku", "") or product.get("sku", "")
            if sku:
                variants.append({
                    "name": product.get("name", ""),
                    "sku": sku,
                    "price": offers.get("price", ""),
                    "availability": offers.get("availability", ""),
                })
    return variants


def _extract_variants_from_bootstrap(html: str) -> list:
    """Extract variant/spec data from embedded JSON blocks."""
    variants = []
    blocks = extract_embedded_json_blocks(html)
    for block in blocks:
        payload = safe_json_loads(block)
        if not payload:
            continue
        # Walk the JSON tree looking for variant-like structures
        _walk_for_variants(payload, variants, depth=0, max_depth=6)
    return variants[:20]  # Cap at 20 variants


def _walk_for_variants(node, variants: list, depth: int, max_depth: int):
    """Recursively walk JSON looking for variant-like key patterns."""
    if depth > max_depth or len(variants) >= 20:
        return
    if isinstance(node, dict):
        for key, val in node.items():
            key_lower = key.lower()
            # Detect variant specification arrays
            if key_lower in ("skus", "variants", "specs", "sale_attrs",
                             "attr_list", "spec_items", "variant_list",
                             "skulist", "product_options", "attributes"):
                if isinstance(val, list):
                    for item in val[:10]:
                        if isinstance(item, dict):
                            variants.append({
                                "name": _as_text(item.get("name" or item.get("attr_name" or item.get("spec_name", "")))),
                                "values": _extract_variant_values(item),
                                "sku_id": _as_text(item.get("sku_id" or item.get("skuId" or item.get("id", "")))),
                            })
            # Detect single variant objects with key patterns
            for pat in VARIANT_KEY_PATTERNS:
                m = re.search(pat, json.dumps(node, default=str) if isinstance(node, (dict, list)) else str(node))
                if m:
                    variants.append({
                        "name": m.group(1),
                        "values": [m.group(2)],
                    })
                    break
            _walk_for_variants(val, variants, depth + 1, max_depth)
    elif isinstance(node, list):
        for item in node[:10]:
            _walk_for_variants(item, variants, depth + 1, max_depth)


def _extract_variant_values(item: dict) -> list:
    """Extract variant option values from a variant item dict."""
    values = []
    # Common key names for variant value lists
    for vkey in ("values", "options", "list", "value_list", "attr_values", "spec_values"):
        v = item.get(vkey)
        if isinstance(v, list):
            for entry in v[:15]:
                if isinstance(entry, dict):
                    val = _as_text(entry.get("name" or entry.get("value" or entry.get("text", ""))))
                elif isinstance(entry, str):
                    val = entry
                else:
                    val = str(entry)
                if val:
                    values.append(val)
            break
    return values[:15]


def _extract_variants_by_regex(html: str) -> list:
    """Extract variant data using regex patterns on raw HTML."""
    variants = []
    for pat in VARIANT_KEY_PATTERNS:
        matches = re.findall(pat, html)
        for m in matches:
            if isinstance(m, tuple) and len(m) >= 2:
                variants.append({"name": m[0], "values": [m[1]]})
    # Deduplicate
    seen = set()
    unique = []
    for v in variants:
        key = f"{v['name']}:{','.join(v['values'])}"
        if key not in seen:
            seen.add(key)
            unique.append(v)
    return unique[:10]


def _extract_variants_from_css(html: str, selector) -> list:
    """Extract variant options using CSS selector (fallback)."""
    variants = []
    try:
        # Look for select/option elements that likely represent variants
        option_groups = selector.css("select[name*=sku], select[name*=variant], select[name*=spec], select[name*=attr], select[name*=size], select[name*=color]")
        for group in option_groups:
            name = group.attrib.get("name", "")
            options = [opt.text.strip() for opt in group.css("option") if opt.text and opt.text.strip()]
            if options:
                variants.append({"name": name, "values": options})
    except Exception:
        pass
    return variants


# ── Image Gallery Extraction ────

def extract_image_gallery(page_url: str, img_srcs: list[str], limit: int = 30) -> list[dict]:
    """Build a normalized product image gallery from raw image src values."""
    gallery: list[dict] = []
    seen: set[str] = set()
    for src in img_srcs:
        if not src:
            continue
        abs_url = urljoin(page_url, src.strip())
        lowered = abs_url.lower()
        if abs_url in seen or any(token in lowered for token in ("sprite", "blank", "placeholder", "loading.gif")):
            continue
        seen.add(abs_url)
        kind = "main" if not gallery else "gallery"
        if "thumb" in lowered or "60x60" in lowered or "50x50" in lowered:
            kind = "thumbnail"
        gallery.append({"url": abs_url, "alt": "", "kind": kind})
        if len(gallery) >= limit:
            break
    return gallery


def extract_parameter_table(html: str, limit: int = 30) -> list[dict]:
    """Extract product parameter/specification key-value pairs."""
    params: list[dict] = []
    for key, value in re.findall(
        r"(?is)<tr[^>]*>\s*<t[dh][^>]*>(.*?)</t[dh]>\s*<t[dh][^>]*>(.*?)</t[dh]>",
        html,
    ):
        clean_key = _clean_html_text(key)
        clean_value = _clean_html_text(value)
        if clean_key and clean_value and len(clean_key) < 80:
            params.append({"key": clean_key, "value": clean_value})
        if len(params) >= limit:
            return params

    for block in extract_embedded_json_blocks(html, limit=5, max_chars=4000):
        for key, value in re.findall(r'"([\w\u4e00-\u9fa5]{2,30})"\s*:\s*"([^"]{1,120})"', block):
            if key and value:
                params.append({"key": key, "value": value})
            if len(params) >= limit:
                return params
    return params


def detect_coupons_promotions(html: str, limit: int = 10) -> list[dict]:
    """Detect coupon and promotion signals without requiring site-specific selectors."""
    signals: list[dict] = []
    patterns = [
        r'class="[^"]*(coupon|promo|promotion|discount|voucher)[^"]*"',
        r"data-(coupon|promo|promotion|discount|voucher)",
        r"([\u4fc3\u9500\u4f18\u60e0\u5238\u6ee1\u51cf\u6298\u6263]{2,12})",
    ]
    seen: set[str] = set()
    for pattern in patterns:
        for match in re.findall(pattern, html, flags=re.I):
            text = match[0] if isinstance(match, tuple) else match
            text = str(text).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            signals.append({"type": "promotion", "description": text})
            if len(signals) >= limit:
                return signals
    return signals


def extract_stock_status(html: str) -> dict:
    """Classify stock/availability state from common text signals."""
    lowered = html.lower()
    out_of_stock = ("售罄", "无货", "sold out", "out of stock", "currently unavailable", "暂无库存")
    in_stock = ("有货", "开放购买", "in stock", "add to cart", "立即购买", "预售")
    limited = ("仅限", "limited", "即将售罄")
    if any(signal.lower() in lowered for signal in out_of_stock):
        return {"status": "out_of_stock"}
    if any(signal.lower() in lowered for signal in in_stock):
        return {"status": "in_stock"}
    if any(signal.lower() in lowered for signal in limited):
        return {"status": "limited"}
    return {"status": "unknown"}


def _clean_html_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()
