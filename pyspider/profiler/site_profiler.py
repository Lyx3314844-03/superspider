from dataclasses import dataclass, field
from typing import Dict, List
from urllib.parse import urlparse


@dataclass
class SiteProfile:
    url: str
    page_type: str
    signals: Dict[str, bool] = field(default_factory=dict)
    candidate_fields: List[str] = field(default_factory=list)
    risk_level: str = "low"


class SiteProfiler:
    def profile(self, url: str, content: str) -> SiteProfile:
        lower = content.lower()
        signals = {
            "has_form": "<form" in lower,
            "has_pagination": "next" in lower or "page=" in lower,
            "has_list": "<li" in lower or "<ul" in lower,
            "has_detail": "<article" in lower or "<h1" in lower,
            "has_captcha": "captcha" in lower or "verify" in lower,
        }

        if signals["has_list"] and not signals["has_detail"]:
            page_type = "list"
        elif signals["has_detail"]:
            page_type = "detail"
        else:
            page_type = "generic"

        candidate_fields: List[str] = []
        if "<title" in lower:
            candidate_fields.append("title")
        if "price" in lower:
            candidate_fields.append("price")
        if "author" in lower:
            candidate_fields.append("author")

        risk_level = (
            "high"
            if signals["has_captcha"]
            else (
                "medium"
                if urlparse(url).scheme == "https" and signals["has_form"]
                else "low"
            )
        )
        return SiteProfile(
            url=url,
            page_type=page_type,
            signals=signals,
            candidate_fields=candidate_fields,
            risk_level=risk_level,
        )
