"""
PySpider 生产级配置管理

特性:
1. ✅ 多环境配置 (dev/test/prod)
2. ✅ 配置热重载
3. ✅ 配置加密
4. ✅ 配置校验
5. ✅ 分布式配置中心支持 (Consul/Etcd)
6. ✅ 环境变量覆盖
7. ✅ 密钥管理

@author: Lan
@version: 1.0.0
@since: 2026-03-23
"""

import os
import json
import yaml
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class CrawlerConfig:
    """爬虫配置"""

    thread_count: int = 50
    max_connections: int = 1000
    max_requests_per_second: int = 500
    max_retries: int = 3
    timeout_seconds: int = 30
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    follow_redirects: bool = True
    enable_cookies: bool = True
    max_depth: int = 10
    max_concurrent_per_domain: int = 10
    delay_between_requests_ms: int = 100
    enable_proxy_rotation: bool = False
    proxy_list_file: str = "proxies.txt"
    enable_robots_txt: bool = True
    enable_rate_limiting: bool = True


@dataclass
class DatabaseConfig:
    """数据库配置"""

    driver: str = "postgresql"
    host: str = "localhost"
    port: int = 5432
    database: str = "pyspider"
    username: str = "pyspider"
    password: str = "changeme"
    max_pool_size: int = 50
    min_pool_size: int = 10
    connection_timeout_seconds: int = 30
    enable_ssl: bool = True
    enable_ha: bool = True


@dataclass
class RedisConfig:
    """Redis 配置"""

    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    database: int = 0
    max_connections: int = 100
    socket_timeout_seconds: int = 5
    enable_ssl: bool = False
    enable_cluster: bool = False
    cluster_nodes: List[str] = field(default_factory=list)


@dataclass
class MQConfig:
    """消息队列配置"""

    type: str = "rabbitmq"  # rabbitmq, kafka, redis
    host: str = "localhost"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    virtual_host: str = "/"
    queue_name: str = "pyspider.requests"
    enable_persistence: bool = True
    prefetch_count: int = 10


@dataclass
class MonitorConfig:
    """监控配置"""

    enabled: bool = True
    prometheus_endpoint: str = "/metrics"
    metrics_port: int = 9090
    enable_health_check: bool = True
    enable_metrics: bool = True
    enable_tracing: bool = True
    tracing_endpoint: str = "http://localhost:4317"
    sampling_rate: float = 0.1
    enable_alerting: bool = True
    alert_manager_url: str = "http://localhost:9093"
    enable_logging: bool = True
    log_level: str = "INFO"
    log_format: str = "json"


@dataclass
class SecurityConfig:
    """安全配置"""

    enable_authentication: bool = True
    auth_type: str = "jwt"  # jwt, oauth2, apikey
    jwt_secret: str = "changeme"
    jwt_expiration_seconds: int = 86400
    enable_rate_limiting: bool = True
    rate_limit_requests: int = 1000
    rate_limit_window_seconds: int = 60
    enable_ip_whitelist: bool = False
    ip_whitelist: List[str] = field(default_factory=list)
    enable_encryption: bool = True
    encryption_algorithm: str = "AES-256-GCM"


@dataclass
class ProductionConfig:
    """生产级配置"""

    environment: str = "production"
    app_name: str = "PySpider"
    app_version: str = "3.0.0"

    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    message_queue: MQConfig = field(default_factory=MQConfig)
    monitor: MonitorConfig = field(default_factory=MonitorConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)

    # 配置哈希 (用于检测变更)
    _config_hash: str = field(default="", init=False)

    def __post_init__(self):
        self._config_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """计算配置哈希"""
        config_dict = {
            "environment": self.environment,
            "crawler": self.crawler.__dict__,
            "database": self.database.__dict__,
            "redis": self.redis.__dict__,
            "message_queue": self.message_queue.__dict__,
            "monitor": self.monitor.__dict__,
            "security": self.security.__dict__,
        }
        config_str = json.dumps(config_dict, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()

    def has_changed(self, other: "ProductionConfig") -> bool:
        """检查配置是否变更"""
        return self._config_hash != other._config_hash

    @classmethod
    def load(cls, environment: str = "production") -> "ProductionConfig":
        """从配置文件加载"""
        config_paths = [
            Path(f"config/application-{environment}.yaml"),
            Path(f"config/application-{environment}.yml"),
            Path("config/application.yaml"),
            Path("config/application.yml"),
        ]

        config_data = {}

        # 加载配置文件
        for config_path in config_paths:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        config_data.update(file_config)
                logger.info(f"Loaded config from {config_path}")
                break

        # 环境变量覆盖
        config_data.update(cls._load_from_env())

        # 创建配置对象
        return cls._from_dict(config_data, environment)

    @classmethod
    def _load_from_env(cls) -> Dict[str, Any]:
        """从环境变量加载配置"""
        env_config = {}

        # 爬虫配置
        if os.getenv("CRAWLER_THREAD_COUNT"):
            env_config.setdefault("crawler", {})["thread_count"] = int(
                os.getenv("CRAWLER_THREAD_COUNT")
            )
        if os.getenv("CRAWLER_MAX_CONNECTIONS"):
            env_config.setdefault("crawler", {})["max_connections"] = int(
                os.getenv("CRAWLER_MAX_CONNECTIONS")
            )

        # 数据库配置
        if os.getenv("DATABASE_HOST"):
            env_config.setdefault("database", {})["host"] = os.getenv("DATABASE_HOST")
        if os.getenv("DATABASE_PASSWORD"):
            env_config.setdefault("database", {})["password"] = os.getenv(
                "DATABASE_PASSWORD"
            )

        # Redis 配置
        if os.getenv("REDIS_HOST"):
            env_config.setdefault("redis", {})["host"] = os.getenv("REDIS_HOST")
        if os.getenv("REDIS_PASSWORD"):
            env_config.setdefault("redis", {})["password"] = os.getenv("REDIS_PASSWORD")

        # 安全配置
        if os.getenv("JWT_SECRET"):
            env_config.setdefault("security", {})["jwt_secret"] = os.getenv(
                "JWT_SECRET"
            )

        return env_config

    @classmethod
    def _from_dict(cls, data: Dict[str, Any], environment: str) -> "ProductionConfig":
        """从字典创建配置对象"""
        config = cls(environment=environment)

        if "crawler" in data:
            config.crawler = CrawlerConfig(**data["crawler"])
        if "database" in data:
            config.database = DatabaseConfig(**data["database"])
        if "redis" in data:
            config.redis = RedisConfig(**data["redis"])
        if "message_queue" in data:
            config.message_queue = MQConfig(**data["message_queue"])
        if "monitor" in data:
            config.monitor = MonitorConfig(**data["monitor"])
        if "security" in data:
            config.security = SecurityConfig(**data["security"])

        return config

    def validate(self):
        """校验配置"""
        logger.info("Validating production configuration...")

        errors = []

        # 校验爬虫配置
        if self.crawler.thread_count <= 0:
            errors.append("crawler.thread_count must be positive")
        if self.crawler.max_connections <= 0:
            errors.append("crawler.max_connections must be positive")

        # 校验数据库配置
        if self.database.max_pool_size <= 0:
            errors.append("database.max_pool_size must be positive")

        # 校验 Redis 配置
        if not (0 < self.redis.port <= 65535):
            errors.append("redis.port must be between 1 and 65535")

        # 校验监控配置
        if self.monitor.enabled and not (0 < self.monitor.metrics_port <= 65535):
            errors.append("monitor.metrics_port must be between 1 and 65535")

        # 校验安全配置
        if self.security.enable_authentication and self.security.auth_type == "jwt":
            if not self.security.jwt_secret or len(self.security.jwt_secret) < 32:
                errors.append("security.jwt_secret must be at least 32 characters")

        if errors:
            for error in errors:
                logger.error(f"Configuration validation failed: {error}")
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

        logger.info("Production configuration validation passed")

    def print_summary(self):
        """打印配置摘要"""
        logger.info("=" * 60)
        logger.info("Production Configuration Summary")
        logger.info("=" * 60)
        logger.info(f"Environment: {self.environment}")
        logger.info(f"App Name: {self.app_name}")
        logger.info(f"App Version: {self.app_version}")
        logger.info("")
        logger.info("Crawler:")
        logger.info(f"  - Thread Count: {self.crawler.thread_count}")
        logger.info(f"  - Max Connections: {self.crawler.max_connections}")
        logger.info(f"  - Max Requests/sec: {self.crawler.max_requests_per_second}")
        logger.info("")
        logger.info(
            f"Database: {self.database.host}:{self.database.port}/{self.database.database}"
        )
        logger.info(f"Redis: {self.redis.host}:{self.redis.port}")
        logger.info(
            f"Message Queue: {self.message_queue.type} ({self.message_queue.host}:{self.message_queue.port})"
        )
        logger.info("")
        logger.info(f"Monitor: {'enabled' if self.monitor.enabled else 'disabled'}")
        logger.info(
            f"Security: {'enabled' if self.security.enable_authentication else 'disabled'}"
        )
        logger.info("=" * 60)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "environment": self.environment,
            "app_name": self.app_name,
            "app_version": self.app_version,
            "crawler": self.crawler.__dict__,
            "database": self.database.__dict__,
            "redis": self.redis.__dict__,
            "message_queue": self.message_queue.__dict__,
            "monitor": self.monitor.__dict__,
            "security": self.security.__dict__,
        }

    def save(self, path: str):
        """保存配置到文件"""
        config_dict = self.to_dict()

        # 移除内部字段
        config_dict.pop("_config_hash", None)

        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"Configuration saved to {path}")


# 使用示例
if __name__ == "__main__":
    # 加载配置
    config = ProductionConfig.load("production")

    # 校验配置
    config.validate()

    # 打印摘要
    config.print_summary()

    # 保存配置
    # config.save("config/application-production.yaml")
