//! 视频平台解析器
//! 支持优酷、爱奇艺、腾讯等平台

use md5::{Digest, Md5};
use regex::Regex;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::error::Error;
use url::Url;

/// 视频数据
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VideoData {
    pub title: String,
    pub video_id: String,
    pub platform: String,
    pub m3u8_url: Option<String>,
    pub mp4_url: Option<String>,
    pub dash_url: Option<String>,
    pub download_url: Option<String>,
    pub cover_url: Option<String>,
    pub duration: i64,
    pub description: String,
}

fn clean_text(value: &str) -> String {
    value.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn normalize_media_url(page_url: &str, candidate: &str) -> Option<String> {
    let value = candidate
        .replace("\\/", "/")
        .replace("\\u002F", "/")
        .replace("\\u003A", ":")
        .trim()
        .to_string();
    if value.is_empty() || value.starts_with("data:") || value.starts_with("javascript:") {
        return None;
    }
    if value.starts_with("//") {
        let scheme = Url::parse(page_url)
            .ok()
            .map(|parsed| parsed.scheme().to_string())
            .unwrap_or_else(|| "https".to_string());
        return Some(format!("{scheme}:{value}"));
    }
    if let Ok(parsed) = Url::parse(&value) {
        return Some(parsed.to_string());
    }
    Url::parse(page_url)
        .ok()
        .and_then(|base| base.join(&value).ok())
        .map(|joined| joined.to_string())
}

fn classify_media_url(url: &str) -> &'static str {
    let lower = url.to_lowercase();
    if lower.contains(".m3u8") {
        "m3u8"
    } else if lower.contains(".mpd") || lower.contains("dash") {
        "dash"
    } else if [".mp4", ".webm", ".m4v", ".mov", ".m4s"]
        .iter()
        .any(|ext| lower.contains(ext))
    {
        "mp4"
    } else {
        "download"
    }
}

fn is_media_url(url: &str) -> bool {
    matches!(classify_media_url(url), "m3u8" | "dash" | "mp4")
}

fn collect_from_json(
    value: &Value,
    page_url: &str,
    title: &mut Option<String>,
    description: &mut Option<String>,
    cover_url: &mut Option<String>,
    urls: &mut Vec<String>,
) {
    match value {
        Value::Array(items) => {
            for item in items {
                collect_from_json(item, page_url, title, description, cover_url, urls);
            }
        }
        Value::Object(map) => {
            let object_types = match map.get("@type") {
                Some(Value::String(kind)) => vec![kind.to_lowercase()],
                Some(Value::Array(items)) => items
                    .iter()
                    .filter_map(|item| item.as_str().map(|s| s.to_lowercase()))
                    .collect(),
                _ => Vec::new(),
            };

            if object_types.iter().any(|kind| kind == "videoobject") {
                if let Some(name) = map
                    .get("name")
                    .and_then(Value::as_str)
                    .or_else(|| map.get("headline").and_then(Value::as_str))
                    .map(clean_text)
                {
                    *title = Some(name);
                }
                if let Some(text) = map
                    .get("description")
                    .and_then(Value::as_str)
                    .map(clean_text)
                {
                    *description = Some(text);
                }
                if cover_url.is_none() {
                    *cover_url = map
                        .get("thumbnailUrl")
                        .and_then(Value::as_str)
                        .and_then(|candidate| normalize_media_url(page_url, candidate));
                }
            }

            for key in [
                "contentUrl",
                "embedUrl",
                "url",
                "videoUrl",
                "video_url",
                "playAddr",
                "play_url",
                "m3u8Url",
                "m3u8_url",
                "dashUrl",
                "dash_url",
                "mp4Url",
                "mp4_url",
                "baseUrl",
                "base_url",
            ] {
                if let Some(candidate) = map
                    .get(key)
                    .and_then(Value::as_str)
                    .and_then(|raw| normalize_media_url(page_url, raw))
                {
                    urls.push(candidate);
                }
            }

            if description.is_none() {
                if let Some(text) = map.get("desc").and_then(Value::as_str).map(clean_text) {
                    *description = Some(text);
                }
            }
            if cover_url.is_none() {
                for key in ["cover", "pic", "poster", "dynamic_cover", "originCover"] {
                    if let Some(candidate) = map
                        .get(key)
                        .and_then(Value::as_str)
                        .and_then(|raw| normalize_media_url(page_url, raw))
                    {
                        *cover_url = Some(candidate);
                        break;
                    }
                }
            }

            for nested in map.values() {
                collect_from_json(nested, page_url, title, description, cover_url, urls);
            }
        }
        _ => {}
    }
}

/// 通用解析器
pub struct UniversalParser {
    client: reqwest::blocking::Client,
}

impl UniversalParser {
    pub fn new() -> Result<Self, Box<dyn Error>> {
        let client = reqwest::blocking::Client::builder()
            .timeout(std::time::Duration::from_secs(30))
            .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            .build()?;

        Ok(Self { client })
    }

    /// 解析视频
    pub fn parse(&self, url: &str) -> Option<VideoData> {
        // 检测平台
        let mut specific = None;
        if let Some(platform) = self.detect_platform(url) {
            match platform {
                "youku" => specific = self.parse_youku(url),
                "iqiyi" => specific = self.parse_iqiyi(url),
                "tencent" => specific = self.parse_tencent(url),
                "bilibili" => specific = self.parse_bilibili(url),
                "douyin" => specific = self.parse_douyin(url),
                _ => {}
            }
        }

        // 通用解析
        merge_video_data(specific, self.universal_parse(url))
    }

    pub fn parse_artifacts(
        &self,
        page_url: &str,
        html: Option<&str>,
        artifact_texts: &[String],
    ) -> Option<VideoData> {
        let generic = self.universal_parse_artifacts(page_url, html, artifact_texts);
        merge_video_data(None, generic)
    }

    fn detect_platform(&self, url: &str) -> Option<&str> {
        if url.contains("youku.com") || url.contains("youku.tv") {
            Some("youku")
        } else if url.contains("iqiyi.com")
            || self
                .extract_video_id_from_patterns(
                    url,
                    &[
                        r"/v_([A-Za-z0-9]+)\.html",
                        r"/play/([A-Za-z0-9]+)",
                        r"[?&]curid=([^&]+)",
                    ],
                )
                .is_some()
        {
            Some("iqiyi")
        } else if url.contains("qq.com")
            || url.contains("v.qq.com")
            || self
                .extract_video_id_from_patterns(
                    url,
                    &[
                        r"/x/cover/[^/]+/([A-Za-z0-9]+)\.html",
                        r"/x/page/([A-Za-z0-9]+)\.html",
                        r"/x/([A-Za-z0-9]+)\.html",
                        r"[?&]vid=([A-Za-z0-9]+)",
                    ],
                )
                .is_some()
        {
            Some("tencent")
        } else if url.contains("bilibili.com") || url.contains("b23.tv") {
            Some("bilibili")
        } else if url.contains("douyin.com") {
            Some("douyin")
        } else if url
            .split("/video/")
            .nth(1)
            .map(|tail| {
                tail.chars()
                    .take_while(|ch| ch.is_ascii_alphanumeric())
                    .collect::<String>()
            })
            .map(|token| token.starts_with("BV") || token.starts_with("av"))
            .unwrap_or(false)
        {
            Some("bilibili")
        } else if url
            .split("/video/")
            .nth(1)
            .map(|tail| {
                let token = tail
                    .chars()
                    .take_while(|ch| ch.is_ascii_digit())
                    .collect::<String>();
                !token.is_empty()
            })
            .unwrap_or(false)
        {
            Some("douyin")
        } else {
            None
        }
    }

    fn parse_youku(&self, url: &str) -> Option<VideoData> {
        let video_id = self.extract_video_id(url, r"id_(?:X)?([a-zA-Z0-9=]+)")?;

        // 获取页面
        let resp = self.client.get(url).send().ok()?;
        let html = resp.text().ok()?;

        let title = self.extract_title(&html, &video_id);
        let video_data = self.extract_video_data(&html);

        Some(VideoData {
            title,
            video_id,
            platform: "youku".to_string(),
            m3u8_url: video_data.get("m3u8_url").cloned(),
            mp4_url: video_data.get("mp4_url").cloned(),
            dash_url: video_data.get("dash_url").cloned(),
            download_url: video_data.get("download_url").cloned(),
            cover_url: video_data.get("cover_url").cloned(),
            duration: 0,
            description: String::new(),
        })
    }

    fn parse_iqiyi(&self, url: &str) -> Option<VideoData> {
        let video_id = self.extract_video_id_from_patterns(
            url,
            &[
                r"/v_([A-Za-z0-9]+)\.html",
                r"/play/([A-Za-z0-9]+)",
                r"[?&]curid=([^&]+)",
            ],
        )?;

        let resp = self.client.get(url).send().ok()?;
        let html = resp.text().ok()?;

        let title = self.extract_title(&html, &video_id);
        let video_data = self.extract_video_data(&html);
        let m3u8_url = video_data.get("m3u8_url").cloned();
        let dash_url = video_data.get("dash_url").cloned();
        let cover_url = video_data.get("cover_url").cloned();
        let description = Regex::new(r#""(?:desc|description)"\s*:\s*"([^"]+)""#)
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().to_string())
            .unwrap_or_default();
        let duration = Regex::new(r#""duration"\s*:\s*(\d+)"#)
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .and_then(|m| m.as_str().parse().ok())
            .unwrap_or(0);

        Some(VideoData {
            title,
            video_id,
            platform: "iqiyi".to_string(),
            m3u8_url,
            mp4_url: None,
            dash_url,
            download_url: None,
            cover_url,
            duration,
            description,
        })
    }

    fn parse_tencent(&self, url: &str) -> Option<VideoData> {
        let video_id = self.extract_video_id_from_patterns(
            url,
            &[
                r"/x/cover/[^/]+/([A-Za-z0-9]+)\.html",
                r"/x/page/([A-Za-z0-9]+)\.html",
                r"/x/([A-Za-z0-9]+)\.html",
                r"[?&]vid=([A-Za-z0-9]+)",
            ],
        )?;

        let resp = self.client.get(url).send().ok()?;
        let html = resp.text().ok()?;

        let title = self.extract_title(&html, &video_id);
        let video_data = self.extract_video_data(&html);
        let mp4_url = video_data.get("mp4_url").cloned();
        let m3u8_url = video_data.get("m3u8_url").cloned();
        let dash_url = video_data.get("dash_url").cloned();
        let cover_url = video_data.get("cover_url").cloned();
        let description = Regex::new(r#""(?:desc|description)"\s*:\s*"([^"]+)""#)
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().to_string())
            .unwrap_or_default();
        let duration = Regex::new(r#""duration"\s*:\s*(\d+)"#)
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .and_then(|m| m.as_str().parse().ok())
            .unwrap_or(0);

        Some(VideoData {
            title,
            video_id,
            platform: "tencent".to_string(),
            m3u8_url,
            mp4_url,
            dash_url,
            download_url: None,
            cover_url,
            duration,
            description,
        })
    }

    fn parse_bilibili(&self, url: &str) -> Option<VideoData> {
        let video_id = self.extract_video_id(url, r"/video/((?:BV|av)[A-Za-z0-9]+)")?;
        let resp = self.client.get(url).send().ok()?;
        let html = resp.text().ok()?;
        let title = self.extract_title(&html, &video_id);

        let cover_url = Regex::new(r#""(?:cover|pic|thumbnailUrl)"\s*:\s*"([^"]+)""#)
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().to_string());
        let dash_url = Regex::new(r#""baseUrl"\s*:\s*"(https?://[^"]+)""#)
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().to_string());
        let description = Regex::new(r#""(?:desc|description)"\s*:\s*"([^"]+)""#)
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().to_string())
            .unwrap_or_default();
        let duration = Regex::new(r#""duration"\s*:\s*(\d+)"#)
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .and_then(|m| m.as_str().parse().ok())
            .unwrap_or(0);

        Some(VideoData {
            title,
            video_id,
            platform: "bilibili".to_string(),
            m3u8_url: None,
            mp4_url: None,
            dash_url,
            download_url: None,
            cover_url,
            duration,
            description,
        })
    }

    fn parse_douyin(&self, url: &str) -> Option<VideoData> {
        let video_id = self.extract_video_id(url, r"/video/(\d+)")?;
        let resp = self.client.get(url).send().ok()?;
        let html = resp.text().ok()?;
        let title = self.extract_title(&html, &video_id);

        let mp4_url = Regex::new(r#""(?:playAddr|play_api|playUrl)"\s*:\s*"([^"]+)""#)
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().replace("\\u002F", "/").replace("\\/", "/"));
        let cover_url = Regex::new(r#""(?:cover|dynamic_cover|originCover)"\s*:\s*"([^"]+)""#)
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().replace("\\u002F", "/").replace("\\/", "/"));
        let description = Regex::new(r#""(?:desc|description)"\s*:\s*"([^"]+)""#)
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().to_string())
            .unwrap_or_default();
        let duration = Regex::new(r#""duration"\s*:\s*(\d+)"#)
            .ok()
            .and_then(|re| re.captures(&html))
            .and_then(|caps| caps.get(1))
            .and_then(|m| m.as_str().parse().ok())
            .unwrap_or(0);

        Some(VideoData {
            title,
            video_id,
            platform: "douyin".to_string(),
            m3u8_url: None,
            mp4_url: mp4_url.clone(),
            dash_url: None,
            download_url: mp4_url,
            cover_url,
            duration,
            description,
        })
    }

    fn universal_parse(&self, url: &str) -> Option<VideoData> {
        if let Some(normalized) = normalize_media_url(url, url) {
            if is_media_url(&normalized) {
                let kind = classify_media_url(&normalized);
                return Some(VideoData {
                    title: "Unknown Video".to_string(),
                    video_id: format!("{:x}", Md5::digest(url.as_bytes())),
                    platform: "generic".to_string(),
                    m3u8_url: if kind == "m3u8" {
                        Some(normalized.clone())
                    } else {
                        None
                    },
                    mp4_url: if kind == "mp4" {
                        Some(normalized.clone())
                    } else {
                        None
                    },
                    dash_url: if kind == "dash" {
                        Some(normalized.clone())
                    } else {
                        None
                    },
                    download_url: if kind == "download" {
                        Some(normalized)
                    } else {
                        None
                    },
                    cover_url: None,
                    duration: 0,
                    description: String::new(),
                });
            }
        }

        let resp = self.client.get(url).send().ok()?;
        let html = resp.text().ok()?;
        self.universal_parse_html(url, &html)
    }

    fn universal_parse_artifacts(
        &self,
        page_url: &str,
        html: Option<&str>,
        artifact_texts: &[String],
    ) -> Option<VideoData> {
        let mut title = html.and_then(|body| {
            Regex::new(r"(?is)<title>([^<]+)</title>")
                .ok()
                .and_then(|re| re.captures(body))
                .and_then(|caps| caps.get(1))
                .map(|m| clean_text(m.as_str()))
        });
        let mut description = None;
        let mut cover_url = None;
        let mut urls = Vec::new();

        if let Some(body) = html {
            if let Some(parsed) = self.universal_parse_html(page_url, body) {
                title = Some(parsed.title);
                description = Some(parsed.description);
                cover_url = parsed.cover_url;
                for candidate in [
                    parsed.m3u8_url,
                    parsed.dash_url,
                    parsed.mp4_url,
                    parsed.download_url,
                ]
                .into_iter()
                .flatten()
                {
                    urls.push(candidate);
                }
            }
        }

        let url_patterns = [
            r#"(?is)\b(?:contentUrl|embedUrl|videoUrl|video_url|playAddr|play_url|m3u8Url|m3u8_url|dashUrl|dash_url|mp4Url|mp4_url|baseUrl|base_url)\b["']?\s*[:=]\s*["']([^"']+)["']"#,
            r#"(https?://[^"'\\s<>]+(?:\.m3u8|\.mpd|\.mp4|\.webm|\.m4v|\.mov|\.m4s)[^"'\\s<>]*)"#,
        ];
        for artifact in artifact_texts {
            for pattern in url_patterns {
                if let Ok(re) = Regex::new(pattern) {
                    for captures in re.captures_iter(artifact) {
                        if let Some(candidate) = captures
                            .get(1)
                            .and_then(|m| normalize_media_url(page_url, m.as_str()))
                        {
                            urls.push(candidate);
                        }
                    }
                }
            }
            if let Ok(value) = serde_json::from_str::<Value>(artifact) {
                collect_from_json(
                    &value,
                    page_url,
                    &mut title,
                    &mut description,
                    &mut cover_url,
                    &mut urls,
                );
            }
        }

        let mut deduped_urls = Vec::new();
        for candidate in urls {
            if !deduped_urls.contains(&candidate) {
                deduped_urls.push(candidate);
            }
        }

        let m3u8_url = deduped_urls
            .iter()
            .find(|candidate| classify_media_url(candidate) == "m3u8")
            .cloned();
        let dash_url = deduped_urls
            .iter()
            .find(|candidate| classify_media_url(candidate) == "dash")
            .cloned();
        let mp4_url = deduped_urls
            .iter()
            .find(|candidate| classify_media_url(candidate) == "mp4")
            .cloned();
        let download_url = deduped_urls
            .iter()
            .find(|candidate| {
                Some(candidate.as_str()) != m3u8_url.as_deref()
                    && Some(candidate.as_str()) != dash_url.as_deref()
                    && Some(candidate.as_str()) != mp4_url.as_deref()
            })
            .cloned();

        if m3u8_url.is_none() && dash_url.is_none() && mp4_url.is_none() && download_url.is_none() {
            return None;
        }

        let mut video = VideoData {
            title: title.unwrap_or_else(|| "Unknown Video".to_string()),
            video_id: format!("{:x}", Md5::digest(page_url.as_bytes())),
            platform: self
                .detect_platform(page_url)
                .unwrap_or("generic-artifact")
                .to_string(),
            m3u8_url,
            mp4_url,
            dash_url,
            download_url,
            cover_url,
            duration: 0,
            description: description.unwrap_or_default(),
        };
        let mut source_text = String::new();
        if let Some(body) = html {
            source_text.push_str(body);
            source_text.push('\n');
        }
        if !artifact_texts.is_empty() {
            source_text.push_str(&artifact_texts.join("\n"));
        }
        self.enrich_generic_video(page_url, &source_text, &mut video);
        Some(video)
    }

    fn universal_parse_html(&self, page_url: &str, html: &str) -> Option<VideoData> {
        let title_patterns = [
            r#"(?is)<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']+)["']"#,
            r#"(?is)<meta[^>]+name=["']twitter:title["'][^>]+content=["']([^"']+)["']"#,
            r"(?is)<title>([^<]+)</title>",
        ];
        let description_patterns = [
            r#"(?is)<meta[^>]+property=["']og:description["'][^>]+content=["']([^"']+)["']"#,
            r#"(?is)<meta[^>]+name=["']description["'][^>]+content=["']([^"']+)["']"#,
        ];
        let cover_patterns = [
            r#"(?is)<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']"#,
            r#"(?is)<meta[^>]+name=["']twitter:image["'][^>]+content=["']([^"']+)["']"#,
            r#"(?is)<video[^>]+poster=["']([^"']+)["']"#,
        ];
        let url_patterns = [
            r#"(?is)<meta[^>]+(?:property|name)=["'](?:og:video(?::url)?|twitter:player:stream)["'][^>]+content=["']([^"']+)["']"#,
            r#"(?is)<video[^>]+src=["']([^"']+)["']"#,
            r#"(?is)<source[^>]+src=["']([^"']+)["']"#,
            r#"(?is)\b(?:contentUrl|embedUrl|videoUrl|video_url|playAddr|play_url|m3u8Url|m3u8_url|dashUrl|dash_url|mp4Url|mp4_url)\b["']?\s*[:=]\s*["']([^"']+)["']"#,
            r#"(https?://[^"'\\s<>]+(?:\.m3u8|\.mpd|\.mp4|\.webm|\.m4v|\.mov)[^"'\\s<>]*)"#,
        ];

        let mut title = title_patterns
            .iter()
            .filter_map(|pattern| Regex::new(pattern).ok())
            .find_map(|re| {
                re.captures(html)
                    .and_then(|caps| caps.get(1))
                    .map(|m| clean_text(m.as_str()))
            });
        let mut description = description_patterns
            .iter()
            .filter_map(|pattern| Regex::new(pattern).ok())
            .find_map(|re| {
                re.captures(html)
                    .and_then(|caps| caps.get(1))
                    .map(|m| clean_text(m.as_str()))
            });
        let mut cover_url = cover_patterns
            .iter()
            .filter_map(|pattern| Regex::new(pattern).ok())
            .find_map(|re| {
                re.captures(html)
                    .and_then(|caps| caps.get(1))
                    .and_then(|m| normalize_media_url(page_url, m.as_str()))
            });
        let mut urls = Vec::new();

        for pattern in url_patterns {
            if let Ok(re) = Regex::new(pattern) {
                for captures in re.captures_iter(html) {
                    if let Some(candidate) = captures
                        .get(1)
                        .and_then(|m| normalize_media_url(page_url, m.as_str()))
                    {
                        urls.push(candidate);
                    }
                }
            }
        }

        if let Ok(ld_re) =
            Regex::new(r#"(?is)<script[^>]+type=["']application/ld\+json["'][^>]*>(.*?)</script>"#)
        {
            for captures in ld_re.captures_iter(html) {
                let Some(raw) = captures.get(1).map(|m| m.as_str().trim()) else {
                    continue;
                };
                if let Ok(value) = serde_json::from_str::<Value>(raw) {
                    collect_from_json(
                        &value,
                        page_url,
                        &mut title,
                        &mut description,
                        &mut cover_url,
                        &mut urls,
                    );
                }
            }
        }

        let mut deduped_urls = Vec::new();
        for candidate in urls {
            if !deduped_urls.contains(&candidate) {
                deduped_urls.push(candidate);
            }
        }

        let m3u8_url = deduped_urls
            .iter()
            .find(|candidate| classify_media_url(candidate) == "m3u8")
            .cloned();
        let dash_url = deduped_urls
            .iter()
            .find(|candidate| classify_media_url(candidate) == "dash")
            .cloned();
        let mp4_url = deduped_urls
            .iter()
            .find(|candidate| classify_media_url(candidate) == "mp4")
            .cloned();
        let download_url = deduped_urls
            .iter()
            .find(|candidate| {
                Some(candidate.as_str()) != m3u8_url.as_deref()
                    && Some(candidate.as_str()) != dash_url.as_deref()
                    && Some(candidate.as_str()) != mp4_url.as_deref()
            })
            .cloned();

        if m3u8_url.is_none() && dash_url.is_none() && mp4_url.is_none() && download_url.is_none() {
            return None;
        }

        let mut video = VideoData {
            title: title.unwrap_or_else(|| "Unknown Video".to_string()),
            video_id: format!("{:x}", Md5::digest(page_url.as_bytes())),
            platform: self
                .detect_platform(page_url)
                .unwrap_or("generic")
                .to_string(),
            m3u8_url,
            mp4_url,
            dash_url,
            download_url,
            cover_url,
            duration: 0,
            description: description.unwrap_or_default(),
        };
        self.enrich_generic_video(page_url, html, &mut video);
        Some(video)
    }

    fn extract_video_id(&self, url: &str, pattern: &str) -> Option<String> {
        Regex::new(pattern)
            .ok()
            .and_then(|re| re.captures(url))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().to_string())
    }

    fn extract_video_id_from_patterns(&self, url: &str, patterns: &[&str]) -> Option<String> {
        patterns
            .iter()
            .find_map(|pattern| self.extract_video_id(url, pattern))
    }

    fn extract_title(&self, html: &str, video_id: &str) -> String {
        Regex::new(r"<title>([^<]+)</title>")
            .ok()
            .and_then(|re| re.captures(html))
            .and_then(|caps| caps.get(1))
            .map(|m| {
                let title = m.as_str().trim();
                // 清理标题
                let title = regex::Regex::new(r"\s*-?\s*优酷\s*$")
                    .ok()
                    .map(|re| re.replace_all(title, ""))
                    .map(|s| s.to_string())
                    .unwrap_or_else(|| title.to_string());
                title
            })
            .unwrap_or_else(|| format!("Video {}", video_id))
    }

    fn extract_video_data(&self, html: &str) -> std::collections::HashMap<String, String> {
        let mut data = std::collections::HashMap::new();

        // 查找 M3U8
        if let Some(m3u8) = Regex::new(r#"(https?://[^"\s]+\.m3u8[^"\s]*)"#)
            .ok()
            .and_then(|re| re.captures(html))
            .and_then(|caps| caps.get(1))
        {
            data.insert("m3u8_url".to_string(), m3u8.as_str().to_string());
        }

        // 查找 DASH
        if let Some(dash) = Regex::new(r#"(https?://[^"\s]+(?:\.mpd|/dash[^"\s]*)[^"\s]*)"#)
            .ok()
            .and_then(|re| re.captures(html))
            .and_then(|caps| caps.get(1))
        {
            data.insert("dash_url".to_string(), dash.as_str().to_string());
        }

        // 查找 MP4
        if let Some(mp4) =
            Regex::new(r#""(?:url|playAddr|play_api|playUrl)"\s*:\s*"([^"]+\.mp4[^"]*)""#)
                .ok()
                .and_then(|re| re.captures(html))
                .and_then(|caps| caps.get(1))
        {
            data.insert(
                "mp4_url".to_string(),
                mp4.as_str().replace("\\u002F", "/").replace("\\/", "/"),
            );
        }

        // 查找封面
        if let Some(cover) = Regex::new(
            r#"(?is)(?:<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["'])|(?:"(?:poster|cover|pic|thumbnailUrl|dynamic_cover|originCover)"\s*:\s*"([^"]+)")"#,
        )
            .ok()
            .and_then(|re| re.captures(html))
            .and_then(|caps| caps.get(1).or_else(|| caps.get(2)))
        {
            data.insert("cover_url".to_string(), cover.as_str().to_string());
        }

        data
    }

    fn enrich_generic_video(&self, page_url: &str, source_text: &str, video: &mut VideoData) {
        if let Some(platform) = self.detect_platform(page_url) {
            if video.platform == "generic" || video.platform == "generic-artifact" {
                video.platform = platform.to_string();
            }
            if let Some(video_id) = self.infer_video_id(page_url, platform) {
                video.video_id = video_id;
            }
        }

        if video.description.trim().is_empty() {
            video.description = Regex::new(r#""(?:desc|description)"\s*:\s*"([^"]+)""#)
                .ok()
                .and_then(|re| re.captures(source_text))
                .and_then(|caps| caps.get(1))
                .map(|m| clean_text(m.as_str()))
                .unwrap_or_default();
        }

        if video.duration == 0 {
            video.duration = Regex::new(r#""duration"\s*:\s*(\d+)"#)
                .ok()
                .and_then(|re| re.captures(source_text))
                .and_then(|caps| caps.get(1))
                .and_then(|m| m.as_str().parse().ok())
                .unwrap_or(0);
        }
    }

    fn infer_video_id(&self, page_url: &str, platform: &str) -> Option<String> {
        match platform {
            "youku" => self.extract_video_id(page_url, r"id_(?:X)?([a-zA-Z0-9=]+)"),
            "iqiyi" => self.extract_video_id_from_patterns(
                page_url,
                &[
                    r"/v_([A-Za-z0-9]+)\.html",
                    r"/play/([A-Za-z0-9]+)",
                    r"[?&]curid=([^&]+)",
                ],
            ),
            "tencent" => self.extract_video_id_from_patterns(
                page_url,
                &[
                    r"/x/cover/[^/]+/([A-Za-z0-9]+)\.html",
                    r"/x/page/([A-Za-z0-9]+)\.html",
                    r"/x/([A-Za-z0-9]+)\.html",
                    r"[?&]vid=([A-Za-z0-9]+)",
                ],
            ),
            "bilibili" => self.extract_video_id(page_url, r"(BV[A-Za-z0-9]+)"),
            "douyin" => self.extract_video_id(page_url, r"/video/([0-9]+)"),
            _ => None,
        }
    }
}

impl Default for UniversalParser {
    fn default() -> Self {
        Self::new().unwrap()
    }
}

fn merge_video_data(primary: Option<VideoData>, fallback: Option<VideoData>) -> Option<VideoData> {
    match (primary, fallback) {
        (None, None) => None,
        (Some(primary), None) => Some(primary),
        (None, Some(fallback)) => Some(fallback),
        (Some(mut primary), Some(fallback)) => {
            if primary.title.trim().is_empty() || primary.title == "Unknown Video" {
                primary.title = fallback.title;
            }
            if primary.description.trim().is_empty() {
                primary.description = fallback.description;
            }
            primary.m3u8_url = primary.m3u8_url.or(fallback.m3u8_url);
            primary.mp4_url = primary.mp4_url.or(fallback.mp4_url);
            primary.dash_url = primary.dash_url.or(fallback.dash_url);
            primary.download_url = primary.download_url.or(fallback.download_url);
            primary.cover_url = primary.cover_url.or(fallback.cover_url);
            Some(primary)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Read, Write};
    use std::net::TcpListener;
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::sync::Arc;
    use std::thread;
    use std::time::Duration;

    struct MockServer {
        url: String,
        shutdown: Arc<AtomicBool>,
        handle: Option<thread::JoinHandle<()>>,
    }

    impl Drop for MockServer {
        fn drop(&mut self) {
            self.shutdown.store(true, Ordering::SeqCst);
            let _ = std::net::TcpStream::connect(self.url.replace("http://", ""));
            if let Some(handle) = self.handle.take() {
                let _ = handle.join();
            }
        }
    }

    fn start_mock_server(body: &'static str) -> MockServer {
        let listener = TcpListener::bind("127.0.0.1:0").expect("listener should bind");
        listener
            .set_nonblocking(true)
            .expect("listener should be non-blocking");
        let addr = listener.local_addr().expect("local addr");
        let shutdown = Arc::new(AtomicBool::new(false));
        let flag = shutdown.clone();

        let handle = thread::spawn(move || {
            while !flag.load(Ordering::SeqCst) {
                match listener.accept() {
                    Ok((mut stream, _)) => {
                        let mut buffer = [0_u8; 2048];
                        let _ = stream.read(&mut buffer);
                        let response = format!(
                            "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                            body.len(),
                            body
                        );
                        let _ = stream.write_all(response.as_bytes());
                        let _ = stream.flush();
                    }
                    Err(err) if err.kind() == std::io::ErrorKind::WouldBlock => {
                        thread::sleep(Duration::from_millis(20));
                    }
                    Err(_) => break,
                }
            }
        });

        MockServer {
            url: format!("http://{}", addr),
            shutdown,
            handle: Some(handle),
        }
    }

    #[test]
    fn test_parser() {
        let parser = UniversalParser::new().unwrap();

        // 注意：这是示例测试，需要有效的 URL
        // let video = parser.parse("https://v.youku.com/...");
        // assert!(video.is_some());
    }

    #[test]
    fn video_parser_supports_bilibili_and_douyin_html() {
        let bili = start_mock_server(
            r#"<html><head><title>示例 B站视频 - 哔哩哔哩</title></head><body><script>{"duration":321,"cover":"https://img.example.com/cover.jpg","desc":"B站描述","baseUrl":"https://media.example.com/video.m4s"}</script></body></html>"#,
        );
        let douyin = start_mock_server(
            r#"<html><head><title>示例抖音 - 抖音</title></head><body><script>{"duration":18,"dynamic_cover":"https://img.example.com/dy.jpg","desc":"抖音描述","playAddr":"https:\/\/media.example.com\/douyin.mp4"}</script></body></html>"#,
        );

        let parser = UniversalParser::new().unwrap();

        let bilibili = parser
            .parse(&(bili.url.clone() + "/video/BV1demo"))
            .expect("bilibili parse should succeed");
        assert_eq!(bilibili.platform, "bilibili");
        assert_eq!(bilibili.video_id, "BV1demo");
        assert_eq!(bilibili.duration, 321);
        assert_eq!(
            bilibili.dash_url.as_deref(),
            Some("https://media.example.com/video.m4s")
        );

        let douyin_video = parser
            .parse(&(douyin.url.clone() + "/video/123456789"))
            .expect("douyin parse should succeed");
        assert_eq!(douyin_video.platform, "douyin");
        assert_eq!(douyin_video.video_id, "123456789");
        assert_eq!(douyin_video.duration, 18);
        assert_eq!(
            douyin_video.mp4_url.as_deref(),
            Some("https://media.example.com/douyin.mp4")
        );
    }

    #[test]
    fn video_parser_supports_iqiyi_and_tencent_html() {
        let iqiyi = start_mock_server(
            r#"<html><head><title>示例爱奇艺 - 爱奇艺</title><meta property="og:image" content="https://img.example.com/iqiyi-cover.jpg" /></head><body><script>{"duration":88,"desc":"爱奇艺描述","m3u8Url":"https://media.example.com/master.m3u8","dashUrl":"https://media.example.com/manifest.mpd"}</script></body></html>"#,
        );
        let tencent = start_mock_server(
            r#"<html><head><title>示例腾讯视频 - 腾讯视频</title></head><body><script>{"duration":45,"desc":"腾讯描述","pic":"https://img.example.com/tencent-cover.jpg","url":"https://media.example.com/tencent.mp4","dashUrl":"https://media.example.com/tencent.mpd"}</script></body></html>"#,
        );

        let parser = UniversalParser::new().unwrap();

        let iqiyi_video = parser
            .parse(&(iqiyi.url.clone() + "/v_19rrdemo.html"))
            .expect("iqiyi parse should succeed");
        assert_eq!(iqiyi_video.platform, "iqiyi");
        assert_eq!(iqiyi_video.video_id, "19rrdemo");
        assert_eq!(iqiyi_video.duration, 88);
        assert_eq!(
            iqiyi_video.m3u8_url.as_deref(),
            Some("https://media.example.com/master.m3u8")
        );
        assert_eq!(
            iqiyi_video.dash_url.as_deref(),
            Some("https://media.example.com/manifest.mpd")
        );
        assert_eq!(
            iqiyi_video.cover_url.as_deref(),
            Some("https://img.example.com/iqiyi-cover.jpg")
        );

        let tencent_video = parser
            .parse(&(tencent.url.clone() + "/x/page/demo123.html"))
            .expect("tencent parse should succeed");
        assert_eq!(tencent_video.platform, "tencent");
        assert_eq!(tencent_video.video_id, "demo123");
        assert_eq!(tencent_video.duration, 45);
        assert_eq!(
            tencent_video.mp4_url.as_deref(),
            Some("https://media.example.com/tencent.mp4")
        );
        assert_eq!(
            tencent_video.dash_url.as_deref(),
            Some("https://media.example.com/tencent.mpd")
        );
        assert_eq!(
            tencent_video.cover_url.as_deref(),
            Some("https://img.example.com/tencent-cover.jpg")
        );
    }

    #[test]
    fn universal_parser_discovers_video_object_and_manifest_urls() {
        let parser = UniversalParser::new().unwrap();
        let html = r#"
        <html>
          <head>
            <title>Fallback Title</title>
            <meta property="og:video" content="/streams/master.m3u8" />
            <meta property="og:image" content="/cover.jpg" />
            <script type="application/ld+json">
              {
                "@context": "https://schema.org",
                "@type": "VideoObject",
                "name": "Universal Fixture",
                "description": "fixture description",
                "contentUrl": "https://cdn.example.com/video.mp4",
                "thumbnailUrl": "https://cdn.example.com/poster.png"
              }
            </script>
          </head>
          <body>
            <video><source src="/dash/manifest.mpd" /></video>
          </body>
        </html>
        "#;

        let video = parser
            .universal_parse_html("https://example.com/watch/demo", html)
            .expect("generic parse should succeed");

        assert_eq!(video.title, "Universal Fixture");
        assert_eq!(video.description, "fixture description");
        assert_eq!(
            video.m3u8_url.as_deref(),
            Some("https://example.com/streams/master.m3u8")
        );
        assert_eq!(
            video.dash_url.as_deref(),
            Some("https://example.com/dash/manifest.mpd")
        );
        assert_eq!(
            video.mp4_url.as_deref(),
            Some("https://cdn.example.com/video.mp4")
        );
        assert_eq!(
            video.cover_url.as_deref(),
            Some("https://example.com/cover.jpg")
        );
    }

    #[test]
    fn universal_parser_discovers_media_from_artifact_payloads() {
        let parser = UniversalParser::new().unwrap();
        let artifacts = vec![
            r#"{"player":{"videoUrl":"https://cdn.example.com/direct.mp4","dashUrl":"https://cdn.example.com/manifest.mpd"}}"#
                .to_string(),
        ];

        let video = parser
            .parse_artifacts("https://example.com/watch/demo", None, &artifacts)
            .expect("artifact parse should succeed");

        assert_eq!(
            video.mp4_url.as_deref(),
            Some("https://cdn.example.com/direct.mp4")
        );
        assert_eq!(
            video.dash_url.as_deref(),
            Some("https://cdn.example.com/manifest.mpd")
        );
    }
}
