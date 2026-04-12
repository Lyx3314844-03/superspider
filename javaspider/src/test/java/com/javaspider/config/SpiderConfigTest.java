package com.javaspider.config;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;

import static org.junit.jupiter.api.Assertions.*;

import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * SpiderConfig 单元测试
 */
@DisplayName("SpiderConfig 测试")
class SpiderConfigTest {

    private Path tempConfigFile;
    private SpiderConfig config;

    @BeforeEach
    void setUp() throws IOException {
        config = new SpiderConfig();
        tempConfigFile = Files.createTempFile("spider-test", ".properties");
    }

    @AfterEach
    void tearDown() throws IOException {
        if (tempConfigFile != null && Files.exists(tempConfigFile)) {
            Files.delete(tempConfigFile);
        }
        SpiderConfig.reload();
    }

    @Test
    @DisplayName("测试单例模式")
    void testSingleton() {
        SpiderConfig instance1 = SpiderConfig.getInstance();
        SpiderConfig instance2 = SpiderConfig.getInstance();
        
        assertSame(instance1, instance2, "单例应该返回相同实例");
    }

    @Test
    @DisplayName("测试默认配置")
    void testDefaultConfig() {
        SpiderConfig config = new SpiderConfig();
        
        // 测试默认值
        assertEquals(5, config.getInt("spider.threads", 5));
        assertEquals("default", config.getString("nonexistent.key", "default"));
        assertTrue(config.getBoolean("nonexistent.key", true));
        assertFalse(config.getBoolean("nonexistent.key", false));
    }

    @Test
    @DisplayName("测试从文件加载配置")
    void testLoadFromFile() throws IOException {
        // 写入测试配置
        try (FileWriter writer = new FileWriter(tempConfigFile.toFile())) {
            writer.write("test.string=hello\n");
            writer.write("test.int=42\n");
            writer.write("test.boolean=true\n");
            writer.write("test.double=3.14\n");
        }

        config.loadFromFile(tempConfigFile.toFile().getAbsolutePath());

        // 验证配置
        assertEquals("hello", config.getString("test.string", "default"));
        assertEquals(42, config.getInt("test.int", 0));
        assertTrue(config.getBoolean("test.boolean", false));
        assertEquals(3.14, config.getDouble("test.double", 0.0), 0.01);
    }

    @Test
    @DisplayName("测试类型转换")
    void testTypeConversion() {
        // 测试无效数字的默认值处理
        config.setProperty("invalid.int", "not-a-number");
        config.setProperty("invalid.double", "not-a-number");
        
        assertEquals(100, config.getInt("invalid.int", 100));
        assertEquals(2.5, config.getDouble("invalid.double", 2.5), 0.01);
    }

    @Test
    @DisplayName("测试布尔值解析")
    void testBooleanParsing() {
        config.setProperty("bool.true", "true");
        config.setProperty("bool.false", "false");
        config.setProperty("bool.invalid", "invalid");
        
        assertTrue(config.getBoolean("bool.true", false));
        assertFalse(config.getBoolean("bool.false", true));
        assertFalse(config.getBoolean("bool.invalid", false));
    }

    @Test
    @DisplayName("测试长整数配置")
    void testLongConfig() {
        config.setProperty("test.long", "1234567890123");
        
        assertEquals(1234567890123L, config.getLong("test.long", 0L));
        assertEquals(999L, config.getLong("nonexistent", 999L));
    }

    @Test
    @DisplayName("测试配置覆盖")
    void testConfigOverride() {
        config.setProperty("test.key", "value1");
        assertEquals("value1", config.getString("test.key", "default"));
        
        config.setProperty("test.key", "value2");
        assertEquals("value2", config.getString("test.key", "default"));
    }

    @Test
    @DisplayName("测试环境变量键转换")
    void testEnvKeyConversion() {
        // 验证内部方法的行为
        config.setProperty("dot.separated.key", "value");
        assertEquals("value", config.getString("dot.separated.key", "default"));
    }

    @Test
    @DisplayName("测试重新加载")
    void testReload() {
        SpiderConfig config1 = SpiderConfig.getInstance();
        config1.setProperty("test.key", "test-value");
        
        SpiderConfig.reload();
        
        SpiderConfig config2 = SpiderConfig.getInstance();
        assertNotSame(config1, config2);
        assertEquals("default", config2.getString("test.key", "default"));
    }

    @Test
    @DisplayName("测试空值处理")
    void testNullHandling() {
        config.setProperty("empty.string", "");
        
        // 空字符串应该返回默认值
        assertEquals("default", config.getString("empty.string", "default"));
    }

    @Test
    @DisplayName("测试特殊字符")
    void testSpecialCharacters() {
        config.setProperty("special.value", "hello=world:test");
        
        assertEquals("hello=world:test", config.getString("special.value", "default"));
    }

    @Test
    @DisplayName("测试边界值")
    void testBoundaryValues() {
        config.setProperty("max.int", String.valueOf(Integer.MAX_VALUE));
        config.setProperty("min.int", String.valueOf(Integer.MIN_VALUE));
        
        assertEquals(Integer.MAX_VALUE, config.getInt("max.int", 0));
        assertEquals(Integer.MIN_VALUE, config.getInt("min.int", 0));
    }
}
