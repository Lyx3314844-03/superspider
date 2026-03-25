package com.javaspider.performance.fingerprint;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.BitSet;
import java.util.zip.CRC32;

/**
 * 内容指纹和去重
 * 类似 Scrapy 的 RFPDupeFilter
 * 
 * 特性:
 * - SimHash 指纹
 * - Bloom Filter 去重
 * - 感知哈希
 */
public class ContentFingerprinter {
    
    /**
     * 计算 SimHash 指纹
     * 
     * @param content 内容
     * @return 64 位 SimHash 值
     */
    public static long simHash(String content) {
        if (content == null || content.isEmpty()) {
            return 0L;
        }
        
        // 分词（简单按字符分割）
        int[] v = new int[64];
        
        for (char c : content.toCharArray()) {
            long hash = murmurHash64(String.valueOf(c));
            
            for (int i = 0; i < 64; i++) {
                if ((hash & (1L << i)) != 0) {
                    v[i]++;
                } else {
                    v[i]--;
                }
            }
        }
        
        // 计算最终指纹
        long fingerprint = 0L;
        for (int i = 0; i < 64; i++) {
            if (v[i] > 0) {
                fingerprint |= (1L << i);
            }
        }
        
        return fingerprint;
    }
    
    /**
     * 计算两个 SimHash 的海明距离
     * 
     * @param hash1 哈希 1
     * @param hash2 哈希 2
     * @return 海明距离
     */
    public static int hammingDistance(long hash1, long hash2) {
        long xor = hash1 ^ hash2;
        return Long.bitCount(xor);
    }
    
    /**
     * 检查两个内容是否相似
     * 
     * @param content1 内容 1
     * @param content2 内容 2
     * @param threshold 相似度阈值（海明距离）
     * @return 是否相似
     */
    public static boolean isSimilar(String content1, String content2, int threshold) {
        long hash1 = simHash(content1);
        long hash2 = simHash(content2);
        return hammingDistance(hash1, hash2) <= threshold;
    }
    
    /**
     * 计算 MD5 指纹
     */
    public static String md5Fingerprint(String content) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] digest = md.digest(content.getBytes(StandardCharsets.UTF_8));
            return bytesToHex(digest);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("MD5 not available", e);
        }
    }
    
    /**
     * 计算 SHA-256 指纹
     */
    public static String sha256Fingerprint(String content) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(content.getBytes(StandardCharsets.UTF_8));
            return bytesToHex(digest);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }
    
    /**
     * 计算 CRC32 校验和
     */
    public static long crc32(String content) {
        CRC32 crc32 = new CRC32();
        crc32.update(content.getBytes(StandardCharsets.UTF_8));
        return crc32.getValue();
    }
    
    /**
     * MurmurHash64
     */
    public static long murmurHash64(String key) {
        final long m = 0xc6a4a7935bd1e995L;
        final int r = 47;
        
        long h = 0x9747b28cL ^ (key.length() * m);
        
        int len = key.length();
        int len4 = len / 4;
        
        for (int i = 0; i < len4; i++) {
            int i4 = i * 4;
            long k = (key.charAt(i4) & 0xffff) |
                    ((key.charAt(i4 + 1) & 0xffff) << 16) |
                    ((long) (key.charAt(i4 + 2) & 0xffff) << 32) |
                    ((long) (key.charAt(i4 + 3) & 0xffff) << 48);
            k *= m;
            k ^= k >>> r;
            k *= m;
            h ^= k;
            h *= m;
        }
        
        switch (len % 4) {
            case 3:
                h ^= (long) (key.charAt((len & ~3) + 2) & 0xffff) << 32;
            case 2:
                h ^= (long) (key.charAt((len & ~3) + 1) & 0xffff) << 16;
            case 1:
                h ^= (long) (key.charAt(len & ~3) & 0xffff);
                h *= m;
        }
        
        h ^= h >>> r;
        h *= m;
        h ^= h >>> r;
        
        return h;
    }
    
    /**
     * 字节转十六进制
     */
    private static String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
    
    /**
     * 创建布隆过滤器去重器
     */
    public static BloomFilterDupeFilter createBloomFilter(int expectedElements) {
        return new BloomFilterDupeFilter(expectedElements);
    }
    
    /**
     * 布隆过滤器去重器
     */
    public static class BloomFilterDupeFilter {
        private final BitSet bitSet;
        private final int size;
        private final int hashCount;
        
        public BloomFilterDupeFilter(int expectedElements) {
            this.size = optimalSize(expectedElements, 0.01);
            this.hashCount = optimalHashCount(size, expectedElements);
            this.bitSet = new BitSet(size);
        }
        
        public boolean addAndCheck(String content) {
            String fingerprint = md5Fingerprint(content);
            byte[] bytes = fingerprint.getBytes(StandardCharsets.UTF_8);

            boolean allSet = true;
            for (int i = 0; i < hashCount; i++) {
                long hashLong = murmurHash64(fingerprint + i) % size;
                int hash = (int) hashLong;
                if (hash < 0) hash += size;

                if (!bitSet.get(hash)) {
                    allSet = false;
                }
                bitSet.set(hash);
            }

            return allSet; // 如果所有位都已设置，说明可能重复
        }
        
        private int optimalSize(int n, double p) {
            return (int) Math.ceil(-n * Math.log(p) / (Math.log(2) * Math.log(2)));
        }
        
        private int optimalHashCount(int m, int n) {
            return (int) Math.round((double) m / n * Math.log(2));
        }
    }
}
