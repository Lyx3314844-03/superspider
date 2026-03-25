# PySpider Makefile

.PHONY: all install test lint format type-check clean docs docker help

# 变量
PYTHON?=python3
PIP?=pip
PACKAGE_NAME=pyspider
VERSION?=2.0.0

# 默认目标
all: lint type-check test

# 安装依赖
install:
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

# 安装开发依赖
install-dev:
	$(PIP) install -r requirements.txt
	$(PIP) install -e ".[dev]"

# 测试
test:
	$(PYTHON) -m pytest tests/ -v --cov=$(PACKAGE_NAME) --cov-report=html --cov-report=term-missing

# 运行单个测试
test-file:
	$(PYTHON) -m pytest $(file) -v

# 代码检查
lint:
	flake8 $(PACKAGE_NAME)/ tests/ --max-line-length=120 --ignore=E501,W503

# 格式化
format:
	black $(PACKAGE_NAME)/ tests/

# 类型检查
type-check:
	mypy $(PACKAGE_NAME)/ --ignore-missing-imports

# 清理
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# 构建
build:
	$(PYTHON) setup.py sdist bdist_wheel

# 发布
publish: clean build
	twine upload dist/*

# Docker 构建
docker:
	docker build -t $(PACKAGE_NAME):$(VERSION) -f docker/Dockerfile .
	docker tag $(PACKAGE_NAME):$(VERSION) $(PACKAGE_NAME):latest

# Docker 推送
docker-push:
	docker push $(PACKAGE_NAME):$(VERSION)
	docker push $(PACKAGE_NAME):latest

# 文档
docs:
	mkdocs build

# 文档服务
docs-serve:
	mkdocs serve

# 帮助
help:
	@echo "PySpider 构建命令"
	@echo ""
	@echo "用法：make [目标]"
	@echo ""
	@echo "目标:"
	@echo "  all          - 默认目标 (lint + type-check + test)"
	@echo "  install      - 安装依赖"
	@echo "  install-dev  - 安装开发依赖"
	@echo "  test         - 运行测试"
	@echo "  lint         - 代码检查"
	@echo "  format       - 格式化代码"
	@echo "  type-check   - 类型检查"
	@echo "  clean        - 清理"
	@echo "  build        - 构建包"
	@echo "  publish      - 发布到 PyPI"
	@echo "  docker       - 构建 Docker 镜像"
	@echo "  docker-push  - 推送 Docker 镜像"
	@echo "  docs         - 构建文档"
	@echo "  docs-serve   - 运行文档服务器"
	@echo "  help         - 显示帮助信息"
