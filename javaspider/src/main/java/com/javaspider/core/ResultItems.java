package com.javaspider.core;

import lombok.Data;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * ResultItems - 结果对象
 * 
 * 存储爬取结果，支持多种数据类型
 * 
 * @author Lan
 * @version 2.0.0
 * @since 2026-03-20
 */
@Data
public class ResultItems {
    
    /**
     * 结果数据
     */
    private Map<String, Object> data = new LinkedHashMap<>();
    
    /**
     * 请求对象
     */
    private Request request;
    
    /**
     * 爬虫 ID
     */
    private String spiderId;
    
    /**
     * 是否跳过
     */
    private boolean skip;
    
    /**
     * 添加结果
     * @param key 键
     * @param value 值
     * @return this
     */
    public ResultItems put(String key, Object value) {
        data.put(key, value);
        return this;
    }
    
    /**
     * 添加多个结果
     * @param data 数据
     * @return this
     */
    public ResultItems putAll(Map<String, Object> data) {
        this.data.putAll(data);
        return this;
    }
    
    /**
     * 获取结果
     * @param key 键
     * @return 结果
     */
    @SuppressWarnings("unchecked")
    public <T> T get(String key) {
        return (T) data.get(key);
    }
    
    /**
     * 获取字符串结果
     * @param key 键
     * @return 字符串结果
     */
    public String getString(String key) {
        return get(key);
    }
    
    /**
     * 获取整数结果
     * @param key 键
     * @return 整数结果
     */
    public Integer getInteger(String key) {
        return get(key);
    }
    
    /**
     * 获取长整数结果
     * @param key 键
     * @return 长整数结果
     */
    public Long getLong(String key) {
        return get(key);
    }
    
    /**
     * 获取浮点数结果
     * @param key 键
     * @return 浮点数结果
     */
    public Double getDouble(String key) {
        return get(key);
    }
    
    /**
     * 获取布尔结果
     * @param key 键
     * @return 布尔结果
     */
    public Boolean getBoolean(String key) {
        return get(key);
    }
    
    /**
     * 获取列表结果
     * @param key 键
     * @return 列表结果
     */
    @SuppressWarnings("unchecked")
    public <T> java.util.List<T> getList(String key) {
        return (java.util.List<T>) data.get(key);
    }
    
    /**
     * 获取 Map 结果
     * @param key 键
     * @return Map 结果
     */
    @SuppressWarnings("unchecked")
    public <K, V> Map<K, V> getMap(String key) {
        return (Map<K, V>) data.get(key);
    }
    
    /**
     * 获取所有数据
     * @return 所有数据
     */
    public Map<String, Object> getAll() {
        return data;
    }
    
    /**
     * 检查是否包含指定键
     * @param key 键
     * @return 是否包含
     */
    public boolean contains(String key) {
        return data.containsKey(key);
    }
    
    /**
     * 检查是否为空
     * @return 是否为空
     */
    public boolean isEmpty() {
        return data.isEmpty();
    }
    
    /**
     * 获取数据大小
     * @return 数据大小
     */
    public int size() {
        return data.size();
    }
    
    /**
     * 清除所有数据
     */
    public void clear() {
        data.clear();
    }
    
    /**
     * 移除指定键的数据
     * @param key 键
     * @return 移除的值
     */
    public Object remove(String key) {
        return data.remove(key);
    }
    
    /**
     * 获取所有键
     * @return 所有键
     */
    public java.util.Set<String> keySet() {
        return data.keySet();
    }
    
    /**
     * 获取所有值
     * @return 所有值
     */
    public java.util.Collection<Object> values() {
        return data.values();
    }
    
    /**
     * 获取所有条目
     * @return 所有条目
     */
    public java.util.Set<Map.Entry<String, Object>> entrySet() {
        return data.entrySet();
    }
    
    /**
     * 创建 ResultItems 实例
     * @return ResultItems 实例
     */
    public static ResultItems create() {
        return new ResultItems();
    }
    
    /**
     * 创建 ResultItems 实例并设置请求
     * @param request 请求
     * @return ResultItems 实例
     */
    public static ResultItems of(Request request) {
        ResultItems resultItems = new ResultItems();
        resultItems.request = request;
        return resultItems;
    }
}
