package com.javaspider.core;

import lombok.Data;

import java.util.HashMap;
import java.util.Map;

/**
 * Request - 请求对象
 * 
 * 封装 HTTP 请求信息，支持优先级、重试、元数据等功能
 * 
 * @author Lan
 * @version 2.0.0
 * @since 2026-03-20
 */
@Data
public class Request {
    
    /**
     * URL
     */
    private String url;
    
    /**
     * 请求方法
     */
    private String method = "GET";
    
    /**
     * 请求头
     */
    private Map<String, String> headers = new HashMap<>();
    
    /**
     * 请求体
     */
    private byte[] body;
    
    /**
     * Cookie
     */
    private Map<String, String> cookies = new HashMap<>();
    
    /**
     * 请求参数
     */
    private Map<String, String> params = new HashMap<>();
    
    /**
     * 表单数据
     */
    private Map<String, String> formData = new HashMap<>();
    
    /**
     * JSON 数据
     */
    private String jsonBody;
    
    /**
     * 爬虫 ID
     */
    private String spiderId;
    
    /**
     * 优先级 (数值越大优先级越高)
     */
    private int priority = 0;
    
    /**
     * 重试次数
     */
    private int retryCount = 0;
    
    /**
     * 最大重试次数
     */
    private int maxRetryCount = 3;
    
    /**
     * 是否已下载
     */
    private boolean downloaded = false;
    
    /**
     * 下载时间
     */
    private long downloadTime;
    
    /**
     * 创建时间
     */
    private long createTime = System.currentTimeMillis();
    
    /**
     * 过期时间
     */
    private long expireTime;
    
    /**
     * 元数据
     */
    private Map<String, Object> meta = new HashMap<>();
    
    /**
     * 回调处理器
     */
    private String callback;
    
    /**
     * 是否启用 JavaScript
     */
    private boolean enableJavaScript = false;
    
    /**
     * 是否使用代理
     */
    private boolean useProxy = false;
    
    /**
     * 是否跳过
     */
    private boolean skip = false;
    
    /**
     * 来源 URL
     */
    private String referer;
    
    /**
     * 请求 ID
     */
    private String requestId;
    
    /**
     * 构造函数
     */
    public Request() {
    }
    
    /**
     * 构造函数
     * @param url URL
     */
    public Request(String url) {
        this.url = url;
    }
    
    /**
     * 构造函数
     * @param url URL
     * @param method 请求方法
     */
    public Request(String url, String method) {
        this.url = url;
        this.method = method;
    }
    
    // ========== 链式调用方法 ==========
    
    /**
     * 设置请求方法
     * @param method 请求方法
     * @return this
     */
    public Request method(String method) {
        this.method = method;
        return this;
    }
    
    /**
     * 添加请求头
     * @param key 键
     * @param value 值
     * @return this
     */
    public Request header(String key, String value) {
        this.headers.put(key, value);
        return this;
    }
    
    /**
     * 添加多个请求头
     * @param headers 请求头
     * @return this
     */
    public Request headers(Map<String, String> headers) {
        this.headers.putAll(headers);
        return this;
    }
    
    /**
     * 设置 User-Agent
     * @param userAgent User-Agent
     * @return this
     */
    public Request userAgent(String userAgent) {
        this.headers.put("User-Agent", userAgent);
        return this;
    }
    
    /**
     * 设置 Referer
     * @param referer Referer
     * @return this
     */
    public Request referer(String referer) {
        this.headers.put("Referer", referer);
        this.referer = referer;
        return this;
    }
    
    /**
     * 设置 Content-Type
     * @param contentType Content-Type
     * @return this
     */
    public Request contentType(String contentType) {
        this.headers.put("Content-Type", contentType);
        return this;
    }
    
    /**
     * 添加 Cookie
     * @param key 键
     * @param value 值
     * @return this
     */
    public Request cookie(String key, String value) {
        this.cookies.put(key, value);
        return this;
    }
    
    /**
     * 添加请求参数
     * @param key 键
     * @param value 值
     * @return this
     */
    public Request param(String key, String value) {
        this.params.put(key, value);
        return this;
    }
    
    /**
     * 添加表单数据
     * @param key 键
     * @param value 值
     * @return this
     */
    public Request formData(String key, String value) {
        this.formData.put(key, value);
        return this;
    }
    
    /**
     * 设置 JSON 数据
     * @param json JSON 数据
     * @return this
     */
    public Request json(String json) {
        this.jsonBody = json;
        this.contentType("application/json");
        return this;
    }
    
    /**
     * 设置优先级
     * @param priority 优先级
     * @return this
     */
    public Request priority(int priority) {
        this.priority = priority;
        return this;
    }
    
    /**
     * 设置元数据
     * @param key 键
     * @param value 值
     * @return this
     */
    public Request meta(String key, Object value) {
        this.meta.put(key, value);
        return this;
    }
    
    /**
     * 设置回调处理器
     * @param callback 回调处理器名称
     * @return this
     */
    public Request callback(String callback) {
        this.callback = callback;
        return this;
    }
    
    /**
     * 启用 JavaScript
     * @param enable 是否启用
     * @return this
     */
    public Request enableJavaScript(boolean enable) {
        this.enableJavaScript = enable;
        return this;
    }
    
    /**
     * 使用代理
     * @param use 是否使用
     * @return this
     */
    public Request useProxy(boolean use) {
        this.useProxy = use;
        return this;
    }
    
    /**
     * 设置过期时间
     * @param expireTime 过期时间 (毫秒)
     * @return this
     */
    public Request expireTime(long expireTime) {
        this.expireTime = expireTime;
        return this;
    }
    
    /**
     * 设置来源 URL
     * @param referer 来源 URL
     * @return this
     */
    public Request from(String referer) {
        this.referer = referer;
        return this;
    }
    
    /**
     * 设置爬虫 ID
     * @param spiderId 爬虫 ID
     * @return this
     */
    public Request spiderId(String spiderId) {
        this.spiderId = spiderId;
        return this;
    }
    
    /**
     * 检查是否已过期
     * @return 是否已过期
     */
    public boolean isExpired() {
        if (expireTime <= 0) {
            return false;
        }
        return System.currentTimeMillis() > expireTime;
    }
    
    /**
     * 检查是否可以重试
     * @return 是否可以重试
     */
    public boolean canRetry() {
        return retryCount < maxRetryCount;
    }
    
    /**
     * 获取请求方法 (大写)
     * @return 请求方法
     */
    public String getMethodUpperCase() {
        return method.toUpperCase();
    }
    
    /**
     * 判断是否是 GET 请求
     * @return 是否是 GET 请求
     */
    public boolean isGet() {
        return "GET".equalsIgnoreCase(method);
    }
    
    /**
     * 判断是否是 POST 请求
     * @return 是否是 POST 请求
     */
    public boolean isPost() {
        return "POST".equalsIgnoreCase(method);
    }
    
    /**
     * 判断是否是 PUT 请求
     * @return 是否是 PUT 请求
     */
    public boolean isPut() {
        return "PUT".equalsIgnoreCase(method);
    }
    
    /**
     * 判断是否是 DELETE 请求
     * @return 是否是 DELETE 请求
     */
    public boolean isDelete() {
        return "DELETE".equalsIgnoreCase(method);
    }
    
    /**
     * 创建 Request 实例
     * @param url URL
     * @return Request 实例
     */
    public static Request of(String url) {
        return new Request(url);
    }
    
    /**
     * 创建 GET Request 实例
     * @param url URL
     * @return Request 实例
     */
    public static Request get(String url) {
        return new Request(url, "GET");
    }
    
    /**
     * 创建 POST Request 实例
     * @param url URL
     * @return Request 实例
     */
    public static Request post(String url) {
        return new Request(url, "POST");
    }
}
