use rustspider::{run_preflight, CommandRequirement, PreflightOptions};

#[test]
fn preflight_options_include_expected_browser_and_media_requirements() {
    let options = PreflightOptions::new()
        .require_browser()
        .require_ffmpeg()
        .require_yt_dlp();

    let names: Vec<_> = options
        .command_requirements
        .iter()
        .map(|item| item.name.as_str())
        .collect();

    assert!(names.contains(&"browser automation runtime"));
    assert!(names.contains(&"ffmpeg"));
    assert!(names.contains(&"yt-dlp"));
}

#[test]
fn preflight_report_summary_text_tracks_pass_and_fail_counts() {
    let options = PreflightOptions::new().with_command_requirement(CommandRequirement::new(
        "missing-tool",
        vec!["definitely-missing-binary".to_string()],
    ));
    let report = run_preflight(&options);

    assert_eq!(report.summary(), "failed");
    assert!(report.summary_text().contains("failed"));
}
