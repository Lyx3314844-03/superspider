package com.javaspider.scrapy.item;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Item 类单元测试
 */
class ItemTest {

    @Test
    @DisplayName("创建空 Item")
    void testCreateEmptyItem() {
        Item item = new Item();
        
        assertNotNull(item);
        assertTrue(item.isEmpty());
        assertEquals(0, item.size());
    }

    @Test
    @DisplayName("设置和获取字段")
    void testSetAndGet() {
        Item item = new Item();
        
        item.set("title", "Hello World");
        item.set("price", 99.99);
        item.set("count", 42);
        
        assertEquals("Hello World", item.get("title"));
        assertEquals(99.99, item.get("price"));
        assertEquals(42, item.get("count"));
    }

    @Test
    @DisplayName("设置字段返回自身（链式调用）")
    void testSetReturnsSelf() {
        Item item = new Item();
        
        Item result = item.set("title", "Test");
        
        assertSame(item, result);
    }

    @Test
    @DisplayName("链式设置字段")
    void testChainedSet() {
        Item item = new Item();
        
        item.set("title", "Test")
            .set("price", 99.99)
            .set("url", "https://example.com");
        
        assertEquals("Test", item.get("title"));
        assertEquals(99.99, item.get("price"));
        assertEquals("https://example.com", item.get("url"));
    }

    @Test
    @DisplayName("获取不存在的字段返回 null")
    void testGetNonExistentField() {
        Item item = new Item();
        
        assertNull(item.get("nonexistent"));
    }

    @Test
    @DisplayName("获取不存在的字段返回默认值")
    void testGetWithDefault() {
        Item item = new Item();
        
        String value = item.get("nonexistent", "default");
        
        assertEquals("default", value);
    }

    @Test
    @DisplayName("检查字段是否存在")
    void testHasField() {
        Item item = new Item();
        item.set("title", "Test");
        
        assertTrue(item.hasField("title"));
        assertFalse(item.hasField("nonexistent"));
    }

    @Test
    @DisplayName("获取所有字段名")
    void testGetFields() {
        Item item = new Item();
        item.set("title", "Test")
            .set("price", 99.99)
            .set("url", "https://example.com");
        
        Set<String> fields = item.getFields();
        
        assertEquals(3, fields.size());
        assertTrue(fields.contains("title"));
        assertTrue(fields.contains("price"));
        assertTrue(fields.contains("url"));
    }

    @Test
    @DisplayName("移除字段")
    void testRemove() {
        Item item = new Item();
        item.set("title", "Test");
        
        Object removed = item.remove("title");
        
        assertEquals("Test", removed);
        assertFalse(item.hasField("title"));
    }

    @Test
    @DisplayName("清空所有字段")
    void testClear() {
        Item item = new Item();
        item.set("title", "Test")
            .set("price", 99.99);
        
        item.clear();
        
        assertTrue(item.isEmpty());
        assertEquals(0, item.size());
        assertTrue(item.getFields().isEmpty());
    }

    @Test
    @DisplayName("合并另一个 Item")
    void testMerge() {
        Item item1 = new Item();
        item1.set("title", "Test");
        
        Item item2 = new Item();
        item2.set("price", 99.99);
        item2.set("url", "https://example.com");
        
        item1.merge(item2);
        
        assertEquals("Test", item1.get("title"));
        assertEquals(99.99, item1.get("price"));
        assertEquals("https://example.com", item1.get("url"));
    }

    @Test
    @DisplayName("转换为 Map")
    void testToMap() {
        Item item = new Item();
        item.set("title", "Test")
            .set("price", 99.99);
        
        Map<String, Object> map = item.toMap();
        
        assertEquals(2, map.size());
        assertEquals("Test", map.get("title"));
        assertEquals(99.99, map.get("price"));
    }

    @Test
    @DisplayName("从 Map 创建 Item")
    void testFromMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("title", "Test");
        map.put("price", 99.99);
        
        Item item = Item.fromMap(map);
        
        assertEquals("Test", item.get("title"));
        assertEquals(99.99, item.get("price"));
    }

    @Test
    @DisplayName("toString 测试")
    void testToString() {
        Item item = new Item();
        item.set("title", "Test");
        item.set("price", 99.99);
        
        String str = item.toString();
        
        assertTrue(str.contains("title"));
        assertTrue(str.contains("Test"));
        assertTrue(str.contains("price"));
    }

    @Test
    @DisplayName("泛型获取测试")
    void testGenericGet() {
        Item item = new Item();
        item.set("title", "Test");
        item.set("price", 99.99);
        item.set("count", 42);
        
        String title = item.get("title", String.class);
        Double price = item.get("price", Double.class);
        Integer count = item.get("count", Integer.class);
        
        assertEquals("Test", title);
        assertEquals(99.99, price);
        assertEquals(42, count);
    }
}
