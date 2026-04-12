use std::fs;
use std::path::PathBuf;

#[test]
fn browser_example_and_examples_readme_exist() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let example = fs::read_to_string(root.join("examples").join("playwright_example.rs"))
        .expect("browser example");
    let readme =
        fs::read_to_string(root.join("examples").join("README.md")).expect("examples readme");

    assert!(example.contains("Browser"));
    assert!(readme.contains("Examples"));
}
