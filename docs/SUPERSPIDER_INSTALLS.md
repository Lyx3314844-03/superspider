# SuperSpider Install Matrix

This document defines the three-system install surface for the four primary
frameworks in the SuperSpider suite:

- `pyspider`
- `gospider`
- `rustspider`
- `javaspider`

The suite keeps the original all-in-one installers and now also exposes
single-framework installers for Windows, Linux, and macOS.

## Brand Asset

- multicolor wordmark: `docs/assets/superspider-wordmark.svg`
- icon badge: `docs/assets/superspider-icon.svg`

## Suite Installers

These install the full suite:

- Windows: `scripts/windows/install.bat`
- Linux: `scripts/linux/install.sh`
- macOS: `scripts/macos/install.sh`

## Single-Framework Installers

| Framework | Windows | Linux | macOS | Main output |
| --- | --- | --- | --- | --- |
| PySpider | `scripts/windows/install-pyspider.bat` | `scripts/linux/install-pyspider.sh` | `scripts/macos/install-pyspider.sh` | isolated virtual environment with editable install |
| GoSpider | `scripts/windows/install-gospider.bat` | `scripts/linux/install-gospider.sh` | `scripts/macos/install-gospider.sh` | compiled `gospider` binary |
| RustSpider | `scripts/windows/install-rustspider.bat` | `scripts/linux/install-rustspider.sh` | `scripts/macos/install-rustspider.sh` | release `rustspider` binary |
| JavaSpider | `scripts/windows/install-javaspider.bat` | `scripts/linux/install-javaspider.sh` | `scripts/macos/install-javaspider.sh` | Maven package and dependency-ready target directory |

## Prerequisite Matrix

| Framework | Required tools |
| --- | --- |
| PySpider | Python 3 + `venv` + `pip` |
| GoSpider | Go |
| RustSpider | Rust + Cargo |
| JavaSpider | Java 17+ + Maven |

## Post-Install Entry Commands

| Framework | Example command |
| --- | --- |
| PySpider | `.venv-pyspider` activated, then `python -m pyspider version` |
| GoSpider | `gospider\\gospider.exe version` on Windows, `./gospider/gospider version` on Linux/macOS |
| RustSpider | `rustspider\\target\\release\\rustspider.exe version` on Windows, `./rustspider/target/release/rustspider version` on Linux/macOS |
| JavaSpider | `mvn -f javaspider/pom.xml -q exec:java -Dexec.mainClass=com.javaspider.EnhancedSpider -Dexec.args="version"` |

## Install Intent Per Runtime

- PySpider:
  - creates `.venv-pyspider`
  - upgrades `pip`
  - installs `pyspider/requirements.txt`
  - installs `pyspider` in editable mode
- GoSpider:
  - builds the CLI binary from `./cmd/gospider`
  - leaves the output binary inside `gospider/`
- RustSpider:
  - builds the release binary with Cargo
  - leaves the output binary inside `rustspider/target/release/`
- JavaSpider:
  - packages the Maven project
  - copies dependency jars into `javaspider/target/dependency/`

## Recommended Install Choice

- Choose PySpider when you want the richest project authoring and AI workflow surface.
- Choose GoSpider when you want a simple binary deployment with strong concurrency.
- Choose RustSpider when you want a strongly typed release binary with feature gates.
- Choose JavaSpider when you want Maven-native packaging and enterprise integration.
