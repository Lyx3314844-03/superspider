package com.javaspider.config;

import org.yaml.snakeyaml.Yaml;
import org.yaml.snakeyaml.constructor.Constructor;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;

/**
 * Spider 配置管理器
 * 支持 YAML 和 Properties 格式配置文件
 */
public class SpiderConfigManager {
    
    private static final String DEFAULT_CONFIG_FILE = "spider-config.yaml";
    private static final String DEFAULT_PROPERTIES_FILE = "spider-config.properties";
    
    private Map<String, Object> config;
    private String configPath;
    
    /**
     * 默认构造函数
     */
    public SpiderConfigManager() {
        this.config = new HashMap<>();
        this.configPath = DEFAULT_CONFIG_FILE;
        loadDefaultConfig();
    }
    
    /**
     * 指定配置文件路径
     * @param configPath 配置文件路径
     */
    public SpiderConfigManager(String configPath) {
        this.config = new HashMap<>();
        this.configPath = configPath;
        loadConfig(configPath);
    }
    
    /**
     * 加载默认配置文件
     */
    private void loadDefaultConfig() {
        File configFile = new File(configPath);
        if (configFile.exists()) {
            loadConfig(configPath);
        } else {
            // 创建默认配置
            createDefaultConfig();
        }
    }
    
    /**
     * 加载配置文件
     * @param path 配置文件路径
     */
    public void loadConfig(String path) {
        try {
            File file = new File(path);
            if (!file.exists()) {
                System.err.println("配置文件不存在：" + path);
                createDefaultConfig();
                return;
            }
            
            Yaml yaml = new Yaml();
            InputStream inputStream = Files.newInputStream(Paths.get(path));
            config = yaml.load(inputStream);
            inputStream.close();
            
            System.out.println("配置加载成功：" + path);
        } catch (Exception e) {
            System.err.println("加载配置文件失败：" + e.getMessage());
            createDefaultConfig();
        }
    }
    
    /**
     * 保存配置文件
     * @param path 保存路径
     */
    public void saveConfig(String path) {
        try {
            Yaml yaml = new Yaml();
            Writer writer = new FileWriter(path);
            yaml.dump(config, writer);
            writer.close();
            
            System.out.println("配置保存成功：" + path);
        } catch (Exception e) {
            System.err.println("保存配置文件失败：" + e.getMessage());
        }
    }
    
    /**
     * 创建默认配置文件
     */
    private void createDefaultConfig() {
        config = new HashMap<>();
        
        // 爬虫配置
        Map<String, Object> spider = new HashMap<>();
        spider.put("name", "MySpider");
        spider.put("threadCount", 5);
        spider.put("maxDepth", 5);
        spider.put("maxRequests", 10000);
        spider.put("retryTimes", 3);
        spider.put("timeout", 30000);
        spider.put("userAgent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36");
        spider.put("rateLimit", 5.0);
        config.put("spider", spider);
        
        // 下载器配置
        Map<String, Object> downloader = new HashMap<>();
        downloader.put("timeout", 30000);
        downloader.put("retryTimes", 3);
        downloader.put("poolConnections", 10);
        downloader.put("poolMaxSize", 50);
        downloader.put("followRedirects", true);
        config.put("downloader", downloader);
        
        // 代理配置
        Map<String, Object> proxy = new HashMap<>();
        proxy.put("enabled", false);
        proxy.put("type", "http");
        proxy.put("host", "127.0.0.1");
        proxy.put("port", 7890);
        proxy.put("username", "");
        proxy.put("password", "");
        config.put("proxy", proxy);
        
        // 媒体下载配置
        Map<String, Object> media = new HashMap<>();
        media.put("enabled", true);
        media.put("outputDir", "./downloads");
        media.put("maxFileSize", 2147483648L);
        media.put("chunkSize", 8192);
        media.put("concurrent", 5);
        media.put("ffmpegPath", "");
        config.put("media", media);
        
        // 浏览器配置
        Map<String, Object> browser = new HashMap<>();
        browser.put("type", "chrome");
        browser.put("headless", true);
        browser.put("timeout", 30000);
        config.put("browser", browser);
        
        // 日志配置
        Map<String, Object> logging = new HashMap<>();
        logging.put("level", "INFO");
        logging.put("file", "logs/spider.log");
        logging.put("maxSize", "10MB");
        logging.put("maxBackups", 3);
        config.put("logging", logging);
        
        // 保存默认配置
        saveConfig(configPath);
    }
    
    /**
     * 获取配置值
     * @param key 配置键
     * @return 配置值
     */
    public Object get(String key) {
        String[] keys = key.split("\\.");
        Map<String, Object> current = config;
        
        for (int i = 0; i < keys.length - 1; i++) {
            Object obj = current.get(keys[i]);
            if (obj instanceof Map) {
                current = (Map<String, Object>) obj;
            } else {
                return null;
            }
        }
        
        return current.get(keys[keys.length - 1]);
    }
    
    /**
     * 获取字符串配置值
     * @param key 配置键
     * @return 配置值
     */
    public String getString(String key) {
        Object value = get(key);
        return value != null ? value.toString() : null;
    }
    
    /**
     * 获取整数配置值
     * @param key 配置键
     * @return 配置值
     */
    public Integer getInt(String key) {
        Object value = get(key);
        if (value instanceof Number) {
            return ((Number) value).intValue();
        }
        return value != null ? Integer.parseInt(value.toString()) : null;
    }
    
    /**
     * 获取长整型配置值
     * @param key 配置键
     * @return 配置值
     */
    public Long getLong(String key) {
        Object value = get(key);
        if (value instanceof Number) {
            return ((Number) value).longValue();
        }
        return value != null ? Long.parseLong(value.toString()) : null;
    }
    
    /**
     * 获取布尔配置值
     * @param key 配置键
     * @return 配置值
     */
    public Boolean getBoolean(String key) {
        Object value = get(key);
        if (value instanceof Boolean) {
            return (Boolean) value;
        }
        return value != null ? Boolean.parseBoolean(value.toString()) : null;
    }
    
    /**
     * 获取双精度浮点配置值
     * @param key 配置键
     * @return 配置值
     */
    public Double getDouble(String key) {
        Object value = get(key);
        if (value instanceof Number) {
            return ((Number) value).doubleValue();
        }
        return value != null ? Double.parseDouble(value.toString()) : null;
    }
    
    /**
     * 设置配置值
     * @param key 配置键
     * @param value 配置值
     */
    public void set(String key, Object value) {
        String[] keys = key.split("\\.");
        Map<String, Object> current = config;
        
        for (int i = 0; i < keys.length - 1; i++) {
            Object obj = current.get(keys[i]);
            if (obj instanceof Map) {
                current = (Map<String, Object>) obj;
            } else {
                Map<String, Object> newMap = new HashMap<>();
                current.put(keys[i], newMap);
                current = newMap;
            }
        }
        
        current.put(keys[keys.length - 1], value);
    }
    
    /**
     * 获取爬虫配置
     * @return 爬虫配置 Map
     */
    public Map<String, Object> getSpiderConfig() {
        return (Map<String, Object>) config.get("spider");
    }
    
    /**
     * 获取下载器配置
     * @return 下载器配置 Map
     */
    public Map<String, Object> getDownloaderConfig() {
        return (Map<String, Object>) config.get("downloader");
    }
    
    /**
     * 获取代理配置
     * @return 代理配置 Map
     */
    public Map<String, Object> getProxyConfig() {
        return (Map<String, Object>) config.get("proxy");
    }
    
    /**
     * 获取媒体配置
     * @return 媒体配置 Map
     */
    public Map<String, Object> getMediaConfig() {
        return (Map<String, Object>) config.get("media");
    }
    
    /**
     * 获取浏览器配置
     * @return 浏览器配置 Map
     */
    public Map<String, Object> getBrowserConfig() {
        return (Map<String, Object>) config.get("browser");
    }
    
    /**
     * 打印配置信息
     */
    public void printConfig() {
        System.out.println("=== Spider 配置 ===");
        Yaml yaml = new Yaml();
        System.out.println(yaml.dump(config));
    }
    
    /**
     * 从 Properties 加载配置
     * @param properties Properties 对象
     */
    public void loadFromProperties(Properties properties) {
        for (String key : properties.stringPropertyNames()) {
            set(key, properties.getProperty(key));
        }
    }
    
    /**
     * 加载 Properties 配置文件
     * @param path 配置文件路径
     */
    public void loadProperties(String path) {
        try {
            Properties properties = new Properties();
            InputStream inputStream = Files.newInputStream(Paths.get(path));
            properties.load(inputStream);
            inputStream.close();
            
            loadFromProperties(properties);
            System.out.println("Properties 配置加载成功：" + path);
        } catch (Exception e) {
            System.err.println("加载 Properties 配置失败：" + e.getMessage());
        }
    }
}
