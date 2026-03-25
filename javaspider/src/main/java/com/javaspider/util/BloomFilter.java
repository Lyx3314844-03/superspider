package com.javaspider.util;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.BitSet;

/**
 * 布隆过滤器 - 高效 URL 去重
 * 
 * 特点：
 * - 空间效率极高
 * - 查询时间复杂度 O(k)
 * - 可能有误判（false positive），但不会漏判（false negative）
 */
public class BloomFilter {
    
    private final BitSet bitSet;
    private final int size;
    private final int hashCount;
    private int addedCount;
    
    /**
     * 创建布隆过滤器
     * @param expectedElements 预期元素数量
     * @param falsePositiveRate 可接受的误判率 (0.01 = 1%)
     */
    public BloomFilter(int expectedElements, double falsePositiveRate) {
        // 计算最优的位数组大小
        this.size = optimalSize(expectedElements, falsePositiveRate);
        // 计算最优的哈希函数数量
        this.hashCount = optimalHashCount(size, expectedElements);
        this.bitSet = new BitSet(size);
        this.addedCount = 0;
    }
    
    /**
     * 创建默认布隆过滤器（100 万元素，1% 误判率）
     */
    public BloomFilter() {
        this(1000000, 0.01);
    }
    
    /**
     * 添加元素
     */
    public boolean add(String element) {
        byte[] bytes = hash(element);
        
        for (int i = 0; i < hashCount; i++) {
            int index = Math.abs((bytes[i] + i * bytes[i + 1]) % size);
            bitSet.set(index, true);
        }
        
        addedCount++;
        return true;
    }
    
    /**
     * 检查元素是否存在（可能误判）
     * @return true=可能存在，false=一定不存在
     */
    public boolean contains(String element) {
        byte[] bytes = hash(element);
        
        for (int i = 0; i < hashCount; i++) {
            int index = Math.abs((bytes[i] + i * bytes[i + 1]) % size);
            if (!bitSet.get(index)) {
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * 添加并检查是否已存在
     * @return true=新添加，false=已存在
     */
    public boolean addIfAbsent(String element) {
        if (contains(element)) {
            return false;
        }
        add(element);
        return true;
    }
    
    /**
     * 获取已添加元素数量
     */
    public int size() {
        return addedCount;
    }
    
    /**
     * 获取位数组大小
     */
    public int getBitSetSize() {
        return size;
    }
    
    /**
     * 获取当前误判率估计
     */
    public double getFalsePositiveRate() {
        double bitsSet = bitSet.cardinality();
        double rate = Math.pow(1 - Math.exp(-hashCount * addedCount / (double) size), hashCount);
        return rate;
    }
    
    /**
     * 清空过滤器
     */
    public void clear() {
        bitSet.clear();
        addedCount = 0;
    }
    
    /**
     * 计算最优位数组大小
     */
    private int optimalSize(int n, double p) {
        // m = -n * ln(p) / (ln(2)^2)
        return (int) Math.ceil((-n * Math.log(p)) / (Math.log(2) * Math.log(2)));
    }

    /**
     * 计算最优哈希函数数量
     */
    private int optimalHashCount(int m, int n) {
        // k = m/n * ln(2)
        return Math.max(1, (int) Math.round((double) m / n * Math.log(2)));
    }
    
    /**
     * 生成哈希字节数组
     */
    private byte[] hash(String element) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            return md.digest(element.getBytes(StandardCharsets.UTF_8));
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("MD5 algorithm not found", e);
        }
    }
    
    /**
     * 打印统计信息
     */
    public void printStats() {
        System.out.println("========== BloomFilter Stats ==========");
        System.out.println("Expected elements: ~" + addedCount);
        System.out.println("BitSet size: " + size + " bits (" + (size / 8 / 1024) + " KB)");
        System.out.println("Hash count: " + hashCount);
        System.out.println("Bits set: " + bitSet.cardinality() + " (" + (bitSet.cardinality() * 100.0 / size) + "%)");
        System.out.println("Estimated false positive rate: " + (getFalsePositiveRate() * 100) + "%");
        System.out.println("========================================");
    }
}
