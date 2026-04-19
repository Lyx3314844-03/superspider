package com.javaspider;

import java.io.*;
import java.time.Instant;
import java.util.*;

public class Exporter {
    
    private String outputDir;
    
    public Exporter(String outputDir) {
        this.outputDir = outputDir;
        new File(outputDir).mkdirs();
    }
    
    public String exportJSON(List<Map<String, String>> data, String filename) throws IOException {
        if (!filename.endsWith(".json")) filename += ".json";
        String filepath = outputDir + "/" + filename;
        
        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        sb.append("  \"schema_version\": 1,\n");
        sb.append("  \"runtime\": \"java\",\n");
        sb.append("  \"exported_at\": \"").append(Instant.now().toString()).append("\",\n");
        sb.append("  \"item_count\": ").append(data.size()).append(",\n");
        sb.append("  \"items\": [\n");
        
        for (int i = 0; i < data.size(); i++) {
            Map<String, String> item = data.get(i);
            sb.append("    {");
            boolean first = true;
            for (String key : item.keySet()) {
                if (!first) sb.append(", ");
                sb.append("\"").append(key).append("\": \"").append(item.get(key)).append("\"");
                first = false;
            }
            sb.append("}");
            if (i < data.size() - 1) sb.append(",");
            sb.append("\n");
        }
        
        sb.append("  ]\n}");
        
        FileWriter fw = new FileWriter(filepath);
        fw.write(sb.toString());
        fw.close();
        
        return filepath;
    }
    
    public String exportCSV(List<Map<String, String>> data, String filename) throws IOException {
        if (!filename.endsWith(".csv")) filename += ".csv";
        String filepath = outputDir + "/" + filename;
        
        if (data.isEmpty()) return filepath;
        
        FileWriter fw = new FileWriter(filepath);
        Set<String> headers = data.get(0).keySet();
        
        StringBuilder header = new StringBuilder();
        boolean first = true;
        for (String h : headers) {
            if (!first) header.append(",");
            header.append("\"").append(h).append("\"");
            first = false;
        }
        fw.write(header.toString() + "\n");
        
        for (Map<String, String> row : data) {
            StringBuilder line = new StringBuilder();
            first = true;
            for (String h : headers) {
                if (!first) line.append(",");
                line.append("\"").append(row.getOrDefault(h, "")).append("\"");
                first = false;
            }
            fw.write(line.toString() + "\n");
        }
        
        fw.close();
        return filepath;
    }

    public String exportJSONL(List<Map<String, String>> data, String filename) throws IOException {
        if (!filename.endsWith(".jsonl")) filename += ".jsonl";
        String filepath = outputDir + "/" + filename;

        StringBuilder sb = new StringBuilder();
        for (Map<String, String> item : data) {
            sb.append("{");
            boolean first = true;
            for (String key : item.keySet()) {
                if (!first) sb.append(", ");
                sb.append("\"").append(key).append("\": \"").append(item.get(key)).append("\"");
                first = false;
            }
            sb.append("}").append("\n");
        }

        FileWriter fw = new FileWriter(filepath);
        fw.write(sb.toString());
        fw.close();

        return filepath;
    }
    
    public String exportMD(List<Map<String, String>> data, String filename) throws IOException {
        if (!filename.endsWith(".md")) filename += ".md";
        String filepath = outputDir + "/" + filename;
        
        StringBuilder sb = new StringBuilder();
        sb.append("# 爬虫数据导出\n\n");
        sb.append("**导出时间**: ").append(new java.util.Date()).append("\n\n");
        sb.append("**数据条目**: ").append(data.size()).append("\n\n---\n\n");
        
        for (int i = 0; i < data.size(); i++) {
            Map<String, String> item = data.get(i);
            sb.append("## ").append(i + 1).append(". ").append(item.get("title")).append("\n\n");
            sb.append("- **URL**: ").append(item.get("url")).append("\n");
            sb.append("- **来源**: ").append(item.get("source")).append("\n");
            sb.append("- **摘要**: ").append(item.get("snippet")).append("\n\n");
        }
        
        FileWriter fw = new FileWriter(filepath);
        fw.write(sb.toString());
        fw.close();
        
        return filepath;
    }
    
    public void showMenu() {
        System.out.println("\n📊 数据导出功能:");
        System.out.println("  export json <filename> - 导出为 JSON");
        System.out.println("  export jsonl <filename> - 导出为 JSONL");
        System.out.println("  export csv <filename>   - 导出为 CSV");
        System.out.println("  export md <filename>    - 导出为 Markdown");
    }
}
