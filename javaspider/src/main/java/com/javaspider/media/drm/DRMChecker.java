package com.javaspider.media.drm;

import java.util.*;
import java.util.regex.*;

/**
 * DRM 检测器
 * 检测视频是否受 DRM 保护
 */
public class DRMChecker {
    
    /**
     * DRM 类型枚举
     */
    public enum DRMType {
        NONE("无保护"),
        WIDEVINE("Google Widevine"),
        PLAYREADY("Microsoft PlayReady"),
        FAIRPLAY("Apple FairPlay"),
        MARLIN("Marlin"),
        CHINESEDRM("中国 DRM (ChinaDRM)"),
        UNKNOWN("未知");
        
        private final String description;
        
        DRMType(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
    }
    
    /**
     * 检测结果
     */
    public static class DRMResult {
        private boolean isProtected;
        private DRMType drmType;
        private String licenseUrl;
        private List<String> detectedSystems;
        
        public DRMResult() {
            this.isProtected = false;
            this.drmType = DRMType.NONE;
            this.detectedSystems = new ArrayList<>();
        }
        
        public boolean isProtected() { return isProtected; }
        public void setProtected(boolean p) { this.isProtected = p; }
        
        public DRMType getDrmType() { return drmType; }
        public void setDrmType(DRMType t) { this.drmType = t; }
        
        public String getLicenseUrl() { return licenseUrl; }
        public void setLicenseUrl(String u) { this.licenseUrl = u; }
        
        public List<String> getDetectedSystems() { return detectedSystems; }
        public void addDetectedSystem(String s) { this.detectedSystems.add(s); }
        
        @Override
        public String toString() {
            if (!isProtected) {
                return "No DRM protection detected";
            }
            return "DRM Protected: " + drmType.getDescription() + 
                   (licenseUrl != null ? " (License: " + licenseUrl + ")" : "");
        }
    }
    
    /**
     * 检测 HTML 内容中的 DRM 信息
     */
    public DRMResult checkFromHTML(String html) {
        DRMResult result = new DRMResult();
        
        // 检测 Widevine
        if (html.contains("com.widevine.alpha") || html.contains("widevine")) {
            result.setProtected(true);
            result.addDetectedSystem("Widevine");
            result.setDrmType(DRMType.WIDEVINE);
        }
        
        // 检测 PlayReady
        if (html.contains("com.microsoft.playready") || html.contains("playready")) {
            result.setProtected(true);
            result.addDetectedSystem("PlayReady");
            if (result.getDrmType() == DRMType.NONE) {
                result.setDrmType(DRMType.PLAYREADY);
            }
        }
        
        // 检测 FairPlay
        if (html.contains("com.apple.fps") || html.contains("fairplay")) {
            result.setProtected(true);
            result.addDetectedSystem("FairPlay");
            if (result.getDrmType() == DRMType.NONE) {
                result.setDrmType(DRMType.FAIRPLAY);
            }
        }
        
        // 检测许可证 URL
        Pattern licensePattern = Pattern.compile("\"(https?://[^\"]*license[^\"]*)\"");
        Matcher matcher = licensePattern.matcher(html);
        if (matcher.find()) {
            result.setLicenseUrl(matcher.group(1));
        }
        
        return result;
    }
    
    /**
     * 检测 M3U8 流中的 DRM 信息
     */
    public DRMResult checkFromM3U8(String m3u8Content) {
        DRMResult result = new DRMResult();
        
        // 检测 EXT-X-KEY 标签
        if (m3u8Content.contains("#EXT-X-KEY")) {
            result.setProtected(true);
            
            // 提取 METHOD
            Pattern methodPattern = Pattern.compile("METHOD=([^,]+)");
            Matcher methodMatcher = methodPattern.matcher(m3u8Content);
            if (methodMatcher.find()) {
                String method = methodMatcher.group(1);
                if ("AES-128".equals(method)) {
                    result.setDrmType(DRMType.UNKNOWN);
                    result.addDetectedSystem("AES-128");
                } else if ("SAMPLE-AES".equals(method)) {
                    result.setDrmType(DRMType.WIDEVINE);
                    result.addDetectedSystem("SAMPLE-AES");
                }
            }
            
            // 提取 URI (许可证 URL)
            Pattern uriPattern = Pattern.compile("URI=\"([^\"]+)\"");
            Matcher uriMatcher = uriPattern.matcher(m3u8Content);
            if (uriMatcher.find()) {
                result.setLicenseUrl(uriMatcher.group(1));
            }
            
            // 提取 KEYID
            Pattern keyIdPattern = Pattern.compile("KEYID=([^,]+)");
            Matcher keyIdMatcher = keyIdPattern.matcher(m3u8Content);
            if (keyIdMatcher.find()) {
                result.addDetectedSystem("KEYID: " + keyIdMatcher.group(1));
            }
        }
        
        return result;
    }
    
    /**
     * 检测 DASH MPD 中的 DRM 信息
     */
    public DRMResult checkFromMPD(String mpdContent) {
        DRMResult result = new DRMResult();
        
        // 检测 ContentProtection 元素
        if (mpdContent.contains("<ContentProtection")) {
            result.setProtected(true);
            
            // 检测 Widevine
            if (mpdContent.contains("widevine")) {
                result.addDetectedSystem("Widevine");
                result.setDrmType(DRMType.WIDEVINE);
            }
            
            // 检测 PlayReady
            if (mpdContent.contains("playready")) {
                result.addDetectedSystem("PlayReady");
                if (result.getDrmType() == DRMType.NONE) {
                    result.setDrmType(DRMType.PLAYREADY);
                }
            }
            
            // 检测许可证 URL
            Pattern licensePattern = Pattern.compile("ms:laurl.*?licenseUrl=\"([^\"]+)\"");
            Matcher matcher = licensePattern.matcher(mpdContent);
            if (matcher.find()) {
                result.setLicenseUrl(matcher.group(1));
            }
        }
        
        return result;
    }
    
    /**
     * 根据 URL 检测 DRM
     */
    public DRMResult checkFromURL(String url) {
        DRMResult result = new DRMResult();
        
        // 根据 URL 特征判断
        if (url.contains("widevine")) {
            result.setProtected(true);
            result.setDrmType(DRMType.WIDEVINE);
        } else if (url.contains("playready")) {
            result.setProtected(true);
            result.setDrmType(DRMType.PLAYREADY);
        } else if (url.contains("fairplay")) {
            result.setProtected(true);
            result.setDrmType(DRMType.FAIRPLAY);
        }
        
        return result;
    }
    
    /**
     * 打印检测报告
     */
    public void printReport(DRMResult result) {
        System.out.println("========== DRM Check Report ==========");
        System.out.println(result);
        
        if (!result.getDetectedSystems().isEmpty()) {
            System.out.println("\nDetected Systems:");
            for (String system : result.getDetectedSystems()) {
                System.out.println("  - " + system);
            }
        }
        
        if (result.getLicenseUrl() != null) {
            System.out.println("\nLicense URL: " + result.getLicenseUrl());
        }
        
        System.out.println("======================================");
    }
}
