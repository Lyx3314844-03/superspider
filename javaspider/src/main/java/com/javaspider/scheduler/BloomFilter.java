package com.javaspider.scheduler;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.BitSet;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 布隆过滤器
 * 用于 URL 去重，节省内存空间
 */
public class BloomFilter {
    private final BitSet bitSet;
    private final int size;
    private final int hashCount;
    private final AtomicInteger addedCount = new AtomicInteger(0);

    /**
     * 构造函数
     * @param expectedElements 预期元素数量
     * @param falsePositiveRate 期望的误判率 (0-1)
     */
    public BloomFilter(int expectedElements, double falsePositiveRate) {
        this.size = optimalSize(expectedElements, falsePositiveRate);
        this.hashCount = optimalHashCount(size, expectedElements);
        this.bitSet = new BitSet(size);
    }

    /**
     * 默认构造函数
     */
    public BloomFilter() {
        this(1000000, 0.01); // 默认 100 万元素，1% 误判率
    }

    /**
     * 添加元素
     */
    public boolean add(String element) {
        if (element == null) {
            return false;
        }

        byte[] bytes = element.getBytes(StandardCharsets.UTF_8);
        int[] hashes = hash(bytes);

        boolean mayContain = true;
        for (int hash : hashes) {
            int index = Math.abs(hash) % size;
            if (!bitSet.get(index)) {
                mayContain = false;
            }
            bitSet.set(index);
        }

        if (!mayContain) {
            addedCount.incrementAndGet();
        }

        return mayContain;
    }

    /**
     * 检查元素是否存在
     */
    public boolean contains(String element) {
        if (element == null) {
            return false;
        }

        byte[] bytes = element.getBytes(StandardCharsets.UTF_8);
        int[] hashes = hash(bytes);

        for (int hash : hashes) {
            int index = Math.abs(hash) % size;
            if (!bitSet.get(index)) {
                return false;
            }
        }

        return true;
    }

    /**
     * 添加并检查（如果已存在返回 true，否则添加并返回 false）
     */
    public boolean addAndCheck(String element) {
        if (element == null) {
            return true;
        }

        byte[] bytes = element.getBytes(StandardCharsets.UTF_8);
        int[] hashes = hash(bytes);

        boolean allSet = true;
        for (int hash : hashes) {
            int index = Math.abs(hash) % size;
            if (!bitSet.get(index)) {
                allSet = false;
            }
            bitSet.set(index);
        }

        if (!allSet) {
            addedCount.incrementAndGet();
        }

        return allSet;
    }

    /**
     * 清除所有元素
     */
    public void clear() {
        bitSet.clear();
        addedCount.set(0);
    }

    /**
     * 获取已添加元素数量（估算）
     */
    public int size() {
        return addedCount.get();
    }

    /**
     * 获取位数组大小
     */
    public int getBitSetSize() {
        return size;
    }

    /**
     * 获取哈希函数数量
     */
    public int getHashCount() {
        return hashCount;
    }

    /**
     * 获取实际位数组
     */
    public BitSet getBitSet() {
        return bitSet;
    }

    /**
     * 计算当前误判率（估算）
     */
    public double getFalsePositiveRate() {
        int setBits = bitSet.cardinality();
        if (setBits == 0) {
            return 0;
        }
        double p = Math.pow(1.0 - (double) setBits / size, hashCount);
        return Math.pow(1.0 - p, hashCount);
    }

    /**
     * 计算最优位数组大小
     */
    private int optimalSize(int n, double p) {
        if (p == 0) {
            p = 1e-10;
        }
        return (int) Math.ceil(-n * Math.log(p) / (Math.log(2) * Math.log(2)));
    }

    /**
     * 计算最优哈希函数数量
     */
    private int optimalHashCount(int m, int n) {
        int k = (int) Math.round((double) m / n * Math.log(2));
        return Math.max(1, k);
    }

    /**
     * 生成多个哈希值（线程安全版本）
     * 注意：每次调用都创建新的 MessageDigest 实例，避免线程安全问题
     */
    private int[] hash(byte[] data) {
        int[] hashes = new int[hashCount];

        try {
            // 每次创建新的 MessageDigest 实例以保证线程安全
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] digest = md.digest(data);

            // 从 MD5 结果派生多个哈希值
            for (int i = 0; i < hashCount; i++) {
                int h1 = ((digest[i * 4 % 16] & 0xFF) << 24) |
                         ((digest[(i * 4 + 1) % 16] & 0xFF) << 16) |
                         ((digest[(i * 4 + 2) % 16] & 0xFF) << 8) |
                         (digest[(i * 4 + 3) % 16] & 0xFF);
                hashes[i] = h1;
            }
        } catch (NoSuchAlgorithmException e) {
            // 降级到简单的字符串哈希
            for (int i = 0; i < hashCount; i++) {
                hashes[i] = murmurHash(data, i);
            }
        }

        return hashes;
    }

    /**
     * MurmurHash 实现
     */
    private int murmurHash(byte[] data, int seed) {
        int m = 0x5bd1e995;
        int r = 24;
        int h = seed ^ data.length;
        int len = data.length;
        int nBlocks = len / 4;

        for (int i = 0; i < nBlocks; i++) {
            int k = (data[i * 4] & 0xFF) |
                    ((data[i * 4 + 1] & 0xFF) << 8) |
                    ((data[i * 4 + 2] & 0xFF) << 16) |
                    ((data[i * 4 + 3] & 0xFF) << 24);

            k *= m;
            k ^= k >>> r;
            k *= m;

            h *= m;
            h ^= k;
        }

        int nRemainder = len % 4;
        if (nRemainder > 0) {
            byte[] remainder = new byte[nRemainder];
            System.arraycopy(data, len - nRemainder, remainder, 0, nRemainder);
            int k = 0;
            for (int i = 0; i < nRemainder; i++) {
                k |= (remainder[i] & 0xFF) << (8 * i);
            }
            k *= m;
            k ^= k >>> r;
            h *= m;
            h ^= k;
        }

        h ^= h >>> 13;
        h *= m;
        h ^= h >>> 15;

        return h;
    }

    /**
     * 创建默认布隆过滤器
     */
    public static BloomFilter create() {
        return new BloomFilter();
    }

    /**
     * 创建指定容量的布隆过滤器
     */
    public static BloomFilter create(int expectedElements) {
        return new BloomFilter(expectedElements, 0.01);
    }

    /**
     * 创建指定容量和误判率的布隆过滤器
     */
    public static BloomFilter create(int expectedElements, double falsePositiveRate) {
        return new BloomFilter(expectedElements, falsePositiveRate);
    }
}
