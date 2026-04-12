# SuperSpider Install Matrix

这个仓库只保留四个框架的三系统安装路径。

## Windows

- `scripts/windows/install-pyspider.bat`
- `scripts/windows/install-gospider.bat`
- `scripts/windows/install-rustspider.bat`
- `scripts/windows/install-javaspider.bat`

## Linux

- `scripts/linux/install-pyspider.sh`
- `scripts/linux/install-gospider.sh`
- `scripts/linux/install-rustspider.sh`
- `scripts/linux/install-javaspider.sh`

## macOS

- `scripts/macos/install-pyspider.sh`
- `scripts/macos/install-gospider.sh`
- `scripts/macos/install-rustspider.sh`
- `scripts/macos/install-javaspider.sh`

## Outputs

- `PySpider`: 创建 `.venv-pyspider` 并完成可编辑安装
- `GoSpider`: 生成 `gospider` 可执行文件
- `RustSpider`: 生成 `rustspider/target/release/rustspider`
- `JavaSpider`: 生成 `javaspider/target` Maven 构建输出
