use rustspider::browser::browser_compatibility_matrix;

#[test]
fn browser_compatibility_reports_webdriver_base_engine() {
    let payload = browser_compatibility_matrix();

    assert_eq!(payload["base_engine"], "fantoccini-webdriver");
    assert_eq!(payload["bridge_style"], "webdriver-and-helper");
}

#[test]
fn browser_compatibility_reports_playwright_helper_surface() {
    let payload = browser_compatibility_matrix();
    let playwright = &payload["surfaces"]["playwright"];

    assert_eq!(playwright["supported"], true);
    assert_eq!(playwright["mode"], "native-process");
    assert_eq!(playwright["adapter_engine"], "node-playwright");
}

#[test]
fn browser_compatibility_reports_native_webdriver_surface() {
    let payload = browser_compatibility_matrix();
    let webdriver = &payload["surfaces"]["webdriver"];
    let selenium = &payload["surfaces"]["selenium"];

    assert_eq!(webdriver["supported"], true);
    assert_eq!(webdriver["mode"], "native");
    assert_eq!(webdriver["adapter_engine"], "fantoccini-webdriver");
    assert_eq!(selenium["mode"], "native");
    assert_eq!(selenium["adapter_engine"], "fantoccini-webdriver");
}

#[test]
fn browser_compatibility_reports_upload_and_iframe_support() {
    let payload = browser_compatibility_matrix();

    assert_eq!(payload["interaction"]["file_upload"], true);
    assert_eq!(
        payload["interaction"]["iframe_switching"],
        "webdriver-frame-switch"
    );
    assert_eq!(
        payload["interaction"]["shadow_dom"],
        "open-shadow-root-helper"
    );
    assert_eq!(
        payload["interaction"]["realtime_stream_capture"],
        "in-page-websocket-eventsource-hook"
    );
}
