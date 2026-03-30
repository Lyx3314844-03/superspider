# Omega-Spider Cluster - Python Master 调度器

该目录包含了分布式爬虫系统的中心化调度器实现。

## 主要组件

- `master.py`: 基于 Flask 的主服务，负责任务分发和状态跟踪。
- `schema.sql`: 数据库架构定义，使用 SQLite 存储任务。
- `verify_master.py`: 用于验证 API 功能的测试脚本。

## API 端点

- `GET /task/get`: 获取一个待处理任务并标记为 `running`。
- `POST /task/submit`: 提交任务执行结果及状态。
- `GET /stats`: 获取系统的总体任务进度统计。
- `POST /task/add`: 手动添加新任务。

## 使用方法

1. **启动 Master 服务**:
   ```bash
   python master.py
   ```

2. **运行验证测试**:
   ```bash
   python verify_master.py
   ```
