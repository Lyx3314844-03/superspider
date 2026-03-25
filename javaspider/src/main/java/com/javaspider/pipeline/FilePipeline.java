package com.javaspider.pipeline;

import com.javaspider.core.ResultItems;
import com.javaspider.core.Spider;
import com.javaspider.util.SpiderExceptionHandler;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;

/**
 * 文件管道
 */
public class FilePipeline implements Pipeline {
    
    private static final Gson gson = new GsonBuilder().setPrettyPrinting().create();
    private final String outputPath;
    
    public FilePipeline(String outputPath) {
        this.outputPath = outputPath;
        
        // 创建目录
        try {
            Path path = Paths.get(outputPath);
            if (!Files.exists(path.getParent())) {
                Files.createDirectories(path.getParent());
            }
        } catch (IOException e) {
            SpiderExceptionHandler.handle(e, "FilePipeline directory creation");
        }
    }
    
    @Override
    public void process(ResultItems resultItems, Spider spider) {
        try {
            if (resultItems == null) {
                System.err.println("ResultItems is null, skipping file save");
                return;
            }
            
            // 转换为 Map
            Map<String, Object> data = resultItems.getAll();
            
            // 保存为 JSON
            saveAsJson(data);
            
        } catch (Exception e) {
            SpiderExceptionHandler.handle(e, "FilePipeline");
        }
    }
    
    /**
     * 保存为 JSON
     */
    private void saveAsJson(Map<String, Object> data) throws IOException {
        try (FileWriter writer = new FileWriter(outputPath)) {
            gson.toJson(data, writer);
        }
        System.out.println("Data saved to: " + outputPath);
    }
    
    @Override
    public void close() {
        // 无需特殊关闭操作
    }
}
