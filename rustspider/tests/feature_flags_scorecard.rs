use std::fs;
use std::path::PathBuf;

#[test]
fn cargo_manifest_lists_expected_feature_flags() {
    let manifest = fs::read_to_string(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("Cargo.toml"))
        .expect("Cargo.toml");

    assert!(manifest.contains("default = [\"browser\"]"));
    assert!(manifest.contains("distributed = [\"redis\"]"));
    assert!(manifest
        .contains("api = [\"axum\", \"tower\", \"tower-http\", \"prometheus\", \"sysinfo\"]"));
    assert!(manifest.contains("full = [\"video\", \"distributed\", \"api\", \"web\", \"ai\"]"));
}
