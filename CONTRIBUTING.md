# Contributing to SuperSpider

Thank you for your interest in contributing to SuperSpider.

SuperSpider is a four-runtime crawler framework. Contributions are welcome across all four runtimes: `pyspider`, `gospider`, `rustspider`, and `javaspider`.

## How to Contribute

### Reporting Issues

- Use the GitHub Issues tracker.
- Include the runtime name (`pyspider`, `gospider`, `rustspider`, or `javaspider`) in the issue title.
- Describe the problem clearly: what you expected, what happened, and how to reproduce it.
- Include your OS, runtime version, and relevant configuration.

### Submitting Pull Requests

1. Fork the repository.
2. Create a branch from `main`:
   ```
   git checkout -b fix/your-description
   ```
3. Make your changes in the relevant runtime directory.
4. Test your changes using the runtime's own test suite (see below).
5. Commit with a clear message:
   ```
   git commit -m "pyspider: fix proxy pool rotation under high concurrency"
   ```
6. Push your branch and open a pull request against `main`.

### Commit Message Format

Use the runtime name as a prefix:

```
pyspider: <description>
gospider: <description>
rustspider: <description>
javaspider: <description>
docs: <description>
```

## Running Tests

### PySpider

```bash
cd pyspider
pip install -e .
pytest tests/
```

### GoSpider

```bash
cd gospider
go test ./...
```

### RustSpider

```bash
cd rustspider
cargo test
```

### JavaSpider

```bash
cd javaspider
mvn test
```

## Code Style

- **Python**: follow PEP 8. Use type hints where practical.
- **Go**: run `gofmt` before committing.
- **Rust**: run `cargo fmt` and `cargo clippy` before committing.
- **Java**: follow standard Java conventions. Use the project's existing code style.

## Scope of Contributions

Contributions are most useful in these areas:

- Bug fixes in any of the four runtimes
- Documentation improvements (English only for public-facing docs)
- Test coverage improvements
- Performance improvements with benchmarks
- New extractor or media platform support

Please open an issue before starting large feature work so we can discuss scope and approach.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
