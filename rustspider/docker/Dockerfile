# RustSpider Dockerfile
FROM rust:1.75 AS builder

WORKDIR /build

# 复制 Cargo 配置
COPY Cargo.toml .
COPY src ./src

# 构建
RUN cargo build --release

# 最终镜像
FROM debian:bookworm-slim

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    ca-certificates \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN useradd -m -u 1000 appuser

# 复制二进制文件
COPY --from=builder /build/target/release/rustspider /usr/local/bin/rustspider

# 设置工作目录
WORKDIR /data

# 切换用户
USER appuser

# 入口点
ENTRYPOINT ["rustspider"]

# 默认命令
CMD ["--help"]
