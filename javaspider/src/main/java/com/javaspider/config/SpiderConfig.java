package com.javaspider.config;

import java.io.IOException;
import java.io.InputStream;
import java.util.Properties;

/**
 * 蜘蛛配置加载器
 */
public class SpiderConfig {
    
    private static final Properties props = new Properties();
    private static boolean loaded = false;
    
    static {
        try (InputStream is = SpiderConfig.class.getResourceAsStream("/spider.properties")) {
            if (is != null) {
                props.load(is);
                loaded = true;
            }
        } catch (IOException e) {
            System.err.println("Failed to load spider.properties: " + e.getMessage());
        }
    }
    
    /**
     * 获取字符串配置
     */
    public static String getString(String key, String defaultValue) {
        return loaded ? props.getProperty(key, defaultValue) : defaultValue;
    }
    
    /**
     * 获取整数配置
     */
    public static int getInt(String key, int defaultValue) {
        try {
            return loaded ? Integer.parseInt(props.getProperty(key)) : defaultValue;
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }
    
    /**
     * 获取布尔配置
     */
    public static boolean getBoolean(String key, boolean defaultValue) {
        try {
            return loaded ? Boolean.parseBoolean(props.getProperty(key)) : defaultValue;
        } catch (Exception e) {
            return defaultValue;
        }
    }
    
    /**
     * 获取长整数配置
     */
    public static long getLong(String key, long defaultValue) {
        try {
            return loaded ? Long.parseLong(props.getProperty(key)) : defaultValue;
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }
    
    // ========== 便捷方法 ==========
    
    public static int getThreads() {
        return getInt("spider.threads", 5);
    }
    
    public static int getRetryTimes() {
        return getInt("spider.retry.times", 3);
    }
    
    public static int getRetrySleep() {
        return getInt("spider.retry.sleep", 1000);
    }
    
    public static long getTimeout() {
        return getLong("spider.timeout", 30000L);
    }
    
    public static String getDownloadDir() {
        return getString("download.dir", "./downloads");
    }
    
    public static int getMaxDownloadCount() {
        return getInt("download.max.count", 10);
    }
    
    public static boolean isDownloadOverwrite() {
        return getBoolean("download.overwrite", false);
    }
    
    public static boolean isProxyEnabled() {
        return getBoolean("proxy.enabled", false);
    }
    
    public static String getProxyHost() {
        return getString("proxy.host", "");
    }
    
    public static int getProxyPort() {
        return getInt("proxy.port", 0);
    }
    
    public static String getBrowserType() {
        return getString("browser.type", "chrome");
    }
    
    public static boolean isBrowserHeadless() {
        return getBoolean("browser.headless", true);
    }
    
    public static long getBrowserPageLoadTimeout() {
        return getLong("browser.pageLoadTimeout", 30000L);
    }
    
    public static String getRedisHost() {
        return getString("redis.host", "localhost");
    }
    
    public static int getRedisPort() {
        return getInt("redis.port", 6379);
    }
    
    public static boolean isApiEnabled() {
        return getBoolean("api.enabled", false);
    }
    
    public static int getApiPort() {
        return getInt("api.port", 8080);
    }
}
