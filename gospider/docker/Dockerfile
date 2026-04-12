# GoSpider Dockerfile
FROM golang:1.22-alpine AS builder

# 安装依赖
RUN apk add --no-cache git

# 设置工作目录
WORKDIR /build

# 复制 go.mod 和 go.sum
COPY go.mod go.sum ./
RUN go mod download

# 复制源代码
COPY . .

# 构建
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o gospider ./cmd/gospider/main.go

# 最终镜像
FROM alpine:latest

# 安装必要的运行时依赖
RUN apk --no-cache add ca-certificates ffmpeg

# 创建非 root 用户
RUN addgroup -g 1000 appgroup && \
    adduser -u 1000 -G appgroup -D appuser

# 复制二进制文件
COPY --from=builder /build/gospider /usr/local/bin/gospider

# 设置工作目录
WORKDIR /data

# 切换到非 root 用户
USER appuser

# 暴露端口（如果需要 API 服务）
EXPOSE 8080

# 入口点
ENTRYPOINT ["gospider"]

# 默认命令
CMD ["help"]
