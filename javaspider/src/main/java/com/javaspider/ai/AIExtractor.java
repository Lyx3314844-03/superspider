package com.javaspider.ai;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/**
 * AI 提取器 - 集成 LLM 进行智能内容提取
 * 支持 OpenAI GPT、Anthropic Claude 等
 */
public class AIExtractor {
    
    private final String apiKey;
    private final String baseUrl;
    private final String model;
    private final int maxTokens;
    private final double temperature;
    
    /**
     * 创建 AI 提取器
     * @param apiKey API 密钥
     * @param baseUrl API 基础 URL
     * @param model 模型名称
     */
    public AIExtractor(String apiKey, String baseUrl, String model) {
        this(apiKey, baseUrl, model, 2000, 0.7);
    }
    
    public AIExtractor(String apiKey, String baseUrl, String model, int maxTokens, double temperature) {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.model = model;
        this.maxTokens = maxTokens;
        this.temperature = temperature;
    }
    
    /**
     * 从环境变量获取 API Key 创建提取器
     */
    public static AIExtractor fromEnv() {
        String apiKey = System.getenv("OPENAI_API_KEY");
        if (apiKey == null || apiKey.isEmpty()) {
            apiKey = System.getenv("AI_API_KEY");
        }
        return new AIExtractor(
            apiKey,
            "https://api.openai.com/v1",
            "gpt-3.5-turbo"
        );
    }
    
    /**
     * 提取结构化数据
     * @param content 页面内容
     * @param instructions 提取指令
     * @param schema JSON Schema 定义
     * @return 提取的数据
     */
    public Map<String, Object> extractStructured(String content, String instructions, Map<String, Object> schema) throws IOException {
        String prompt = String.format(
            "请从以下内容中提取结构化数据。\n\n" +
            "提取要求：%s\n\n" +
            "期望的输出格式（JSON Schema）：\n%s\n\n" +
            "页面内容：\n%s\n\n" +
            "请直接返回符合 JSON Schema 的 JSON 对象，不要包含其他解释。",
            instructions, schema, content
        );
        
        String response = callLLM(prompt);
        return parseJson(response);
    }
    
    /**
     * 页面理解
     * @param content 页面内容
     * @param question 问题
     * @return 回答
     */
    public String understandPage(String content, String question) throws IOException {
        String prompt = String.format(
            "请分析以下网页内容并回答问题。\n\n" +
            "问题：%s\n\n" +
            "页面内容：\n%s\n\n" +
            "请详细回答。",
            question, content
        );
        
        return callLLM(prompt);
    }
    
    /**
     * 生成爬虫配置
     * @param description 自然语言描述
     * @return 配置
     */
    public Map<String, Object> generateSpiderConfig(String description) throws IOException {
        String prompt = String.format(
            "根据以下自然语言描述，生成爬虫配置（JSON 格式）。\n\n" +
            "描述：%s\n\n" +
            "请返回以下格式的 JSON：\n" +
            "{\n" +
            "  \"start_urls\": [\"起始 URL\"],\n" +
            "  \"rules\": [{\"name\": \"规则名称\", \"pattern\": \"URL 匹配模式\", \"extract\": [\"字段\"], \"follow_links\": true}],\n" +
            "  \"settings\": {\"concurrency\": 5, \"max_depth\": 3, \"delay\": 1000}\n" +
            "}\n\n" +
            "只返回 JSON，不要其他解释。",
            description
        );
        
        String response = callLLM(prompt);
        return parseJson(response);
    }
    
    /**
     * 调用 LLM（包内可见）
     */
    String callLLM(String prompt) throws IOException {
        if (apiKey == null || apiKey.isEmpty()) {
            throw new IOException("API key is required");
        }
        
        String requestBody = String.format(
            "{\"model\":\"%s\",\"messages\":[{\"role\":\"user\",\"content\":\"%s\"}],\"max_tokens\":%d,\"temperature\":%.1f}",
            model, escapeJson(prompt), maxTokens, temperature
        );
        
        URL url = new URL(baseUrl + "/chat/completions");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Authorization", "Bearer " + apiKey);
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setDoOutput(true);
        conn.setConnectTimeout(60000);
        conn.setReadTimeout(60000);
        
        try (OutputStream os = conn.getOutputStream()) {
            os.write(requestBody.getBytes(StandardCharsets.UTF_8));
        }
        
        int status = conn.getResponseCode();
        if (status != 200) {
            String errorBody = readStream(conn.getErrorStream());
            throw new IOException("API error: " + status + " - " + errorBody);
        }
        
        String responseBody = readStream(conn.getInputStream());
        return extractContent(responseBody);
    }
    
    /**
     * 从响应中提取内容
     */
    private String extractContent(String jsonResponse) {
        try {
            Map<String, Object> response = parseJson(jsonResponse);
            List<Map<String, Object>> choices = (List<Map<String, Object>>) response.get("choices");
            if (choices != null && !choices.isEmpty()) {
                Map<String, Object> message = (Map<String, Object>) choices.get(0).get("message");
                return (String) message.get("content");
            }
        } catch (Exception e) {
            // Ignore parsing errors
        }
        return jsonResponse;
    }
    
    /**
     * 简单的 JSON 解析（包内可见）
     */
    @SuppressWarnings("unchecked")
    Map<String, Object> parseJson(String json) {
        json = json.trim();
        if (!json.startsWith("{")) {
            // 尝试提取 JSON 部分
            int start = json.indexOf("{");
            int end = json.lastIndexOf("}");
            if (start >= 0 && end > start) {
                json = json.substring(start, end + 1);
            }
        }
        
        Map<String, Object> result = new HashMap<>();
        if (json.isEmpty() || !json.startsWith("{")) {
            result.put("text", json);
            return result;
        }
        
        // 简单解析
        json = json.substring(1, json.length() - 1).trim();
        if (json.isEmpty()) {
            return result;
        }
        
        String[] parts = json.split(",");
        for (String part : parts) {
            String[] kv = part.split(":", 2);
            if (kv.length == 2) {
                String key = kv[0].trim().replaceAll("\"", "");
                String value = kv[1].trim();
                if (value.startsWith("\"") && value.endsWith("\"")) {
                    result.put(key, value.substring(1, value.length() - 1));
                } else if (value.equals("true") || value.equals("false")) {
                    result.put(key, Boolean.parseBoolean(value));
                } else if (value.equals("null")) {
                    result.put(key, null);
                } else {
                    try {
                        result.put(key, Double.parseDouble(value));
                    } catch (NumberFormatException e) {
                        result.put(key, value);
                    }
                }
            }
        }
        
        return result;
    }
    
    private String escapeJson(String text) {
        return text.replace("\\", "\\\\")
                   .replace("\"", "\\\"")
                   .replace("\n", "\\n")
                   .replace("\r", "\\r")
                   .replace("\t", "\\t");
    }
    
    private String readStream(InputStream is) throws IOException {
        if (is == null) return "";
        BufferedReader reader = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            sb.append(line);
        }
        return sb.toString();
    }
}
