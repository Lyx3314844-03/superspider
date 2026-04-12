# SuperSpider Install Matrix

SuperSpider 当前发布四个框架，每个框架都提供 Windows、Linux、macOS 三种操作系统安装版本。

## Install Philosophy

安装脚本不是“整仓库安装器”，而是按框架拆开的独立入口：

- 你只装需要的那个框架
- 你按目标操作系统选择脚本
- 安装结果直接对应到该框架的主要交付物

## Windows Install Versions

- `scripts/windows/install-pyspider.bat`
- `scripts/windows/install-gospider.bat`
- `scripts/windows/install-rustspider.bat`
- `scripts/windows/install-javaspider.bat`

## Linux Install Versions

- `scripts/linux/install-pyspider.sh`
- `scripts/linux/install-gospider.sh`
- `scripts/linux/install-rustspider.sh`
- `scripts/linux/install-javaspider.sh`

## macOS Install Versions

- `scripts/macos/install-pyspider.sh`
- `scripts/macos/install-gospider.sh`
- `scripts/macos/install-rustspider.sh`
- `scripts/macos/install-javaspider.sh`

## What Each Installer Produces

| Framework | Output |
| --- | --- |
| PySpider | `.venv-pyspider` 虚拟环境与可编辑安装 |
| GoSpider | `gospider` 可执行文件 |
| RustSpider | `rustspider/target/release/rustspider` 发布二进制 |
| JavaSpider | `javaspider/target` Maven 构建输出 |

## Typical Prerequisites

| Framework | Required tools |
| --- | --- |
| PySpider | Python 3、`venv`、`pip` |
| GoSpider | Go |
| RustSpider | Rust、Cargo |
| JavaSpider | Java 17+、Maven |

## Install Decision Guide

- 需要最快开始：先装 `PySpider`
- 需要部署到服务器或批处理节点：先装 `GoSpider`
- 需要发布高性能二进制：先装 `RustSpider`
- 需要接入 Java / Maven 工程环境：先装 `JavaSpider`
