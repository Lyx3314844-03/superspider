"""
数据转换模块
支持多种数据清洗和转换规则
"""

import re
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime


class DataTransformer:
    """数据转换器"""
    
    def __init__(self):
        self._rules: List[Dict[str, Any]] = []
    
    def add_trim_rule(self, *fields: str) -> 'DataTransformer':
        """添加去除空白规则"""
        for field in fields:
            self._rules.append({
                "field": field,
                "type": "trim",
                "apply": lambda v: v.strip() if isinstance(v, str) else v,
            })
        return self
    
    def add_replace_rule(self, field: str, from_str: str, to_str: str) -> 'DataTransformer':
        """添加替换规则"""
        self._rules.append({
            "field": field,
            "type": "replace",
            "apply": lambda v: v.replace(from_str, to_str) if isinstance(v, str) else v,
        })
        return self
    
    def add_regex_rule(self, field: str, pattern: str) -> 'DataTransformer':
        """添加正则提取规则"""
        def apply_regex(v: Any) -> Any:
            if isinstance(v, str):
                match = re.search(pattern, v)
                return match.group(1) if match and match.groups() else v
            return v
        
        self._rules.append({
            "field": field,
            "type": "regex",
            "apply": apply_regex,
        })
        return self
    
    def add_upper_case_rule(self, field: str) -> 'DataTransformer':
        """添加大写规则"""
        self._rules.append({
            "field": field,
            "type": "upper",
            "apply": lambda v: v.upper() if isinstance(v, str) else v,
        })
        return self
    
    def add_lower_case_rule(self, field: str) -> 'DataTransformer':
        """添加小写规则"""
        self._rules.append({
            "field": field,
            "type": "lower",
            "apply": lambda v: v.lower() if isinstance(v, str) else v,
        })
        return self
    
    def add_date_format_rule(self, field: str, output_format: str) -> 'DataTransformer':
        """添加日期格式化规则"""
        def apply_date_format(v: Any) -> Any:
            if isinstance(v, str):
                formats = [
                    "%Y-%m-%d",
                    "%Y/%m/%d",
                    "%m/%d/%Y",
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S",
                ]
                for fmt in formats:
                    try:
                        dt = datetime.strptime(v, fmt)
                        return dt.strftime(output_format)
                    except ValueError:
                        continue
            return v
        
        self._rules.append({
            "field": field,
            "type": "date_format",
            "apply": apply_date_format,
        })
        return self
    
    def add_null_rule(self, field: str, default_value: Any) -> 'DataTransformer':
        """添加空值处理规则"""
        self._rules.append({
            "field": field,
            "type": "null",
            "apply": lambda v: default_value if v is None or v == "" else v,
        })
        return self
    
    def add_html_clean_rule(self, *fields: str) -> 'DataTransformer':
        """添加 HTML 清理规则"""
        def clean_html(v: Any) -> Any:
            if isinstance(v, str):
                return re.sub(r'<[^>]*>', '', v)
            return v
        
        for field in fields:
            self._rules.append({
                "field": field,
                "type": "html_clean",
                "apply": clean_html,
            })
        return self
    
    def add_custom_rule(self, field: str, func: Callable[[Any], Any]) -> 'DataTransformer':
        """添加自定义规则"""
        self._rules.append({
            "field": field,
            "type": "custom",
            "apply": func,
        })
        return self
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """转换数据"""
        result = dict(data)
        
        for rule in self._rules:
            field = rule["field"]
            if field in result:
                result[field] = rule["apply"](result[field])
        
        return result
    
    def clear_rules(self) -> None:
        """清空规则"""
        self._rules.clear()


class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def is_email(value: str) -> bool:
        """验证邮箱"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, value))
    
    @staticmethod
    def is_phone_cn(value: str) -> bool:
        """验证中国手机号"""
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, value))
    
    @staticmethod
    def is_url(value: str) -> bool:
        """验证 URL"""
        pattern = r'^https?://.+'
        return bool(re.match(pattern, value))
    
    @staticmethod
    def is_number(value: Any) -> bool:
        """验证数字"""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_date(value: str, format: Optional[str] = None) -> bool:
        """验证日期"""
        formats = [format] if format else [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%m/%d/%Y",
            "%Y-%m-%d %H:%M:%S",
        ]
        for fmt in formats:
            try:
                datetime.strptime(value, fmt)
                return True
            except ValueError:
                continue
        return False
