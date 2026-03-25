package com.javaspider.antibot;

import java.util.*;
import java.security.MessageDigest;
import java.net.*;
import java.io.*;

/**
 * 反反爬处理器
 * 提供多种反反爬策略
 */
public class AntiBotHandler {
    private final List<String> userAgents;
    private final List<String> referers;
    private final List<String> languages;
    private final Random random;
    
    /**
     * 创建反反爬处理器
     */
    public AntiBotHandler() {
        this.random = new Random();
        
        this.userAgents = Arrays.asList(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        );
        
        this.referers = Arrays.asList(
            "https://www.google.com/",
            "https://www.bing.com/",
            "https://www.baidu.com/",
            "https://duckduckgo.com/"
        );
        
        this.languages = Arrays.asList(
            "zh-CN,zh;q=0.9,en;q=0.8",
            "en-US,en;q=0.9",
            "zh-TW,zh;q=0.9",
            "ja-JP,ja;q=0.9"
        );
    }
    
    /**
     * 获取随机请求头
     */
    public Map<String, String> getRandomHeaders() {
        Map<String, String> headers = new HashMap<>();
        
        headers.put("User-Agent", getRandomUserAgent());
        headers.put("Referer", getRandomReferer());
        headers.put("Accept-Language", getRandomLanguage());
        headers.put("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8");
        headers.put("Accept-Encoding", "gzip, deflate, br");
        headers.put("Connection", "keep-alive");
        headers.put("Upgrade-Insecure-Requests", "1");
        headers.put("Cache-Control", "max-age=0");
        
        // 添加隐身请求头
        headers.putAll(getStealthHeaders());
        
        return headers;
    }
    
    /**
     * 获取随机 User-Agent
     */
    public String getRandomUserAgent() {
        return userAgents.get(random.nextInt(userAgents.size()));
    }
    
    /**
     * 获取随机 Referer
     */
    public String getRandomReferer() {
        return referers.get(random.nextInt(referers.size()));
    }
    
    /**
     * 获取随机 Accept-Language
     */
    public String getRandomLanguage() {
        return languages.get(random.nextInt(languages.size()));
    }
    
    /**
     * 获取隐身请求头
     */
    public Map<String, String> getStealthHeaders() {
        Map<String, String> headers = new HashMap<>();
        headers.put("sec-ch-ua", "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\"");
        headers.put("sec-ch-ua-mobile", "?0");
        headers.put("sec-ch-ua-platform", "\"Windows\"");
        headers.put("sec-fetch-dest", "document");
        headers.put("sec-fetch-mode", "navigate");
        headers.put("sec-fetch-site", "none");
        headers.put("sec-fetch-user", "?1");
        return headers;
    }
    
    /**
     * 获取智能延迟
     */
    public long getIntelligentDelay(long baseDelayMs) {
        // 基础延迟
        long delay = baseDelayMs + random.nextInt(2000);
        
        // 随机添加额外延迟（30% 概率）
        if (random.nextDouble() < 0.3) {
            delay += random.nextInt(3000);
        }
        
        // 时间段调整（夜间增加延迟）
        Calendar now = Calendar.getInstance();
        int hour = now.get(Calendar.HOUR_OF_DAY);
        if (hour < 6 || hour > 23) {
            delay = (long) (delay * 1.5);
        }
        
        return delay;
    }
    
    /**
     * 检查是否被封禁
     */
    public boolean isBlocked(String html, int statusCode) {
        List<String> blockedKeywords = Arrays.asList(
            "access denied",
            "blocked",
            "captcha",
            "验证码",
            "封禁",
            "403 forbidden",
            "429 too many requests",
            "request rejected",
            "ip banned"
        );
        
        String htmlLower = html.toLowerCase();
        for (String keyword : blockedKeywords) {
            if (htmlLower.contains(keyword.toLowerCase())) {
                return true;
            }
        }
        
        return statusCode == 403 || statusCode == 429;
    }
    
    /**
     * 绕过 Cloudflare
     */
    public Map<String, String> bypassCloudflare() {
        Map<String, String> headers = new HashMap<>();
        headers.put("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");
        headers.put("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8");
        headers.put("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8");
        headers.put("Connection", "keep-alive");
        headers.put("Upgrade-Insecure-Requests", "1");
        return headers;
    }
    
    /**
     * 绕过 Akamai
     */
    public Map<String, String> bypassAkamai() {
        Map<String, String> headers = new HashMap<>();
        headers.put("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");
        headers.put("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8");
        headers.put("X-Requested-With", "XMLHttpRequest");
        return headers;
    }
    
    /**
     * 生成浏览器指纹
     */
    public String generateFingerprint() {
        try {
            String data = System.currentTimeMillis() + "_" + random.nextDouble();
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] digest = md.digest(data.getBytes());
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (Exception e) {
            return UUID.randomUUID().toString();
        }
    }
    
    /**
     * 轮换代理
     */
    public String rotateProxy(List<String> proxyPool) {
        if (proxyPool.isEmpty()) {
            return null;
        }
        return proxyPool.get(random.nextInt(proxyPool.size()));
    }
    
    /**
     * 解决验证码（需要第三方服务）
     */
    public String solveCaptcha(byte[] captchaImage, String apiKey) {
        // 实际实现需要调用 2Captcha、Anti-Captcha 等第三方服务
        // 这里只是示例
        if (apiKey != null && !apiKey.isEmpty()) {
            // 调用第三方 API
            // ...
        }
        return null;
    }
    
    /**
     * 创建 Cloudflare 绕过器
     */
    public CloudflareBypass createCloudflareBypass() {
        return new CloudflareBypass(this);
    }
    
    /**
     * 创建 Akamai 绕过器
     */
    public AkamaiBypass createAkamaiBypass() {
        return new AkamaiBypass(this);
    }
    
    /**
     * Cloudflare 绕过器
     */
    public static class CloudflareBypass {
        private final AntiBotHandler handler;
        
        public CloudflareBypass(AntiBotHandler handler) {
            this.handler = handler;
        }
        
        public Map<String, String> getHeaders() {
            Map<String, String> headers = handler.bypassCloudflare();
            headers.putAll(handler.getStealthHeaders());
            return headers;
        }
    }
    
    /**
     * Akamai 绕过器
     */
    public static class AkamaiBypass {
        private final AntiBotHandler handler;
        
        public AkamaiBypass(AntiBotHandler handler) {
            this.handler = handler;
        }
        
        public Map<String, String> getHeaders() {
            Map<String, String> headers = handler.bypassAkamai();
            headers.putAll(handler.getStealthHeaders());
            return headers;
        }
    }
}
