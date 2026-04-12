from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ResearchJob:
    seed_urls: List[str]
    site_profile: Dict[str, Any] = field(default_factory=dict)
    extract_schema: Dict[str, Any] = field(default_factory=dict)
    extract_specs: List[Dict[str, Any]] = field(default_factory=list)
    policy: Dict[str, Any] = field(default_factory=dict)
    output: Dict[str, Any] = field(default_factory=dict)
