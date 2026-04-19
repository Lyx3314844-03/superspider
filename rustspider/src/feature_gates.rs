use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::env;

fn default_state() -> BTreeMap<&'static str, bool> {
    BTreeMap::from([
        ("ai", true),
        ("browser", true),
        ("distributed", true),
        ("media", true),
        ("workflow", true),
        ("crawlee", true),
    ])
}

pub fn enabled(name: &str) -> bool {
    let normalized = name.trim().to_ascii_lowercase();
    let env_name = format!(
        "RUSTSPIDER_FEATURE_{}",
        normalized.replace(['-', '.'], "_").to_ascii_uppercase()
    );
    match env::var(&env_name) {
        Ok(value) => matches!(
            value.trim().to_ascii_lowercase().as_str(),
            "1" | "true" | "yes" | "on"
        ),
        Err(_) => default_state()
            .get(normalized.as_str())
            .copied()
            .unwrap_or(false),
    }
}

pub fn catalog() -> Value {
    let defaults = default_state();
    json!({
        "default_profile": "full",
        "profiles": {
            "lite": ["browser", "workflow"],
            "ai": ["ai", "browser", "workflow"],
            "distributed": ["browser", "distributed", "workflow", "crawlee"],
            "full": ["ai", "browser", "distributed", "media", "workflow", "crawlee"]
        },
        "env_prefix": "RUSTSPIDER_FEATURE_",
        "features": defaults
            .keys()
            .map(|name| ((*name).to_string(), enabled(name)))
            .collect::<BTreeMap<String, bool>>()
    })
}
