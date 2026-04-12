from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_publish_metadata_no_longer_uses_placeholder_contacts_or_repo_urls():
    py_setup = (ROOT / "pyspider" / "setup.py").read_text(encoding="utf-8")
    java_pom = (ROOT / "javaspider" / "pom.xml").read_text(encoding="utf-8")

    assert "team@pyspider.dev" not in py_setup
    assert "https://github.com/pyspider/pyspider" not in py_setup
    assert "team@javaspider.com" not in java_pom
    assert "github.com/javaspider/javaspider" not in java_pom


def test_static_runtime_project_runners_do_not_compile_project_source_at_runtime():
    go_runner = (ROOT / "gospider" / "cmd" / "gospider" / "main.go").read_text(encoding="utf-8")
    rust_runner = (ROOT / "rustspider" / "src" / "main.rs").read_text(encoding="utf-8")
    java_runner = (
        ROOT
        / "javaspider"
        / "src"
        / "main"
        / "java"
        / "com"
        / "javaspider"
        / "EnhancedSpider.java"
    ).read_text(encoding="utf-8")

    assert 'exec.Command("go", "run"' not in go_runner
    assert 'Command::new("cargo")' not in rust_runner.split('if subcommand == "run"', 1)[1].split("let callback =", 1)[0]
    assert "javac" not in java_runner
    assert "runJavaScrapyProject" not in java_runner
    assert "metadata-fallback" not in go_runner
    assert "metadata-fallback" not in rust_runner
    assert "metadata-fallback" not in java_runner


def test_static_runtime_starters_use_public_package_style_dependencies_and_runner_artifacts():
    go_manifest = (ROOT / "examples" / "starters" / "gospider-starter" / "scrapy-project.json").read_text(encoding="utf-8")
    rust_manifest = (ROOT / "examples" / "starters" / "rustspider-starter" / "scrapy-project.json").read_text(encoding="utf-8")
    java_manifest = (ROOT / "examples" / "starters" / "javaspider-starter" / "scrapy-project.json").read_text(encoding="utf-8")
    go_mod = (ROOT / "examples" / "starters" / "gospider-starter" / "go.mod").read_text(encoding="utf-8")
    rust_toml = (ROOT / "examples" / "starters" / "rustspider-starter" / "Cargo.toml").read_text(encoding="utf-8")

    assert '"runner": "dist/gospider-project"' in go_manifest
    assert '"runner": "dist/rustspider-project"' in rust_manifest
    assert '"runner": "build/project-runner.jar"' in java_manifest
    assert "replace gospider =>" not in go_mod
    assert 'path = "../../../rustspider"' not in rust_toml


def test_public_readmes_document_beta_positioning_and_project_runner_policy():
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    go_readme = (ROOT / "gospider" / "README.md").read_text(encoding="utf-8")
    rust_readme = (ROOT / "rustspider" / "README.md").read_text(encoding="utf-8")
    java_readme = (ROOT / "javaspider" / "README.md").read_text(encoding="utf-8")

    assert "beta/preview" in root_readme
    assert "built-in metadata runner" in root_readme.lower()
    assert "built-in metadata runner" in go_readme.lower()
    assert "built-in metadata runner" in rust_readme.lower()
    assert "built-in metadata runner" in java_readme.lower()
    assert "project runner artifact" in root_readme.lower()
    assert "project runner artifact" in go_readme.lower()
    assert "project runner artifact" in rust_readme.lower()
    assert "project runner jar artifact" in java_readme.lower()


def test_schema_ids_are_not_left_on_example_invalid_placeholders():
    schema = (ROOT / "schemas" / "scrapy-plugins.schema.json").read_text(encoding="utf-8")
    assert "example.invalid" not in schema
