# 🕷️ 四爬虫框架配置验证器

检查配置并验证所有必需的环境变量和依赖。

## 使用方法

```bash
# GoSpider
node spider/gospider/validate-config.js

# RustSpider
node spider/rustspider/validate-config.js

# PySpider
python spider/pyspider/validate_config.py

# JavaSpider
node spider/javaspider/validate-config.js
```

## 验证项目

### 必需的环境变量

- `REDIS_URL` - Redis 连接 URL（分布式功能需要）
- `LOG_LEVEL` - 日志级别（info/warn/error/debug）
- `OUTPUT_DIR` - 输出目录

### 必需的依赖

#### GoSpider
- puppeteer
- playwright
- express
- ioredis
- cheerio
- ws
- xpath
- xmldom

#### RustSpider
- express
- ioredis
- ws
- cheerio
- yt-dlp (Python 包)

#### PySpider
- flask
- redis
- requests
- beautifulsoup4
- you-get

#### JavaSpider
- express
- cheerio
- Java 运行时

## 自动修复

运行验证脚本会自动检测问题并提供修复建议。
