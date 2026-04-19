package com.javaspider.core;

import com.javaspider.proxy.Proxy;
import lombok.Data;
import lombok.experimental.Accessors;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Site - 站点配置
 * 
 * 吸收 webmagic Site 设计，支持链式调用
 * 集成反爬虫、AI 提取、代理等高级功能
 * 
 * @author Lan
 * @version 2.0.0
 * @since 2026-03-20
 */
@Data
@Accessors(chain = true)
public class Site {

    /**
     * 创建一个新的 Site 实例 (链式调用)
     */
    public static Site me() {
        return new Site();
    }

    // ========== 基础配置 ==========
    
    /**
     * 域名
     */
    private String domain;
    
    /**
     * 起始 URL
     */
    private String startUrl;
    
    /**
     * User-Agent
     */
    private String userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";
    
    /**
     * 请求头
     */
    private Map<String, String> headers = new HashMap<>();
    
    /**
     * Cookie
     */
    private Map<String, Map<String, String>> cookies = new LinkedHashMap<>();
    
    // ========== 重试配置 ==========
    
    /**
     * 重试次数
     */
    private int retryTimes = 3;
    
    /**
     * 重试间隔 (毫秒)
     */
    private int retrySleep = 1000;
    
    // ========== 超时配置 ==========
    
    /**
     * 请求超时 (毫秒)
     */
    private int timeout = 30000;
    
    /**
     * 连接超时 (毫秒)
     */
    private int connectTimeout = 10000;
    
    /**
     * Socket 超时 (毫秒)
     */
    private int socketTimeout = 30000;
    
    // ========== 代理配置 ==========
    
    /**
     * 代理主机
     */
    private String proxyHost;
    
    /**
     * 代理端口
     */
    private int proxyPort;
    
    /**
     * 代理用户名
     */
    private String proxyUsername;
    
    /**
     * 代理密码
     */
    private String proxyPassword;
    
    /**
     * 代理池
     */
    private java.util.List<Proxy> proxyPool;
    
    // ========== 反爬虫配置 ==========
    
    /**
     * 轮换 User-Agent
     */
    private boolean rotateUserAgent = false;
    
    /**
     * 轮换代理
     */
    private boolean rotateProxy = false;
    
    /**
     * 解决验证码
     */
    private boolean solveCaptcha = false;
    
    /**
     * 绕过 Cloudflare
     */
    private boolean bypassCloudflare = false;
    
    /**
     * 绕过 Akamai
     */
    private boolean bypassAkamai = false;
    
    /**
     * 绕过 DataDome
     */
    private boolean bypassDataDome = false;
    
    // ========== AI 配置 ==========
    
    /**
     * 使用 AI 提取
     */
    private boolean useAIExtraction = false;
    
    /**
     * LLM API Key
     */
    private String llmApiKey;
    
    /**
     * LLM 模型
     */
    private String llmModel = "gpt-5.2";
    
    /**
     * LLM API URL
     */
    private String llmApiUrl = "https://api.openai.com/v1/chat/completions";
    
    // ========== 下载配置 ==========
    
    /**
     * 下载延迟 (毫秒)
     */
    private int downloadDelay = 1000;

    /**
     * 是否遵守 robots.txt
     */
    private boolean respectRobotsTxt = true;

    /**
     * robots.txt 缓存时间 (毫秒)
     */
    private long robotsCacheTimeoutMs = 3600_000L;
    
    /**
     * 随机下载延迟范围 (毫秒)
     */
    private int[] randomDownloadDelayRange;
    
    /**
     * 最大下载线程数
     */
    private int maxDownloadThreads = 1;
    
    // ========== 编码配置 ==========
    
    /**
     * 字符编码
     */
    private String charset = "UTF-8";
    
    /**
     * 自动检测编码
     */
    private boolean autoDetectCharset = true;
    
    // ========== User-Agent 列表 ==========
    
    private static final String[] USER_AGENTS = {
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    };
    
    // ========== 链式调用方法 ==========
    
    /**
     * 添加 Cookie
     * @param domain 域名
     * @param name 名称
     * @param value 值
     * @return this
     */
    public Site addCookie(String domain, String name, String value) {
        cookies.computeIfAbsent(domain, k -> new LinkedHashMap<>()).put(name, value);
        return this;
    }
    
    /**
     * 添加 Cookie
     * @param name 名称
     * @param value 值
     * @return this
     */
    public Site addCookie(String name, String value) {
        return addCookie(domain, name, value);
    }
    
    /**
     * 添加请求头
     * @param key 键
     * @param value 值
     * @return this
     */
    public Site addHeader(String key, String value) {
        headers.put(key, value);
        return this;
    }
    
    /**
     * 设置 User-Agent 轮换
     * @param rotate 是否轮换
     * @return this
     */
    public Site rotateUserAgent(boolean rotate) {
        this.rotateUserAgent = rotate;
        return this;
    }
    
    /**
     * 设置代理轮换
     * @param rotate 是否轮换
     * @return this
     */
    public Site rotateProxy(boolean rotate) {
        this.rotateProxy = rotate;
        return this;
    }
    
    /**
     * 启用验证码识别
     * @param solve 是否解决
     * @return this
     */
    public Site solveCaptcha(boolean solve) {
        this.solveCaptcha = solve;
        return this;
    }
    
    /**
     * 启用 Cloudflare 绕过
     * @param bypass 是否绕过
     * @return this
     */
    public Site bypassCloudflare(boolean bypass) {
        this.bypassCloudflare = bypass;
        return this;
    }
    
    /**
     * 启用 Akamai 绕过
     * @param bypass 是否绕过
     * @return this
     */
    public Site bypassAkamai(boolean bypass) {
        this.bypassAkamai = bypass;
        return this;
    }
    
    /**
     * 启用 DataDome 绕过
     * @param bypass 是否绕过
     * @return this
     */
    public Site bypassDataDome(boolean bypass) {
        this.bypassDataDome = bypass;
        return this;
    }
    
    /**
     * 启用 AI 提取
     * @param use 是否使用
     * @param apiKey API Key
     * @param model 模型
     * @return this
     */
    public Site useAIExtraction(boolean use, String apiKey, String model) {
        this.useAIExtraction = use;
        this.llmApiKey = apiKey;
        this.llmModel = model;
        return this;
    }
    
    /**
     * 设置代理
     * @param host 主机
     * @param port 端口
     * @return this
     */
    public Site proxy(String host, int port) {
        this.proxyHost = host;
        this.proxyPort = port;
        return this;
    }
    
    /**
     * 设置代理认证
     * @param username 用户名
     * @param password 密码
     * @return this
     */
    public Site proxyAuth(String username, String password) {
        this.proxyUsername = username;
        this.proxyPassword = password;
        return this;
    }
    
    /**
     * 设置下载延迟
     * @param delay 延迟 (毫秒)
     * @return this
     */
    public Site downloadDelay(int delay) {
        this.downloadDelay = delay;
        return this;
    }
    
    /**
     * 设置随机下载延迟
     * @param min 最小值 (毫秒)
     * @param max 最大值 (毫秒)
     * @return this
     */
    public Site randomDownloadDelay(int min, int max) {
        this.randomDownloadDelayRange = new int[]{min, max};
        return this;
    }
    
    /**
     * 获取随机 User-Agent
     * @return User-Agent
     */
    public String getRandomUserAgent() {
        if (USER_AGENTS.length == 0) {
            return userAgent;
        }
        int index = (int) (Math.random() * USER_AGENTS.length);
        return USER_AGENTS[index];
    }
    
    /**
     * 获取当前 User-Agent
     * @return User-Agent
     */
    public String getCurrentUserAgent() {
        return rotateUserAgent ? getRandomUserAgent() : userAgent;
    }
    
    /**
     * 克隆站点配置
     * @return 克隆的站点配置
     */
    @Override
    public Site clone() {
        try {
            Site site = (Site) super.clone();
            site.headers = new HashMap<>(this.headers);
            site.cookies = new LinkedHashMap<>(this.cookies);
            return site;
        } catch (CloneNotSupportedException e) {
            throw new RuntimeException("Clone not supported", e);
        }
    }
    
    /**
     * 创建 Site 实例
     * @return Site 实例
     */
    public static Site create() {
        return new Site();
    }
    
    /**
     * 创建 Site 实例并设置域名
     * @param domain 域名
     * @return Site 实例
     */
    public static Site of(String domain) {
        Site site = new Site();
        site.setDomain(domain);
        return site;
    }
}
