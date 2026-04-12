"""
配置管理模块
支持 YAML 配置文件、环境变量、默认值
"""

import os
import yaml
import threading
from typing import Optional, Any, List
from dataclasses import dataclass, field, asdict


@dataclass
class SpiderConfig:
    """爬虫配置"""

    name: str = "Spider"
    max_requests: int = 10000
    max_depth: int = 5
    retry_times: int = 3
    request_timeout: int = 30
    rate_limit: float = 5.0  # 每秒请求数
    thread_count: int = 5
    enable_persistence: bool = True
    persistence_path: str = "artifacts/checkpoints/queue.db"
    log_level: str = "INFO"
    log_file: str = "artifacts/logs/spider.log"
    log_max_size: str = "10MB"

    @classmethod
    def from_dict(cls, data: dict) -> "SpiderConfig":
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class DownloaderConfig:
    """下载器配置"""

    timeout: int = 30
    retry_times: int = 3
    pool_connections: int = 10
    pool_maxsize: int = 50
    rate_limit: float = 5.0
    use_proxy: bool = False
    proxy_file: str = "proxies.txt"
    use_cookie: bool = True
    cookie_file: str = "cookies.pkl"
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    verify_ssl: bool = True
    follow_redirects: bool = True
    max_redirects: int = 10

    @classmethod
    def from_dict(cls, data: dict) -> "DownloaderConfig":
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AntiBotConfig:
    """反反爬配置"""

    enable_tls_spoof: bool = True
    enable_browser_spoof: bool = True
    enable_captcha_solver: bool = False
    captcha_api_key: Optional[str] = None
    captcha_service: str = "2captcha"
    stealth_mode: bool = True
    random_user_agent: bool = True
    random_referer: bool = True
    random_delay: bool = True
    min_delay: float = 1.0
    max_delay: float = 5.0
    night_mode: bool = True  # 夜间增加延迟
    night_start_hour: int = 23
    night_end_hour: int = 6

    @classmethod
    def from_dict(cls, data: dict) -> "AntiBotConfig":
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ProxyConfig:
    """代理配置"""

    enabled: bool = False
    proxy_file: str = "artifacts/proxies.txt"
    validate_interval: int = 300  # 秒
    validate_timeout: int = 10
    validate_url: str = "https://www.google.com"
    min_success_rate: float = 0.8
    max_failures: int = 10
    auto_switch: bool = True
    proxy_sources: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "ProxyConfig":
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class MediaConfig:
    """媒体下载配置"""

    output_dir: str = "artifacts/exports"
    max_file_size: int = 2 * 1024 * 1024 * 1024  # 2GB
    chunk_size: int = 8192
    max_workers: int = 5
    enable_resume: bool = True
    enable_hls: bool = True
    ffmpeg_path: Optional[str] = None
    download_images: bool = True
    download_videos: bool = True
    download_audios: bool = True
    download_subtitles: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "MediaConfig":
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CompleteConfig:
    """完整配置"""

    spider: SpiderConfig = field(default_factory=SpiderConfig)
    downloader: DownloaderConfig = field(default_factory=DownloaderConfig)
    antibot: AntiBotConfig = field(default_factory=AntiBotConfig)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    media: MediaConfig = field(default_factory=MediaConfig)

    @classmethod
    def from_dict(cls, data: dict) -> "CompleteConfig":
        """从字典创建"""
        config = cls()

        if "spider" in data:
            config.spider = SpiderConfig.from_dict(data["spider"])
        if "downloader" in data:
            config.downloader = DownloaderConfig.from_dict(data["downloader"])
        if "antibot" in data:
            config.antibot = AntiBotConfig.from_dict(data["antibot"])
        if "proxy" in data:
            config.proxy = ProxyConfig.from_dict(data["proxy"])
        if "media" in data:
            config.media = MediaConfig.from_dict(data["media"])

        return config

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "spider": asdict(self.spider),
            "downloader": asdict(self.downloader),
            "antibot": asdict(self.antibot),
            "proxy": asdict(self.proxy),
            "media": asdict(self.media),
        }

    def save(self, path: str):
        """保存到文件"""
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True)


class ConfigLoader:
    """配置加载器"""

    DEFAULT_CONFIG_FILE = "spider-framework.yaml"

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self.DEFAULT_CONFIG_FILE
        self._config = CompleteConfig()
        self._lock = threading.RLock()
        self._load()
        self._apply_environment_variables()

    def _load(self):
        """加载配置文件"""
        with self._lock:
            candidates = [self.config_file]
            if self.config_file == self.DEFAULT_CONFIG_FILE:
                candidates.extend(
                    ["spider-framework.yml", "spider-framework.json", "config.yaml"]
                )

            for candidate in candidates:
                if os.path.exists(candidate):
                    try:
                        with open(candidate, "r", encoding="utf-8") as f:
                            if candidate.endswith(".json"):
                                import json

                                data = json.load(f)
                            else:
                                data = yaml.safe_load(f)
                            if data:
                                self._config = CompleteConfig.from_dict(data)
                                self.config_file = candidate
                                break
                    except Exception as e:
                        print(f"加载配置文件失败：{e}，使用默认配置")

    def _apply_environment_variables(self):
        """应用环境变量"""
        # Spider 配置
        if os.getenv("SPIDER_NAME"):
            self._config.spider.name = os.getenv("SPIDER_NAME")
        if os.getenv("SPIDER_MAX_REQUESTS"):
            self._config.spider.max_requests = int(os.getenv("SPIDER_MAX_REQUESTS"))
        if os.getenv("SPIDER_THREAD_COUNT"):
            self._config.spider.thread_count = int(os.getenv("SPIDER_THREAD_COUNT"))

        # Downloader 配置
        if os.getenv("DOWNLOADER_TIMEOUT"):
            self._config.downloader.timeout = int(os.getenv("DOWNLOADER_TIMEOUT"))
        if os.getenv("DOWNLOADER_RATE_LIMIT"):
            self._config.downloader.rate_limit = float(
                os.getenv("DOWNLOADER_RATE_LIMIT")
            )

        # Proxy 配置
        if os.getenv("PROXY_ENABLED"):
            self._config.proxy.enabled = os.getenv("PROXY_ENABLED").lower() == "true"
        if os.getenv("PROXY_FILE"):
            self._config.proxy.proxy_file = os.getenv("PROXY_FILE")

    @property
    def spider(self) -> SpiderConfig:
        """获取爬虫配置"""
        return self._config.spider

    @property
    def downloader(self) -> DownloaderConfig:
        """获取下载器配置"""
        return self._config.downloader

    @property
    def antibot(self) -> AntiBotConfig:
        """获取反反爬配置"""
        return self._config.antibot

    @property
    def proxy(self) -> ProxyConfig:
        """获取代理配置"""
        return self._config.proxy

    @property
    def media(self) -> MediaConfig:
        """获取媒体配置"""
        return self._config.media

    @property
    def config(self) -> CompleteConfig:
        """获取完整配置"""
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点分隔路径）

        Args:
            key: 配置键（如 "spider.name"）
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split(".")
        value = self._config.to_dict()

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        设置配置值

        Args:
            key: 配置键（如 "spider.name"）
            value: 配置值
        """
        keys = key.split(".")
        config_dict = self._config.to_dict()

        current = config_dict
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value
        self._config = CompleteConfig.from_dict(config_dict)

    def save(self, path: Optional[str] = None):
        """保存配置到文件"""
        path = path or self.config_file
        self._config.save(path)

    def reload(self):
        """重新加载配置"""
        self._load()

    def validate(self) -> List[str]:
        """
        验证配置

        Returns:
            错误列表
        """
        errors = []

        # 验证爬虫配置
        if self._config.spider.max_requests <= 0:
            errors.append("spider.max_requests 必须大于 0")
        if self._config.spider.thread_count <= 0:
            errors.append("spider.thread_count 必须大于 0")
        if self._config.spider.rate_limit <= 0:
            errors.append("spider.rate_limit 必须大于 0")

        # 验证下载器配置
        if self._config.downloader.timeout <= 0:
            errors.append("downloader.timeout 必须大于 0")
        if self._config.downloader.pool_connections <= 0:
            errors.append("downloader.pool_connections 必须大于 0")

        # 验证代理配置
        if self._config.proxy.enabled and not os.path.exists(
            self._config.proxy.proxy_file
        ):
            errors.append(f"代理文件不存在：{self._config.proxy.proxy_file}")

        return errors

    def __repr__(self) -> str:
        return f"ConfigLoader(config_file={self.config_file})"


# 默认配置文件模板
DEFAULT_CONFIG_TEMPLATE = """# pyspider 配置文件
# 生成时间：{timestamp}

# 爬虫配置
spider:
  name: "MySpider"
  max_requests: 10000
  max_depth: 5
  retry_times: 3
  request_timeout: 30
  rate_limit: 5.0
  thread_count: 5
  enable_persistence: true
  persistence_path: "data/queue.db"
  log_level: "INFO"
  log_file: "logs/spider.log"
  log_max_size: "10MB"

# 下载器配置
downloader:
  timeout: 30
  retry_times: 3
  pool_connections: 10
  pool_maxsize: 50
  rate_limit: 5.0
  use_proxy: false
  proxy_file: "proxies.txt"
  use_cookie: true
  cookie_file: "cookies.pkl"
  user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
  verify_ssl: true
  follow_redirects: true
  max_redirects: 10

# 反反爬配置
antibot:
  enable_tls_spoof: true
  enable_browser_spoof: true
  enable_captcha_solver: false
  captcha_api_key: null
  captcha_service: "2captcha"
  stealth_mode: true
  random_user_agent: true
  random_referer: true
  random_delay: true
  min_delay: 1.0
  max_delay: 5.0
  night_mode: true
  night_start_hour: 23
  night_end_hour: 6

# 代理配置
proxy:
  enabled: false
  proxy_file: "proxies.txt"
  validate_interval: 300
  validate_timeout: 10
  validate_url: "https://www.google.com"
  min_success_rate: 0.8
  max_failures: 10
  auto_switch: true
  proxy_sources: []

# 媒体下载配置
media:
  output_dir: "downloads"
  max_file_size: 2147483648
  chunk_size: 8192
  max_workers: 5
  enable_resume: true
  enable_hls: true
  ffmpeg_path: null
  download_images: true
  download_videos: true
  download_audios: true
  download_subtitles: true
"""


def create_default_config(path: Optional[str] = None):
    """创建默认配置文件"""
    path = path or ConfigLoader.DEFAULT_CONFIG_FILE

    from datetime import datetime

    content = DEFAULT_CONFIG_TEMPLATE.format(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"已创建默认配置文件：{path}")


# 使用示例
if __name__ == "__main__":
    # 创建默认配置文件
    if not os.path.exists("config.yaml"):
        create_default_config()

    # 加载配置
    loader = ConfigLoader("config.yaml")

    # 获取配置值
    print(f"爬虫名称：{loader.spider.name}")
    print(f"最大请求数：{loader.spider.max_requests}")
    print(f"线程数：{loader.spider.thread_count}")
    print(f"下载器超时：{loader.downloader.timeout}")
    print(f"代理启用：{loader.proxy.enabled}")

    # 使用点路径获取
    print(f"媒体输出目录：{loader.get('media.output_dir')}")

    # 验证配置
    errors = loader.validate()
    if errors:
        print("配置验证失败:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("配置验证通过")

    # 保存配置
    # loader.save("config_backup.yaml")
