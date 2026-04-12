from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_static_runtimes_support_config_yaml_fallback_in_shared_config_loader():
    java = (
        ROOT
        / "javaspider"
        / "src"
        / "main"
        / "java"
        / "com"
        / "javaspider"
        / "EnhancedSpider.java"
    ).read_text(encoding="utf-8")
    go = (ROOT / "gospider" / "cmd" / "gospider" / "main.go").read_text(encoding="utf-8")
    rust = (ROOT / "rustspider" / "src" / "main.rs").read_text(encoding="utf-8")

    assert '"config.yaml"' in java
    assert '"config.yaml"' in go
    assert '"config.yaml"' in rust


def test_checkpoint_defaults_point_at_shared_artifact_layout():
    py_checkpoint = (ROOT / "pyspider" / "core" / "checkpoint.py").read_text(encoding="utf-8")
    java_checkpoint = (
        ROOT
        / "javaspider"
        / "src"
        / "main"
        / "java"
        / "com"
        / "javaspider"
        / "core"
        / "CheckpointManager.java"
    ).read_text(encoding="utf-8")
    rust_checkpoint = (ROOT / "rustspider" / "src" / "checkpoint.rs").read_text(encoding="utf-8")

    assert 'checkpoint_dir: str = "artifacts/checkpoints"' in py_checkpoint
    assert 'CheckpointManager("artifacts/checkpoints")' in java_checkpoint
    assert 'CheckpointManager::new("artifacts/checkpoints", Some(300))' in rust_checkpoint


def test_java_exporter_uses_machine_readable_timestamp():
    exporter = (
        ROOT
        / "javaspider"
        / "src"
        / "main"
        / "java"
        / "com"
        / "javaspider"
        / "Exporter.java"
    ).read_text(encoding="utf-8")

    assert "Instant.now().toString()" in exporter
