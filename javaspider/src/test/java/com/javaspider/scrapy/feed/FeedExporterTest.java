package com.javaspider.scrapy.feed;

import com.javaspider.scrapy.item.Item;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * FeedExporter 类单元测试
 */
class FeedExporterTest {

    @TempDir
    Path tempDir;

    @Test
    @DisplayName("创建 JSON 导出器")
    void testCreateJsonExporter() {
        Path outputPath = tempDir.resolve("test.json");
        FeedExporter exporter = FeedExporter.json(outputPath.toString());
        
        assertNotNull(exporter);
        assertEquals(0, exporter.getItemCount());
    }

    @Test
    @DisplayName("创建 CSV 导出器")
    void testCreateCsvExporter() {
        Path outputPath = tempDir.resolve("test.csv");
        FeedExporter exporter = FeedExporter.csv(outputPath.toString());
        
        assertNotNull(exporter);
    }

    @Test
    @DisplayName("创建 XML 导出器")
    void testCreateXmlExporter() {
        Path outputPath = tempDir.resolve("test.xml");
        FeedExporter exporter = FeedExporter.xml(outputPath.toString());
        
        assertNotNull(exporter);
    }

    @Test
    @DisplayName("导出单个 Item 到 JSON")
    void testExportSingleItemJson() {
        Path outputPath = tempDir.resolve("single.json");
        FeedExporter exporter = FeedExporter.json(outputPath.toString());
        
        Item item = new Item();
        item.set("title", "Test");
        item.set("price", 99.99);
        
        exporter.exportItem(item);
        exporter.close();
        
        assertEquals(1, exporter.getItemCount());
        assertTrue(Files.exists(outputPath));
    }

    @Test
    @DisplayName("导出多个 Item 到 JSON")
    void testExportMultipleItemsJson() {
        Path outputPath = tempDir.resolve("multiple.json");
        FeedExporter exporter = FeedExporter.json(outputPath.toString());
        
        List<Item> items = List.of(
            createItem("Item 1", 10.00),
            createItem("Item 2", 20.00),
            createItem("Item 3", 30.00)
        );
        
        exporter.exportItems(items);
        exporter.close();
        
        assertEquals(3, exporter.getItemCount());
        assertTrue(Files.exists(outputPath));
        
        // 验证文件内容
        String content = readFile(outputPath);
        assertTrue(content.contains("Item 1"));
        assertTrue(content.contains("Item 2"));
        assertTrue(content.contains("Item 3"));
    }

    @Test
    @DisplayName("导出 CSV 包含头行")
    void testExportCsvWithHeader() {
        Path outputPath = tempDir.resolve("test.csv");
        FeedExporter exporter = FeedExporter.csv(outputPath.toString());
        
        Item item1 = new Item();
        item1.set("title", "Test 1");
        item1.set("price", "10.00");
        
        Item item2 = new Item();
        item2.set("title", "Test 2");
        item2.set("price", "20.00");
        
        exporter.exportItem(item1);
        exporter.exportItem(item2);
        exporter.close();
        
        assertTrue(Files.exists(outputPath));
        
        String content = readFile(outputPath);
        String[] lines = content.split("\n");
        
        // 第一行应该是头行
        assertTrue(lines[0].contains("title"));
        assertTrue(lines[0].contains("price"));
        
        // 应该有 3 行（头行 + 2 个数据行）
        assertEquals(3, lines.length);
    }

    @Test
    @DisplayName("导出 XML")
    void testExportXml() {
        Path outputPath = tempDir.resolve("test.xml");
        FeedExporter exporter = FeedExporter.xml(outputPath.toString());
        
        Item item = new Item();
        item.set("title", "Test");
        item.set("price", 99.99);
        
        exporter.exportItem(item);
        exporter.close();
        
        assertTrue(Files.exists(outputPath));
        
        String content = readFile(outputPath);
        assertTrue(content.contains("<?xml version=\"1.0\""));
        assertTrue(content.contains("<items>"));
        assertTrue(content.contains("</items>"));
        assertTrue(content.contains("<title>"));
    }

    @Test
    @DisplayName("导出 JSON Lines")
    void testExportJsonLines() {
        Path outputPath = tempDir.resolve("test.jl");
        FeedExporter exporter = FeedExporter.jsonlines(outputPath.toString());
        
        List<Item> items = List.of(
            createItem("Item 1", 10.00),
            createItem("Item 2", 20.00)
        );
        
        exporter.exportItems(items);
        exporter.close();
        
        assertTrue(Files.exists(outputPath));
        
        String content = readFile(outputPath);
        String[] lines = content.split("\n");
        
        // 每行都是一个完整的 JSON 对象
        assertEquals(2, lines.length);
        assertTrue(lines[0].startsWith("{"));
        assertTrue(lines[1].startsWith("{"));
    }

    @Test
    @DisplayName("追加模式导出")
    void testAppendMode() {
        Path outputPath = tempDir.resolve("append.json");
        
        // 第一次导出
        FeedExporter exporter1 = new FeedExporter("json", outputPath.toString(), false);
        exporter1.exportItem(createItem("Item 1", 10.00));
        exporter1.close();
        
        // 追加模式导出
        FeedExporter exporter2 = new FeedExporter("json", outputPath.toString(), true);
        exporter2.exportItem(createItem("Item 2", 20.00));
        exporter2.close();
        
        assertTrue(Files.exists(outputPath));
    }

    @Test
    @DisplayName("获取输出文件路径")
    void testGetCurrentFile() {
        Path outputPath = tempDir.resolve("test.json");
        FeedExporter exporter = FeedExporter.json(outputPath.toString());
        
        Path currentFile = exporter.getCurrentFile();
        
        assertNotNull(currentFile);
    }

    @Test
    @DisplayName("空 Item 导出")
    void testExportEmptyItem() {
        Path outputPath = tempDir.resolve("empty.json");
        FeedExporter exporter = FeedExporter.json(outputPath.toString());
        
        Item item = new Item();
        exporter.exportItem(item);
        exporter.close();
        
        assertEquals(1, exporter.getItemCount());
        assertTrue(Files.exists(outputPath));
    }

    /**
     * 辅助方法：创建测试 Item
     */
    private Item createItem(String title, double price) {
        Item item = new Item();
        item.set("title", title);
        item.set("price", price);
        item.set("url", "https://example.com/" + title.replace(" ", "-"));
        return item;
    }

    /**
     * 辅助方法：读取文件内容
     */
    private String readFile(Path path) {
        try {
            return Files.readString(path);
        } catch (Exception e) {
            fail("Failed to read file: " + e.getMessage());
            return "";
        }
    }
}
