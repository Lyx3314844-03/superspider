//! 运行前自检模块
//! 用于在生产或试运行前检查依赖、网络和工作目录状态

use serde::Serialize;
use std::env;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::net::{TcpStream, ToSocketAddrs};
use std::path::{Path, PathBuf};
use std::time::Duration;

/// 自检状态
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum CheckStatus {
    Passed,
    Failed,
}

/// 单项自检结果
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct PreflightCheck {
    pub name: String,
    pub status: CheckStatus,
    pub details: String,
}

impl PreflightCheck {
    fn passed(name: impl Into<String>, details: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            status: CheckStatus::Passed,
            details: details.into(),
        }
    }

    fn failed(name: impl Into<String>, details: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            status: CheckStatus::Failed,
            details: details.into(),
        }
    }
}

/// 命令依赖要求
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommandRequirement {
    pub name: String,
    pub candidates: Vec<String>,
}

impl CommandRequirement {
    pub fn new(name: impl Into<String>, candidates: Vec<String>) -> Self {
        Self {
            name: name.into(),
            candidates,
        }
    }
}

/// 自检选项
#[derive(Debug, Clone)]
pub struct PreflightOptions {
    pub writable_paths: Vec<PathBuf>,
    pub network_targets: Vec<String>,
    pub redis_url: Option<String>,
    pub command_requirements: Vec<CommandRequirement>,
    pub timeout: Duration,
}

impl PreflightOptions {
    pub fn new() -> Self {
        Self {
            writable_paths: Vec::new(),
            network_targets: Vec::new(),
            redis_url: None,
            command_requirements: Vec::new(),
            timeout: Duration::from_secs(3),
        }
    }

    pub fn with_writable_path(mut self, path: impl Into<PathBuf>) -> Self {
        self.writable_paths.push(path.into());
        self
    }

    pub fn with_network_target(mut self, target: impl Into<String>) -> Self {
        self.network_targets.push(target.into());
        self
    }

    pub fn with_redis_url(mut self, redis_url: impl Into<String>) -> Self {
        self.redis_url = Some(redis_url.into());
        self
    }

    pub fn with_timeout(mut self, timeout: Duration) -> Self {
        self.timeout = timeout;
        self
    }

    pub fn with_command_requirement(mut self, requirement: CommandRequirement) -> Self {
        self.command_requirements.push(requirement);
        self
    }

    pub fn require_yt_dlp(self) -> Self {
        self.with_command_requirement(CommandRequirement::new(
            "yt-dlp",
            vec!["yt-dlp".to_string()],
        ))
    }

    pub fn require_ffmpeg(self) -> Self {
        self.with_command_requirement(CommandRequirement::new(
            "ffmpeg",
            vec![
                "ffmpeg".to_string(),
                r"C:\ffmpeg\ffmpeg.exe".to_string(),
                r"C:\ffmpeg\bin\ffmpeg.exe".to_string(),
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe".to_string(),
            ],
        ))
    }

    pub fn require_browser(self) -> Self {
        self.with_command_requirement(CommandRequirement::new(
            "browser automation runtime",
            vec![
                "chrome".to_string(),
                "chromedriver".to_string(),
                "msedgedriver".to_string(),
                "geckodriver".to_string(),
                "google-chrome".to_string(),
                "chromium".to_string(),
                "msedge".to_string(),
                r"C:\Program Files\Google\Chrome\Application\chrome.exe".to_string(),
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe".to_string(),
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe".to_string(),
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe".to_string(),
            ],
        ))
    }
}

impl Default for PreflightOptions {
    fn default() -> Self {
        Self::new()
    }
}

/// 自检报告
#[derive(Debug, Clone, Serialize)]
pub struct PreflightReport {
    pub checks: Vec<PreflightCheck>,
}

impl PreflightReport {
    pub fn is_success(&self) -> bool {
        self.checks
            .iter()
            .all(|check| check.status == CheckStatus::Passed)
    }

    pub fn failures(&self) -> Vec<&PreflightCheck> {
        self.checks
            .iter()
            .filter(|check| check.status == CheckStatus::Failed)
            .collect()
    }

    pub fn ensure_success(&self) -> Result<(), String> {
        if self.is_success() {
            return Ok(());
        }

        let summary = self
            .failures()
            .into_iter()
            .map(|check| format!("{}: {}", check.name, check.details))
            .collect::<Vec<_>>()
            .join("; ");

        Err(summary)
    }

    pub fn summary(&self) -> &'static str {
        if self.is_success() {
            "passed"
        } else {
            "failed"
        }
    }

    pub fn to_json(&self) -> serde_json::Result<String> {
        #[derive(Serialize)]
        struct SerializableReport<'a> {
            command: &'static str,
            runtime: &'static str,
            exit_code: i32,
            summary: &'a str,
            checks: &'a [PreflightCheck],
        }

        serde_json::to_string_pretty(&SerializableReport {
            command: "preflight",
            runtime: "rust",
            exit_code: if self.is_success() { 0 } else { 1 },
            summary: self.summary(),
            checks: &self.checks,
        })
    }
}

/// 执行运行前自检
pub fn run_preflight(options: &PreflightOptions) -> PreflightReport {
    let mut checks = Vec::new();

    for path in &options.writable_paths {
        let name = format!("filesystem:{}", path.display());
        match check_writable_path(path) {
            Ok(details) => checks.push(PreflightCheck::passed(name, details)),
            Err(details) => checks.push(PreflightCheck::failed(name, details)),
        }
    }

    for target in &options.network_targets {
        let name = format!("network:{target}");
        match check_tcp_target(target, options.timeout) {
            Ok(details) => checks.push(PreflightCheck::passed(name, details)),
            Err(details) => checks.push(PreflightCheck::failed(name, details)),
        }
    }

    if let Some(redis_url) = &options.redis_url {
        let name = format!("redis:{redis_url}");
        match check_tcp_target(redis_url, options.timeout) {
            Ok(details) => checks.push(PreflightCheck::passed(name, details)),
            Err(details) => checks.push(PreflightCheck::failed(name, details)),
        }
    }

    for requirement in &options.command_requirements {
        let name = format!("dependency:{}", requirement.name);
        match find_command_in_path(&requirement.candidates) {
            Some(path) => checks.push(PreflightCheck::passed(
                name,
                format!("found {}", path.display()),
            )),
            None => checks.push(PreflightCheck::failed(
                name,
                format!("missing any of {:?}", requirement.candidates),
            )),
        }
    }

    PreflightReport { checks }
}

fn check_writable_path(path: &Path) -> Result<String, String> {
    fs::create_dir_all(path)
        .map_err(|err| format!("cannot create directory {}: {}", path.display(), err))?;

    let probe_path = path.join(format!(
        ".rustspider-preflight-{}-{}.tmp",
        std::process::id(),
        current_timestamp_millis()
    ));

    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&probe_path)
        .map_err(|err| format!("cannot create probe file {}: {}", probe_path.display(), err))?;

    file.write_all(b"rustspider preflight")
        .map_err(|err| format!("cannot write probe file {}: {}", probe_path.display(), err))?;

    drop(file);
    fs::remove_file(&probe_path)
        .map_err(|err| format!("cannot remove probe file {}: {}", probe_path.display(), err))?;

    Ok(format!("writable {}", path.display()))
}

fn check_tcp_target(target: &str, timeout: Duration) -> Result<String, String> {
    let addresses = resolve_target_addresses(target)?;
    let first = addresses
        .first()
        .ok_or_else(|| format!("no socket address resolved for {target}"))?;

    TcpStream::connect_timeout(first, timeout)
        .map_err(|err| format!("cannot connect to {}: {}", first, err))?;

    Ok(format!("reachable {}", first))
}

fn resolve_target_addresses(target: &str) -> Result<Vec<std::net::SocketAddr>, String> {
    if target.contains("://") {
        let parsed =
            url::Url::parse(target).map_err(|err| format!("invalid url {target}: {err}"))?;
        let host = parsed
            .host_str()
            .ok_or_else(|| format!("missing host in url {target}"))?;
        let port = parsed
            .port_or_known_default()
            .ok_or_else(|| format!("missing port for url {target}"))?;
        return resolve_host_and_port(host, port);
    }

    let host_port = target
        .rsplit_once(':')
        .ok_or_else(|| format!("target must be URL or host:port, got {target}"))?;
    let port = host_port
        .1
        .parse::<u16>()
        .map_err(|err| format!("invalid port in {target}: {err}"))?;

    resolve_host_and_port(host_port.0, port)
}

fn resolve_host_and_port(host: &str, port: u16) -> Result<Vec<std::net::SocketAddr>, String> {
    let addresses = (host, port)
        .to_socket_addrs()
        .map_err(|err| format!("dns lookup failed for {host}:{port}: {err}"))?
        .collect::<Vec<_>>();

    if addresses.is_empty() {
        Err(format!("no addresses returned for {host}:{port}"))
    } else {
        Ok(addresses)
    }
}

fn find_command_in_path(candidates: &[String]) -> Option<PathBuf> {
    let path_var = env::var_os("PATH")?;
    let search_dirs = env::split_paths(&path_var).collect::<Vec<_>>();
    find_command_in_dirs(candidates, &search_dirs)
}

fn find_command_in_dirs(candidates: &[String], search_dirs: &[PathBuf]) -> Option<PathBuf> {
    for candidate in candidates {
        let candidate_path = Path::new(candidate);
        if candidate_path.is_absolute() && candidate_path.is_file() {
            return Some(candidate_path.to_path_buf());
        }

        let possible_names = candidate_names(candidate);
        for dir in search_dirs {
            for name in &possible_names {
                let path = dir.join(name);
                if path.is_file() {
                    return Some(path);
                }
            }
        }
    }

    None
}

fn candidate_names(candidate: &str) -> Vec<String> {
    #[cfg(windows)]
    {
        let candidate_path = Path::new(candidate);
        if candidate_path.extension().is_some() {
            return vec![candidate.to_string()];
        }

        let pathext = env::var("PATHEXT").unwrap_or_else(|_| ".COM;.EXE;.BAT;.CMD".to_string());
        let mut names = vec![candidate.to_string()];
        for ext in pathext.split(';').filter(|ext| !ext.is_empty()) {
            names.push(format!("{}{}", candidate, ext.to_ascii_lowercase()));
            names.push(format!("{}{}", candidate, ext.to_ascii_uppercase()));
        }
        names
    }

    #[cfg(not(windows))]
    {
        vec![candidate.to_string()]
    }
}

fn current_timestamp_millis() -> u128 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn writable_path_check_passes_for_temp_directory() {
        let temp_dir = unique_temp_dir("preflight-writable");
        let result = check_writable_path(&temp_dir);
        assert!(result.is_ok());
        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn resolve_target_addresses_supports_http_url() {
        let addresses = resolve_target_addresses("http://127.0.0.1").unwrap();
        assert!(!addresses.is_empty());
    }

    #[test]
    fn resolve_target_addresses_supports_host_port() {
        let addresses = resolve_target_addresses("localhost:80").unwrap();
        assert!(!addresses.is_empty());
    }

    #[test]
    fn command_lookup_uses_provided_directories() {
        let temp_dir = unique_temp_dir("preflight-command");
        fs::create_dir_all(&temp_dir).unwrap();

        let executable_name = if cfg!(windows) {
            "fake-tool.exe"
        } else {
            "fake-tool"
        };
        let executable_path = temp_dir.join(executable_name);
        fs::write(&executable_path, b"echo test").unwrap();

        let result = find_command_in_dirs(
            &[String::from("fake-tool")],
            std::slice::from_ref(&temp_dir),
        );

        assert_eq!(result, Some(executable_path));
        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn command_lookup_accepts_absolute_candidate_paths() {
        let temp_dir = unique_temp_dir("preflight-absolute-command");
        fs::create_dir_all(&temp_dir).unwrap();

        let executable_name = if cfg!(windows) {
            "fake-tool.exe"
        } else {
            "fake-tool"
        };
        let executable_path = temp_dir.join(executable_name);
        fs::write(&executable_path, b"echo test").unwrap();

        let result = find_command_in_dirs(&[executable_path.to_string_lossy().to_string()], &[]);

        assert_eq!(result, Some(executable_path.clone()));
        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn report_aggregates_failures() {
        let report = PreflightReport {
            checks: vec![
                PreflightCheck::passed("filesystem:data", "ok"),
                PreflightCheck::failed("dependency:ffmpeg", "missing"),
            ],
        };

        assert!(!report.is_success());
        assert_eq!(report.failures().len(), 1);
        assert!(report.ensure_success().is_err());
    }

    #[test]
    fn preflight_reports_missing_custom_command() {
        let options = PreflightOptions::new().with_command_requirement(CommandRequirement::new(
            "missing-tool",
            vec!["definitely-missing-command".to_string()],
        ));

        let report = run_preflight(&options);
        assert_eq!(report.checks.len(), 1);
        assert_eq!(report.checks[0].status, CheckStatus::Failed);
    }

    #[test]
    fn preflight_report_can_serialize_to_json() {
        let report = PreflightReport {
            checks: vec![
                PreflightCheck::passed("filesystem:data", "ok"),
                PreflightCheck::failed("dependency:ffmpeg", "missing"),
            ],
        };

        let json = report.to_json().expect("report should serialize");
        let value: serde_json::Value = serde_json::from_str(&json).expect("json should parse");

        assert_eq!(value["command"], "preflight");
        assert_eq!(value["summary"], "failed");
        assert_eq!(value["exit_code"], 1);
        assert_eq!(value["checks"][0]["status"], "passed");
        assert_eq!(value["checks"][1]["name"], "dependency:ffmpeg");
    }

    #[test]
    fn browser_requirement_includes_linux_chrome_binary() {
        let options = PreflightOptions::new().require_browser();

        assert_eq!(options.command_requirements.len(), 1);
        assert!(options.command_requirements[0]
            .candidates
            .contains(&"chrome".to_string()));
    }

    fn unique_temp_dir(prefix: &str) -> PathBuf {
        env::temp_dir().join(format!(
            "{}-{}-{}",
            prefix,
            std::process::id(),
            current_timestamp_millis()
        ))
    }
}
