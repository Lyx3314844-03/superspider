package com.javaspider.ai;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/**
 * AI 提取器 - 集成 LLM 进行智能内容提取
 * 支持 OpenAI GPT、Anthropic Claude 等
 */
public class AIExtractor {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
    
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
        return fromEnvironment(System.getenv());
    }

    static AIExtractor fromEnvironment(Map<String, String> env) {
        String apiKey = firstNonBlank(
            env.get("OPENAI_API_KEY"),
            env.get("AI_API_KEY")
        );
        String baseUrl = firstNonBlank(
            env.get("OPENAI_BASE_URL"),
            env.get("AI_BASE_URL"),
            "https://api.openai.com/v1"
        );
        String model = firstNonBlank(
            env.get("OPENAI_MODEL"),
            env.get("AI_MODEL"),
            "gpt-3.5-turbo"
        );
        int maxTokens = parseInt(env.get("AI_MAX_TOKENS"), 2000);
        double temperature = parseDouble(env.get("AI_TEMPERATURE"), 0.7);
        return new AIExtractor(
            apiKey,
            baseUrl,
            model,
            maxTokens,
            temperature
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
        String schemaJson;
        try {
            schemaJson = OBJECT_MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(schema);
        } catch (Exception ignored) {
            schemaJson = String.valueOf(schema);
        }
        String prompt = String.format(
            "请从以下内容中提取结构化数据。\n\n" +
            "提取要求：%s\n\n" +
            "期望的输出格式（JSON Schema）：\n%s\n\n" +
            "页面内容：\n%s\n\n" +
            "请直接返回符合 JSON Schema 的 JSON 对象，不要包含其他解释。",
            instructions, schemaJson, content
        );
        
        String response = callLLM(prompt);
        return SchemaNormalizer.normalizeObject(schema, parseJson(response), Map.of());
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
            JsonNode root = OBJECT_MAPPER.readTree(jsonResponse);
            JsonNode choices = root.path("choices");
            if (choices.isArray() && !choices.isEmpty()) {
                JsonNode content = choices.get(0).path("message").path("content");
                if (!content.isMissingNode() && !content.isNull()) {
                    return content.asText();
                }
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
        String candidate = extractJsonCandidate(json);
        Map<String, Object> result = new LinkedHashMap<>();
        if (candidate.isEmpty()) {
            result.put("text", json == null ? "" : json);
            return result;
        }

        try {
            JsonNode root = OBJECT_MAPPER.readTree(candidate);
            if (root.isObject()) {
                return convertObject(root);
            }
            if (root.isArray()) {
                result.put("items", convertNode(root));
                return result;
            }
            result.put("value", convertNode(root));
            return result;
        } catch (Exception ignored) {
            result.put("text", json == null ? "" : json.trim());
            return result;
        }
    }

    private String extractJsonCandidate(String input) {
        if (input == null) {
            return "";
        }
        String trimmed = input.trim();
        if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
            return trimmed;
        }

        int objectStart = trimmed.indexOf('{');
        int objectEnd = trimmed.lastIndexOf('}');
        if (objectStart >= 0 && objectEnd > objectStart) {
            return trimmed.substring(objectStart, objectEnd + 1);
        }

        int arrayStart = trimmed.indexOf('[');
        int arrayEnd = trimmed.lastIndexOf(']');
        if (arrayStart >= 0 && arrayEnd > arrayStart) {
            return trimmed.substring(arrayStart, arrayEnd + 1);
        }

        return "";
    }

    private Map<String, Object> convertObject(JsonNode node) {
        Map<String, Object> result = new LinkedHashMap<>();
        Iterator<Map.Entry<String, JsonNode>> fields = node.fields();
        while (fields.hasNext()) {
            Map.Entry<String, JsonNode> entry = fields.next();
            result.put(entry.getKey(), convertNode(entry.getValue()));
        }
        return result;
    }

    private List<Object> convertArray(JsonNode node) {
        List<Object> result = new ArrayList<>();
        for (JsonNode item : node) {
            result.add(convertNode(item));
        }
        return result;
    }

    private Object convertNode(JsonNode node) {
        if (node == null || node.isNull()) {
            return null;
        }
        if (node.isObject()) {
            return convertObject(node);
        }
        if (node.isArray()) {
            return convertArray(node);
        }
        if (node.isBoolean()) {
            return node.asBoolean();
        }
        if (node.isIntegralNumber()) {
            return node.asLong();
        }
        if (node.isFloatingPointNumber()) {
            return node.asDouble();
        }
        return node.asText();
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

    String baseUrl() {
        return baseUrl;
    }

    String model() {
        return model;
    }

    int maxTokens() {
        return maxTokens;
    }

    double temperature() {
        return temperature;
    }

    private static String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return null;
    }

    private static int parseInt(String raw, int fallback) {
        if (raw == null || raw.isBlank()) {
            return fallback;
        }
        try {
            return Integer.parseInt(raw.trim());
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    private static double parseDouble(String raw, double fallback) {
        if (raw == null || raw.isBlank()) {
            return fallback;
        }
        try {
            return Double.parseDouble(raw.trim());
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }
}
