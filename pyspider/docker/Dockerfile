# PySpider Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY . .

# 安装包
RUN pip install -e .

# 安装 Playwright 浏览器
RUN playwright install chromium
RUN playwright install-deps chromium

# 创建非 root 用户
RUN useradd -m -u 1000 appuser

# 切换用户
USER appuser

# 设置工作目录
WORKDIR /data

# 入口点
ENTRYPOINT ["pyspider"]

# 默认命令
CMD ["--help"]
