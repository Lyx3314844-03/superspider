# Install

## Shared Expectations

- Every runtime supports `config init`, `crawl`, `browser fetch`, `doctor`, and `export`.
- Shared config file: `spider-framework.yaml`
- Shared operations docs:
  - `docs/OPERATIONS.md`
  - `docs/PUBLIC_BENCHMARKS.md`
  - `docs/SCALE_VALIDATION.md`
- Shared artifact directories:
  - `artifacts/checkpoints`
  - `artifacts/datasets`
  - `artifacts/exports`
  - `artifacts/browser`

## Operating System Installers

Use the suite-level installer and verify entrypoints when you want one command surface per operating system:

- Windows:
  - `scripts/windows/install.bat`
  - `scripts/windows/verify.bat`
- Linux:
  - `scripts/linux/install.sh`
  - `scripts/linux/verify.sh`
- macOS:
  - `scripts/macos/install.sh`
  - `scripts/macos/verify.sh`

These wrappers install or build all four runtimes and then run the shared OS support verification surface.

## Python

```bash
cd pyspider
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
pyspider config init
pyspider doctor
```

## Go

```bash
cd gospider
go test ./...
go build -o dist/gospider ./cmd/gospider
go run ./cmd/gospider config init
go run ./cmd/gospider doctor
```

## Java

```bash
cd javaspider
mvn test
mvn -q -Dmaven.test.skip=true package
java -cp target/classes com.javaspider.EnhancedSpider config init
java -cp target/classes com.javaspider.EnhancedSpider doctor
```

## Rust

```bash
cd rustspider
cargo test
cargo build --release --bin rustspider
cargo run -- config init
cargo run -- doctor
```
