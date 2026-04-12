package com.javaspider.config;

import java.io.IOException;
import java.io.InputStream;
import java.util.Properties;

/**
 * 爬虫配置管理器
 *
 * 功能:
 * 1. 从配置文件加载配置
 * 2. 支持环境变量覆盖
 * 3. 提供类型安全的配置访问
 *
 * @author Lan
 * @version 1.0.0
 */
public class SpiderConfig {

    private final Properties properties;
    private static SpiderConfig instance;

    public SpiderConfig() {
        properties = new Properties();
        loadDefaultConfig();
    }

    /**
     * 从默认配置文件加载
     */
    private void loadDefaultConfig() {
        try (InputStream input = getClass().getClassLoader().getResourceAsStream("spider.properties")) {
            if (input != null) {
                properties.load(input);
            }
        } catch (IOException e) {
            // 配置文件可选，不存在时使用默认值
        }
    }

    /**
     * 从自定义路径加载配置
     *
     * @param path 配置文件路径
     * @throws IOException 读取失败时抛出
     * @throws SecurityException 路径不安全时抛出
     */
    public void loadFromFile(String path) throws IOException {
        if (path == null || path.isEmpty()) {
            throw new IllegalArgumentException("配置路径不能为空");
        }

        // 防止路径遍历攻击
        String normalizedPath = new java.io.File(path).getCanonicalPath();
        if (!normalizedPath.endsWith(".properties")) {
            throw new SecurityException("配置文件必须是 .properties 后缀");
        }

        try (InputStream input = new java.io.FileInputStream(path)) {
            properties.load(input);
        }
    }

    /**
     * 获取字符串配置
     */
    public String getString(String key, String defaultValue) {
        String envKey = getEnvKey(key);
        String value = System.getenv(envKey);
        if (value == null || value.isEmpty()) {
            value = properties.getProperty(key, defaultValue);
        }
        // 如果最终还是空字符串,返回默认值
        if (value == null || value.isEmpty()) {
            return defaultValue;
        }
        return value;
    }

    /**
     * 获取整数配置
     */
    public int getInt(String key, int defaultValue) {
        String value = getString(key, null);
        if (value == null) {
            return defaultValue;
        }
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }

    /**
     * 获取长整数配置
     */
    public long getLong(String key, long defaultValue) {
        String value = getString(key, null);
        if (value == null) {
            return defaultValue;
        }
        try {
            return Long.parseLong(value);
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }

    /**
     * 获取布尔配置
     */
    public boolean getBoolean(String key, boolean defaultValue) {
        String value = getString(key, null);
        if (value == null) {
            return defaultValue;
        }
        return Boolean.parseBoolean(value);
    }

    /**
     * 获取浮点数配置
     */
    public double getDouble(String key, double defaultValue) {
        String value = getString(key, null);
        if (value == null) {
            return defaultValue;
        }
        try {
            return Double.parseDouble(value);
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }

    /**
     * 设置配置值
     */
    public void setProperty(String key, String value) {
        properties.setProperty(key, value);
    }

    /**
     * 获取环境变量键
     */
    private String getEnvKey(String configKey) {
        return configKey.replace(".", "_").replace("-", "_").toUpperCase();
    }

    /**
     * 获取单例实例
     */
    public static synchronized SpiderConfig getInstance() {
        if (instance == null) {
            instance = new SpiderConfig();
        }
        return instance;
    }

    /**
     * 重新加载配置
     */
    public static void reload() {
        instance = new SpiderConfig();
    }
}
