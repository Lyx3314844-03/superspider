# SuperSpider Install Matrix

SuperSpider ships four runtimes, and every runtime has dedicated installers for Windows, Linux, and macOS.

## Install Packages By Framework

| Framework | Windows | Linux | macOS | Install output |
| --- | --- | --- | --- | --- |
| PySpider | `scripts/windows/install-pyspider.bat` | `scripts/linux/install-pyspider.sh` | `scripts/macos/install-pyspider.sh` | `.venv-pyspider` |
| GoSpider | `scripts/windows/install-gospider.bat` | `scripts/linux/install-gospider.sh` | `scripts/macos/install-gospider.sh` | `gospider` executable |
| RustSpider | `scripts/windows/install-rustspider.bat` | `scripts/linux/install-rustspider.sh` | `scripts/macos/install-rustspider.sh` | `rustspider/target/release/rustspider` |
| JavaSpider | `scripts/windows/install-javaspider.bat` | `scripts/linux/install-javaspider.sh` | `scripts/macos/install-javaspider.sh` | `javaspider/target` |

## Required Tools

| Framework | Typical prerequisites |
| --- | --- |
| PySpider | Python 3, `venv`, `pip` |
| GoSpider | Go |
| RustSpider | Rust, Cargo |
| JavaSpider | Java 17+, Maven |

## Installation Intent

### PySpider

- creates an isolated virtual environment
- installs Python dependencies
- completes an editable `pyspider` install

### GoSpider

- builds the Go binary
- outputs a directly runnable CLI executable

### RustSpider

- builds a Rust release binary
- outputs a production-oriented release artifact

### JavaSpider

- runs Maven packaging
- produces Java build output under `target`

## Recommended Choice

- choose `PySpider` for the fastest project start and AI-heavy workflows
- choose `GoSpider` for concurrent services and worker-style execution
- choose `RustSpider` for performance-sensitive typed deployments
- choose `JavaSpider` for Maven-centric enterprise Java integration
