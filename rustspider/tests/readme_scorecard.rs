use std::fs;
use std::path::PathBuf;

#[test]
fn readme_covers_quick_start_api_and_deploy() {
    let readme = fs::read_to_string(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("README.md"))
        .expect("README");

    assert!(readme.contains("Quick Start"));
    assert!(readme.contains("API"));
    assert!(readme.contains("Deploy"));
}
