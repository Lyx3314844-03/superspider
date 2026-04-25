"""Universal e-commerce site detector for pyspider examples."""

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EcommerceDetectionResult:
    is_ecommerce: bool = False
    confidence: float = 0.0
    site_family: str = "generic"
    platform: str = ""
    detected_features: list[str] = field(default_factory=list)
    currency: str = ""
    language: str = ""
    has_jsonld: bool = False
    has_next_data: bool = False
    has_initial_state: bool = False
    price_api_detected: bool = False
    cart_url: str = ""
    category_urls: list[str] = field(default_factory=list)


URL_SIGNATURES: dict[str, dict[str, Any]] = {
    "jd": {"patterns": [r"jd\.com", r"jd\.hk"], "confidence": 0.95, "currency": "CNY"},
    "taobao": {"patterns": [r"taobao\.com"], "confidence": 0.95, "currency": "CNY"},
    "tmall": {"patterns": [r"tmall\.com"], "confidence": 0.95, "currency": "CNY"},
    "pinduoduo": {"patterns": [r"pinduoduo\.com", r"yangkeduo\.com", r"pdd\.com"], "confidence": 0.95, "currency": "CNY"},
    "1688": {"patterns": [r"1688\.com"], "confidence": 0.95, "currency": "CNY"},
    "suning": {"patterns": [r"suning\.com"], "confidence": 0.90, "currency": "CNY"},
    "vip": {"patterns": [r"vip\.com", r"vipshop\.com"], "confidence": 0.95, "currency": "CNY"},
    "xiaohongshu": {"patterns": [r"xiaohongshu\.com", r"xhscdn\.com"], "confidence": 0.95, "currency": "CNY"},
    "douyin-shop": {"patterns": [r"douyin\.com", r"jinritemai\.com", r"life\.douyin"], "confidence": 0.90, "currency": "CNY"},
    "kuaishou-shop": {"patterns": [r"kuaishou\.com", r"kwai\.com"], "confidence": 0.90, "currency": "CNY"},
    "amazon": {"patterns": [r"amazon\.(com|co\.uk|de|fr|it|es|co\.jp|com\.au|ca|in|com\.br|com\.mx|nl|pl|se|ae|sa|sg)"], "confidence": 0.95, "currency": "USD"},
    "ebay": {"patterns": [r"ebay\.(com|co\.uk|de|fr|it|es|com\.au|ca|ch|at|be|nl|ie|pl|ph|in|my|sg)"], "confidence": 0.95, "currency": "USD"},
    "aliexpress": {"patterns": [r"aliexpress\.(com|us|es|ru|pt|fr|de|it|nl|ja|ko|ar|th|vi|id|he|pl|tr)"], "confidence": 0.95, "currency": "USD"},
    "lazada": {"patterns": [r"lazada\.(com|com\.my|com\.ph|co\.id|co\.th|vn)"], "confidence": 0.95, "currency": "USD"},
    "shopee": {"patterns": [r"shopee\.(com|co\.th|co\.id|com\.my|com\.ph|vn|tw|br|cl|pl)"], "confidence": 0.95, "currency": "USD"},
    "rakuten": {"patterns": [r"rakuten\.(co\.jp|com|com\.tw|co\.kr)"], "confidence": 0.95, "currency": "JPY"},
    "walmart": {"patterns": [r"walmart\.(com|ca)"], "confidence": 0.95, "currency": "USD"},
    "bestbuy": {"patterns": [r"bestbuy\.(com|ca)"], "confidence": 0.95, "currency": "USD"},
    "target": {"patterns": [r"target\.com"], "confidence": 0.95, "currency": "USD"},
    "costco": {"patterns": [r"costco\.(com|ca|co\.uk|com\.au|com\.jp|com\.kr|com\.tw|com\.mx)"], "confidence": 0.95, "currency": "USD"},
    "newegg": {"patterns": [r"newegg\.(com|ca|com\.global)"], "confidence": 0.95, "currency": "USD"},
    "temu": {"patterns": [r"temu\.(com|co\.uk|co\.jp|de|fr|es|it|nl|be|at|se|pl|pt|ch|dk|fi|gr|cz|hu|ro|bg)"], "confidence": 0.95, "currency": "USD"},
    "shein": {"patterns": [r"shein\.(com|co\.uk|co\.jp|de|fr|es|it|nl|se|at|pl|pt|ch|dk|fi|gr|cz|hu|ro|bg)"], "confidence": 0.95, "currency": "USD"},
    "mercadolibre": {"patterns": [r"mercadolibre\.(com\.ar|com\.mx|com\.br|com\.co|com\.pe|cl|com\.uy)"], "confidence": 0.95, "currency": "USD"},
    "ozon": {"patterns": [r"ozon\.ru"], "confidence": 0.95, "currency": "RUB"},
    "wildberries": {"patterns": [r"wildberries\.ru"], "confidence": 0.95, "currency": "RUB"},
    "allegro": {"patterns": [r"allegro\.(pl|cz|sk|hu|ro|bg)"], "confidence": 0.95, "currency": "PLN"},
    "cdiscount": {"patterns": [r"cdiscount\.com"], "confidence": 0.95, "currency": "EUR"},
}

PLATFORM_SIGNATURES: dict[str, dict[str, Any]] = {
    "shopify": {"html": ["shopify.com", "cdn.shopify", "Shopify.theme"], "confidence": 0.90},
    "magento": {"html": ["Magento_", "mage-cache", "mage/cookies"], "confidence": 0.90},
    "woocommerce": {"html": ["woocommerce", "wp-content/plugins/woocommerce"], "confidence": 0.85},
    "bigcommerce": {"html": ["bigcommerce", "bc.js"], "confidence": 0.90},
    "prestashop": {"html": ["prestashop", "ps-shoppingcart"], "confidence": 0.90},
    "wix": {"html": ["wix.com", "wixstores"], "confidence": 0.80},
    "squarespace": {"html": ["squarespace.com", "sqs-shop"], "confidence": 0.80},
    "salesforce": {"html": ["demandware", "sfcc", "commercecloud"], "confidence": 0.85},
}

ECOMMERCE_HTML_SIGNALS = [
    r'"@type"\s*:\s*"Product"',
    r'"@type"\s*:\s*"Offer"',
    r'"@type"\s*:\s*"AggregateOffer"',
    r'class=["\'][^"\']*price[^"\']*["\']',
    r'class=["\'][^"\']*product[^"\']*["\']',
    r'class=["\'][^"\']*add-to-cart[^"\']*["\']',
    r'shopping[\-]?cart',
    r'data-product-id',
    r'data-sku',
    r'data-variant-id',
    r'itemtype=["\']https?://schema\.org/Product["\']',
    r'[\$€£¥₹₩₽][\d,]+\.?\d*',
]

SITE_FAMILY_URLS = {
    "jd": {"cart_url": "https://cart.jd.com/", "category_urls": ["https://channel.jd.com/"]},
    "taobao": {"cart_url": "https://cart.taobao.com/", "category_urls": ["https://www.taobao.com/tbhome/"]},
    "tmall": {"cart_url": "https://cart.tmall.com/", "category_urls": ["https://www.tmall.com/"]},
    "amazon": {"cart_url": "https://www.amazon.com/gp/cart/", "category_urls": ["https://www.amazon.com/best-sellers/"]},
}


class UniversalEcommerceDetector:
    @staticmethod
    def detect(url: str, html: str = "", headers: dict[str, str] | None = None) -> EcommerceDetectionResult:
        result = EcommerceDetectionResult()
        if not url:
            return result

        for candidate in (
            UniversalEcommerceDetector._detect_by_url(url),
            UniversalEcommerceDetector._detect_by_platform(html),
            UniversalEcommerceDetector._detect_by_html(html),
            UniversalEcommerceDetector._detect_by_structured_data(html),
            UniversalEcommerceDetector._detect_by_price_api(html, headers or {}),
        ):
            UniversalEcommerceDetector._merge(result, candidate)

        if result.site_family in SITE_FAMILY_URLS:
            profile = SITE_FAMILY_URLS[result.site_family]
            result.cart_url = profile["cart_url"]
            result.category_urls = list(profile["category_urls"])
        return result

    @staticmethod
    def _merge(result: EcommerceDetectionResult, candidate: EcommerceDetectionResult | None) -> None:
        if candidate is None:
            return
        result.is_ecommerce = result.is_ecommerce or candidate.is_ecommerce
        result.confidence = max(result.confidence, candidate.confidence)
        if result.site_family == "generic" and candidate.site_family != "generic":
            result.site_family = candidate.site_family
        if not result.platform and candidate.platform:
            result.platform = candidate.platform
        if not result.currency and candidate.currency:
            result.currency = candidate.currency
        result.has_jsonld = result.has_jsonld or candidate.has_jsonld
        result.has_next_data = result.has_next_data or candidate.has_next_data
        result.has_initial_state = result.has_initial_state or candidate.has_initial_state
        result.price_api_detected = result.price_api_detected or candidate.price_api_detected
        for feature in candidate.detected_features:
            if feature not in result.detected_features:
                result.detected_features.append(feature)

    @staticmethod
    def _detect_by_url(url: str) -> EcommerceDetectionResult | None:
        for family, signature in URL_SIGNATURES.items():
            if any(re.search(pattern, url, re.I) for pattern in signature["patterns"]):
                return EcommerceDetectionResult(
                    is_ecommerce=True,
                    confidence=float(signature["confidence"]),
                    site_family=family,
                    platform=family,
                    currency=str(signature.get("currency", "")),
                    detected_features=["url_pattern"],
                )
        return None

    @staticmethod
    def _detect_by_platform(html: str) -> EcommerceDetectionResult | None:
        if not html:
            return None
        lowered = html.lower()
        for platform, signature in PLATFORM_SIGNATURES.items():
            if any(needle.lower() in lowered for needle in signature["html"]):
                return EcommerceDetectionResult(
                    is_ecommerce=True,
                    confidence=float(signature["confidence"]),
                    platform=platform,
                    detected_features=["platform_signature"],
                )
        return None

    @staticmethod
    def _detect_by_html(html: str) -> EcommerceDetectionResult | None:
        if not html:
            return None
        signals = sum(1 for pattern in ECOMMERCE_HTML_SIGNALS if re.search(pattern, html, re.I))
        has_jsonld = "application/ld+json" in html
        has_next_data = "__NEXT_DATA__" in html or "__NUXT__" in html
        has_initial_state = "__INITIAL_STATE__" in html or "__PRELOADED_STATE__" in html
        if has_jsonld:
            signals += 2
        if has_next_data or has_initial_state:
            signals += 1
        if signals < 2:
            return None
        return EcommerceDetectionResult(
            is_ecommerce=True,
            confidence=min(0.85, signals * 0.15),
            has_jsonld=has_jsonld,
            has_next_data=has_next_data,
            has_initial_state=has_initial_state,
            detected_features=["html_structure"],
        )

    @staticmethod
    def _detect_by_structured_data(html: str) -> EcommerceDetectionResult | None:
        for payload in _json_payloads(html):
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if _contains_product_shape(data):
                return EcommerceDetectionResult(
                    is_ecommerce=True,
                    confidence=0.75,
                    has_jsonld=True,
                    detected_features=["structured_product_data"],
                )
        return None

    @staticmethod
    def _detect_by_price_api(html: str, headers: dict[str, str]) -> EcommerceDetectionResult | None:
        lowered = html.lower()
        hits = sum(1 for word in ("price", "amount", "currency", "discount", "saleprice", "stock") if word in lowered)
        header_text = " ".join(f"{key}:{value}" for key, value in headers.items()).lower()
        if "json" in header_text and hits >= 2:
            hits += 1
        if hits >= 3:
            return EcommerceDetectionResult(
                is_ecommerce=True,
                confidence=0.50,
                price_api_detected=True,
                detected_features=["price_api"],
            )
        return None


def _json_payloads(html: str) -> list[str]:
    patterns = [
        r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        r'(?is)<script[^>]+type=["\']application/json["\'][^>]*>(.*?)</script>',
        r'(?is)__NEXT_DATA__\s*=\s*(\{.*?\})\s*;',
        r'(?is)__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;',
    ]
    payloads: list[str] = []
    for pattern in patterns:
        payloads.extend(match.group(1).strip() for match in re.finditer(pattern, html))
    return payloads


def _contains_product_shape(value: Any) -> bool:
    if isinstance(value, dict):
        node_type = str(value.get("@type", "")).lower()
        if node_type in {"product", "offer", "aggregateoffer", "itemlist"}:
            return True
        if sum(1 for key in ("sku", "price", "offers", "priceCurrency", "aggregateRating") if key in value) >= 2:
            return True
        return any(_contains_product_shape(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_product_shape(child) for child in value)
    return False


def detect_ecommerce_site(url: str, html: str = "", headers: dict[str, str] | None = None) -> EcommerceDetectionResult:
    return UniversalEcommerceDetector.detect(url, html, headers)
