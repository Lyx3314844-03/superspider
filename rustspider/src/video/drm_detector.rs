//! DRM 检测模块

use std::error::Error;
use regex::Regex;
use serde::{Deserialize, Serialize};

/// DRM 类型
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum DrmType {
    Widevine,
    FairPlay,
    PlayReady,
    ClearKey,
    Aes128,
    SampleAes,
    Unknown,
    None,
}

/// DRM 信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DrmInfo {
    pub drm_type: DrmType,
    pub is_drm_protected: bool,
    pub key_uri: Option<String>,
    pub key_id: Option<String>,
    pub license_url: Option<String>,
    pub kid: Option<String>,
    pub iv: Option<String>,
}

impl Default for DrmInfo {
    fn default() -> Self {
        Self {
            drm_type: DrmType::None,
            is_drm_protected: false,
            key_uri: None,
            key_id: None,
            license_url: None,
            kid: None,
            iv: None,
        }
    }
}

/// DRM 检测器
pub struct DrmDetector;

impl DrmDetector {
    /// 从 M3U8 检测 DRM
    pub fn detect_from_m3u8(content: &str) -> DrmInfo {
        let mut info = DrmInfo::default();

        // 检查加密标签
        let key_re = Regex::new(r"#EXT-X-KEY:(.+)").unwrap();
        
        for caps in key_re.captures_iter(content) {
            let key_line = caps.get(1).unwrap().as_str();

            // METHOD
            if let Some(method) = Self::extract_key_attr(key_line, "METHOD") {
                match method.as_str() {
                    "NONE" => info.drm_type = DrmType::None,
                    "AES-128" => {
                        info.drm_type = DrmType::Aes128;
                        info.is_drm_protected = true;
                    }
                    "SAMPLE-AES" | "SAMPLE-AES-CTR" => {
                        info.drm_type = DrmType::SampleAes;
                        info.is_drm_protected = true;
                    }
                    _ => {}
                }
            }

            // URI
            if let Some(uri) = Self::extract_key_attr(key_line, "URI") {
                info.key_uri = Some(uri.trim_matches('"').to_string());
            }

            // IV
            if let Some(iv) = Self::extract_key_attr(key_line, "IV") {
                info.iv = Some(iv.to_string());
            }

            // KEYFORMAT
            if let Some(format) = Self::extract_key_attr(key_line, "KEYFORMAT") {
                info = Self::detect_from_keyformat(info, &format);
            }
        }

        // 检查 DRM 特征
        if Regex::new(r"(?i)widevine").unwrap().is_match(content) {
            info.drm_type = DrmType::Widevine;
            info.is_drm_protected = true;
        }

        if Regex::new(r"(?i)fairplay").unwrap().is_match(content) {
            info.drm_type = DrmType::FairPlay;
            info.is_drm_protected = true;
        }

        if Regex::new(r"(?i)playready").unwrap().is_match(content) {
            info.drm_type = DrmType::PlayReady;
            info.is_drm_protected = true;
        }

        info
    }

    /// 从 MPD 检测 DRM
    pub fn detect_from_mpd(content: &str) -> DrmInfo {
        let mut info = DrmInfo::default();

        // 检查 ContentProtection
        let protection_re = Regex::new(r"<ContentProtection[^>]*>").unwrap();
        
        for caps in protection_re.captures_iter(content) {
            let protection = caps.get(0).unwrap().as_str();

            // schemeIdUri
            if let Some(scheme) = Self::extract_attr(protection, "schemeIdUri") {
                info = Self::detect_from_scheme(info, &scheme);
            }
        }

        // 检查 PSSH
        if content.contains("<cenc:pssh") || content.contains("<PSSH") {
            info.is_drm_protected = true;
            if info.drm_type == DrmType::None {
                info.drm_type = DrmType::Unknown;
            }
        }

        // 检查 PlayReady
        if content.contains("<mspr:pro") || content.contains("playready") {
            info.drm_type = DrmType::PlayReady;
            info.is_drm_protected = true;
        }

        info
    }

    /// 检查是否可下载
    pub fn is_downloadable(info: &DrmInfo) -> (bool, String) {
        if !info.is_drm_protected {
            return (true, "无 DRM 保护，可直接下载".to_string());
        }

        match info.drm_type {
            DrmType::Aes128 => {
                if info.key_uri.is_some() {
                    (true, format!("AES-128 加密，密钥 URL: {}", info.key_uri.as_ref().unwrap()))
                } else {
                    (false, "AES-128 加密但未找到密钥 URL".to_string())
                }
            }
            DrmType::ClearKey => (true, "ClearKey 加密，可尝试获取密钥".to_string()),
            DrmType::Widevine | DrmType::FairPlay | DrmType::PlayReady => {
                (false, format!("受 {:?} DRM 保护，需要授权", info.drm_type))
            }
            _ => (false, format!("未知 DRM 类型：{:?}", info.drm_type)),
        }
    }

    fn extract_key_attr(line: &str, attr: &str) -> Option<String> {
        let pattern = format!(r"{}=([^,\s]+)", attr);
        Regex::new(&pattern).ok()
            .and_then(|re| re.captures(line))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().to_string())
    }

    fn extract_attr(line: &str, attr: &str) -> Option<String> {
        let pattern = format!(r#"{}="([^"]+)""#, attr);
        Regex::new(&pattern).ok()
            .and_then(|re| re.captures(line))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().to_string())
    }

    fn detect_from_keyformat(mut info: DrmInfo, key_format: &str) -> DrmInfo {
        let format = key_format.to_lowercase();

        if format.contains("widevine") {
            info.drm_type = DrmType::Widevine;
            info.is_drm_protected = true;
        } else if format.contains("fairplay") || format.contains("fps") {
            info.drm_type = DrmType::FairPlay;
            info.is_drm_protected = true;
        } else if format.contains("playready") {
            info.drm_type = DrmType::PlayReady;
            info.is_drm_protected = true;
        } else if format.contains("clearkey") {
            info.drm_type = DrmType::ClearKey;
            info.is_drm_protected = true;
        }

        info
    }

    fn detect_from_scheme(mut info: DrmInfo, scheme: &str) -> DrmInfo {
        let scheme = scheme.to_lowercase();

        if scheme.contains("widevine") {
            info.drm_type = DrmType::Widevine;
            info.is_drm_protected = true;
        } else if scheme.contains("fairplay") || scheme.contains("fps") {
            info.drm_type = DrmType::FairPlay;
            info.is_drm_protected = true;
        } else if scheme.contains("playready") {
            info.drm_type = DrmType::PlayReady;
            info.is_drm_protected = true;
        }

        info
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_drm_detection() {
        let test_m3u8 = r#"
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-KEY:METHOD=AES-128,URI="https://example.com/key.key",IV=0x1234
#EXTINF:10.0,
segment0.ts
#EXT-X-ENDLIST
"#;

        let info = DrmDetector::detect_from_m3u8(test_m3u8);
        assert_eq!(info.drm_type, DrmType::Aes128);
        assert!(info.is_drm_protected);
        assert!(info.key_uri.is_some());
    }
}
