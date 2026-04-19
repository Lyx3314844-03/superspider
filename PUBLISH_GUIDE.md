# SuperSpider Publishing Guide

This guide covers how to publish SuperSpider to GitHub from Windows, Linux, or macOS.

## Prerequisites

| Tool | Required for |
| --- | --- |
| Git | all runtimes |
| Python 3.8+ | PySpider |
| Go 1.20+ | GoSpider |
| Rust 1.70+ + Cargo | RustSpider |
| Java 17+ + Maven | JavaSpider |

## Quick Start: Manual Publish

```bash
# 1. Initialize git (if not already done)
git init

# 2. Stage all files
git add .

# 3. Commit
git commit -m "Initial release: SuperSpider v1.0.0"

# 4. Add remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/superspider.git

# 5. Push
git branch -M main
git push -u origin main
```

## Install Scripts

Every runtime has dedicated install scripts for all three operating systems.

### Windows

```bat
scripts\windows\install-pyspider.bat
scripts\windows\install-gospider.bat
scripts\windows\install-rustspider.bat
scripts\windows\install-javaspider.bat
```

### Linux

```bash
bash scripts/linux/install-pyspider.sh
bash scripts/linux/install-gospider.sh
bash scripts/linux/install-rustspider.sh
bash scripts/linux/install-javaspider.sh
```

### macOS

```bash
bash scripts/macos/install-pyspider.sh
bash scripts/macos/install-gospider.sh
bash scripts/macos/install-rustspider.sh
bash scripts/macos/install-javaspider.sh
```

## Install Outputs

| Framework | Output |
| --- | --- |
| PySpider | `.venv-pyspider` virtual environment |
| GoSpider | `gospider` executable |
| RustSpider | `rustspider/target/release/rustspider` |
| JavaSpider | `javaspider/target` Maven artifacts |

## Verifying Installs

### PySpider

```bash
source .venv-pyspider/bin/activate   # Linux / macOS
.venv-pyspider\Scripts\activate      # Windows
python -m pyspider version
```

### GoSpider

```bash
./gospider --version
```

### RustSpider

```bash
./rustspider/target/release/rustspider --version
```

### JavaSpider

```bash
java -jar javaspider/target/javaspider-*.jar --version
```

## Creating a GitHub Release

After pushing to GitHub:

1. Go to your repository on GitHub.
2. Click **Releases** → **Draft a new release**.
3. Set the tag to `v1.0.0`.
4. Use `docs/GITHUB_RELEASE_TEMPLATE.md` as the release body template.
5. Attach any compiled binaries as release assets if desired.
6. Publish the release.

## Recommended Repository Topics

Add these topics to your GitHub repository for discoverability:

```
python rust golang java crawler spider web-scraping anti-bot playwright
```

## Troubleshooting

### Git push rejected

```bash
# Use HTTPS with a personal access token
git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/superspider.git
```

### SSH key not configured

```bash
ssh-keygen -t ed25519 -C "your@email.com"
# Add the public key at: https://github.com/settings/keys
```

### Python venv creation fails

```bash
python -m pip install --upgrade pip
python -m venv .venv-pyspider
```

### Rust build fails

```bash
rustup update stable
cargo clean
cargo build --release
```

### Go build fails

```bash
go clean -cache
go build ./...
```

### Maven build fails

```bash
mvn clean install -DskipTests
```

## Related Docs

- `README.md` — project overview
- `CHANGELOG.md` — version history
- `CONTRIBUTING.md` — contribution guide
- `docs/DOCS_INDEX.md` — full documentation index
- `docs/RELEASE_NOTES_v1.0.0.md` — v1.0.0 release notes
- `docs/GITHUB_RELEASE_TEMPLATE.md` — GitHub release body template
