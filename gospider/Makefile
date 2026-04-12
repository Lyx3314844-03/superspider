# GoSpider Makefile

.PHONY: all build test clean run lint fmt vet docker docker-push help

# 变量
BINARY_NAME=gospider
VERSION?=1.0.0
GOOS?=$(shell go env GOOS)
GOARCH?=$(shell go env GOARCH)
BUILD_DIR=./build
CMD_DIR=./cmd/gospider
MAIN_FILE=$(CMD_DIR)/main.go

# 默认目标
all: lint test build

# 构建
build:
	@echo "构建 $(BINARY_NAME)..."
	@mkdir -p $(BUILD_DIR)
	go build -o $(BUILD_DIR)/$(BINARY_NAME) $(MAIN_FILE)
	@echo "构建完成：$(BUILD_DIR)/$(BINARY_NAME)"

# 跨平台构建
build-all:
	@echo "跨平台构建..."
	@mkdir -p $(BUILD_DIR)
	
	# Windows
	GOOS=windows GOARCH=amd64 go build -o $(BUILD_DIR)/$(BINARY_NAME)-windows-amd64.exe $(MAIN_FILE)
	
	# Linux
	GOOS=linux GOARCH=amd64 go build -o $(BUILD_DIR)/$(BINARY_NAME)-linux-amd64 $(MAIN_FILE)
	
	# macOS
	GOOS=darwin GOARCH=amd64 go build -o $(BUILD_DIR)/$(BINARY_NAME)-darwin-amd64 $(MAIN_FILE)
	
	@echo "跨平台构建完成"

# 测试
test:
	@echo "运行测试..."
	go test -v ./... -race -coverprofile=coverage.txt -covermode=atomic
	go tool cover -func=coverage.txt
	@echo "测试完成"

# 运行
run:
	go run $(MAIN_FILE) help

# 清理
clean:
	@echo "清理..."
	rm -rf $(BUILD_DIR)
	rm -f coverage.txt
	go clean -cache
	@echo "清理完成"

# 代码检查
lint:
	@echo "代码检查..."
	golangci-lint run ./... || true

# 格式化
fmt:
	@echo "格式化代码..."
	gofmt -s -w .
	go fmt ./...

# Vet 检查
vet:
	@echo "运行 vet..."
	go vet ./...

# 依赖管理
deps:
	@echo "更新依赖..."
	go mod tidy
	go mod download

# Docker 构建
docker:
	@echo "构建 Docker 镜像..."
	docker build -t gospider:$(VERSION) -f docker/Dockerfile .
	docker tag gospider:$(VERSION) gospider:latest

# Docker 推送
docker-push:
	@echo "推送 Docker 镜像..."
	docker push gospider:$(VERSION)
	docker push gospider:latest

# 安装
install:
	@echo "安装..."
	go install $(MAIN_FILE)

# 帮助
help:
	@echo "GoSpider 构建命令"
	@echo ""
	@echo "用法：make [目标]"
	@echo ""
	@echo "目标:"
	@echo "  all          - 默认目标 (lint + test + build)"
	@echo "  build        - 构建当前平台"
	@echo "  build-all    - 跨平台构建 (Windows/Linux/macOS)"
	@echo "  test         - 运行测试"
	@echo "  run          - 运行程序"
	@echo "  clean        - 清理构建产物"
	@echo "  lint         - 代码检查"
	@echo "  fmt          - 格式化代码"
	@echo "  vet          - Vet 检查"
	@echo "  deps         - 更新依赖"
	@echo "  docker       - 构建 Docker 镜像"
	@echo "  docker-push  - 推送 Docker 镜像"
	@echo "  install      - 安装到 GOPATH"
	@echo "  help         - 显示帮助信息"
