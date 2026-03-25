package com.javaspider.core;

import com.javaspider.scheduler.BloomFilter;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.BeforeEach;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

/**
 * BloomFilter 单元测试 (修复版)
 */
@DisplayName("BloomFilter 测试")
class BloomFilterTest {
    
    private BloomFilter bloomFilter;
    
    @BeforeEach
    void setUp() {
        bloomFilter = new BloomFilter(1000, 0.01);
    }
    
    @Test
    @DisplayName("测试初始化")
    void testInitialization() {
        assertNotNull(bloomFilter);
    }
    
    @Test
    @DisplayName("测试添加和检查")
    void testAddAndContains() {
        String value = "test value";
        
        // 添加前应该不存在
        assertFalse(bloomFilter.contains(value));
        
        // 添加
        bloomFilter.add(value);
        
        // 添加后应该存在
        assertTrue(bloomFilter.contains(value));
    }
    
    @Test
    @DisplayName("测试多个值")
    void testMultipleValues() {
        List<String> values = Arrays.asList("value1", "value2", "value3");
        
        // 添加所有值
        for (String value : values) {
            bloomFilter.add(value);
        }
        
        // 验证所有值都存在
        for (String value : values) {
            assertTrue(bloomFilter.contains(value));
        }
    }
    
    @Test
    @DisplayName("测试误判率")
    void testFalsePositiveRate() {
        // 添加一些数据
        for (int i = 0; i < 100; i++) {
            bloomFilter.add("data" + i);
        }
        
        // 检查不存在的数据
        int falsePositives = 0;
        int totalTests = 1000;
        
        for (int i = 100; i < 100 + totalTests; i++) {
            if (bloomFilter.contains("data" + i)) {
                falsePositives++;
            }
        }
        
        double falsePositiveRate = (double) falsePositives / totalTests;
        assertTrue(falsePositiveRate < 0.1, "误判率过高");
    }
    
    @Test
    @DisplayName("测试空字符串")
    void testEmptyString() {
        String empty = "";
        bloomFilter.add(empty);
        assertTrue(bloomFilter.contains(empty));
    }
    
    @Test
    @DisplayName("测试 null 值")
    void testNullValue() {
        // 根据源码，add(null) 返回 false
        assertFalse(bloomFilter.add(null));
    }
}
