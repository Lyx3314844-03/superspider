# JavaSpider Dockerfile
FROM maven:3.9-eclipse-temurin-17 AS builder

WORKDIR /build

# 复制 pom.xml
COPY pom.xml .
RUN mvn dependency:go-offline

# 复制源代码
COPY src ./src

# 构建
RUN mvn clean package -DskipTests

# 最终镜像
FROM eclipse-temurin:17-jre-alpine

# 安装 FFmpeg
RUN apk add --no-cache ffmpeg

# 创建非 root 用户
RUN addgroup -g 1000 appgroup && \
    adduser -u 1000 -G appgroup -D appuser

# 复制构建产物
COPY --from=builder /build/target/*.jar /usr/local/lib/javaspider.jar

# 设置工作目录
WORKDIR /data

# 切换到非 root 用户
USER appuser

# 入口点
ENTRYPOINT ["java", "-jar", "/usr/local/lib/javaspider.jar"]

# 默认命令
CMD ["--help"]
