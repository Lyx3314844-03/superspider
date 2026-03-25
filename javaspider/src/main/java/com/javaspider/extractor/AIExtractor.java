package com.javaspider.extractor;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.*;

/**
 * AI 内容提取器
 * 使用 LLM API 进行智能内容提取
 */
public class AIExtractor {
    private static final Logger logger = LoggerFactory.getLogger(AIExtractor.class);

    private final String apiKey;
    private final AIProvider provider;
    private final String model;
    private final double temperature;
    private final int maxTokens;

    public enum AIProvider {
        OPENAI,
        ANTHROPIC,
        AZURE,
        CUSTOM
    }

    public AIExtractor(String apiKey, AIProvider provider) {
        this(apiKey, provider, null, 0.7, 2000);
    }

    public AIExtractor(String apiKey, AIProvider provider, String model, double temperature, int maxTokens) {
        this.apiKey = apiKey;
        this.provider = provider;
        this.model = model != null ? model : getDefaultModel(provider);
        this.temperature = temperature;
        this.maxTokens = maxTokens;
    }

    private String getDefaultModel(AIProvider provider) {
        switch (provider) {
            case OPENAI:
                return "gpt-3.5-turbo";
            case ANTHROPIC:
                return "claude-3-haiku-20240307";
            case AZURE:
                return "gpt-35-turbo";
            default:
                return "gpt-3.5-turbo";
        }
    }

    /**
     * 提取结构化数据
     * @param content HTML 或文本内容
     * @param schema JSON Schema 定义期望的输出结构
     * @return 提取的结构化数据
     */
    public Map<String, Object> extract(String content, String schema) {
        String prompt = buildExtractionPrompt(content, schema);
        String response = callAPI(prompt);
        return parseResponse(response);
    }

    /**
     * 提取指定字段
     */
    public Map<String, Object> extractFields(String content, List<String> fields) {
        String schema = buildSchemaFromFields(fields);
        return extract(content, schema);
    }

    /**
     * 提取列表数据
     */
    public List<Map<String, Object>> extractList(String content, String itemSchema) {
        String prompt = String.format(
            "Extract all items from the following content as a JSON array. " +
            "Each item should match this schema: %s\n\nContent:\n%s",
            itemSchema, content
        );
        String response = callAPI(prompt);
        return parseListResponse(response);
    }

    /**
     * 总结内容
     */
    public String summarize(String content) {
        return summarize(content, 200);
    }

    /**
     * 总结内容（指定长度）
     */
    public String summarize(String content, int maxLength) {
        String prompt = String.format(
            "Summarize the following content in %d characters or less:\n\n%s",
            maxLength, content
        );
        return callAPI(prompt);
    }

    /**
     * 分类内容
     */
    public String classify(String content, List<String> categories) {
        String prompt = String.format(
            "Classify the following content into one of these categories: %s\n\nContent:\n%s\n\nCategory:",
            String.join(", ", categories), content
        );
        return callAPI(prompt).trim();
    }

    /**
     * 情感分析
     */
    public SentimentResult analyzeSentiment(String content) {
        String prompt = "Analyze the sentiment of the following text. Return JSON with 'sentiment' (positive/negative/neutral) and 'confidence' (0-1):\n\n" + content;
        String response = callAPI(prompt);
        
        try {
            com.google.gson.Gson gson = new com.google.gson.Gson();
            Map<String, Object> result = gson.fromJson(response, Map.class);
            return new SentimentResult(
                String.valueOf(result.get("sentiment")),
                Double.parseDouble(String.valueOf(result.get("confidence")))
            );
        } catch (Exception e) {
            logger.error("Failed to parse sentiment result", e);
            return new SentimentResult("unknown", 0.0);
        }
    }

    /**
     * 提取关键词
     */
    public List<String> extractKeywords(String content) {
        return extractKeywords(content, 10);
    }

    /**
     * 提取关键词（指定数量）
     */
    public List<String> extractKeywords(String content, int maxKeywords) {
        String prompt = String.format(
            "Extract top %d keywords/phrases from the following content as a JSON array:\n\n%s",
            maxKeywords, content
        );
        String response = callAPI(prompt);
        
        try {
            com.google.gson.Gson gson = new com.google.gson.Gson();
            List<String> keywords = gson.fromJson(response, List.class);
            return keywords != null ? keywords : new ArrayList<>();
        } catch (Exception e) {
            logger.error("Failed to parse keywords", e);
            return new ArrayList<>();
        }
    }

    /**
     * 实体识别
     */
    public Map<String, List<String>> extractEntities(String content) {
        String prompt = "Extract named entities from the following text. Return JSON with categories as keys and entity lists as values:\n\n" + content;
        String response = callAPI(prompt);
        
        try {
            com.google.gson.Gson gson = new com.google.gson.Gson();
            return gson.fromJson(response, Map.class);
        } catch (Exception e) {
            logger.error("Failed to parse entities", e);
            return new HashMap<>();
        }
    }

    /**
     * 问答
     */
    public String answerQuestion(String content, String question) {
        String prompt = String.format(
            "Answer the following question based on the provided context:\n\nContext:\n%s\n\nQuestion: %s\n\nAnswer:",
            content, question
        );
        return callAPI(prompt);
    }

    /**
     * 翻译
     */
    public String translate(String content, String targetLanguage) {
        String prompt = String.format(
            "Translate the following text to %s:\n\n%s",
            targetLanguage, content
        );
        return callAPI(prompt);
    }

    /**
     * 构建提取提示
     */
    private String buildExtractionPrompt(String content, String schema) {
        return String.format(
            "Extract structured data from the following content according to this JSON schema:\n%s\n\nContent:\n%s\n\nExtracted data (JSON only):",
            schema, content
        );
    }

    /**
     * 从字段构建 Schema
     */
    private String buildSchemaFromFields(List<String> fields) {
        StringBuilder sb = new StringBuilder("{\n  \"type\": \"object\",\n  \"properties\": {\n");
        for (int i = 0; i < fields.size(); i++) {
            sb.append("    \"").append(fields.get(i)).append("\": {\"type\": \"string\"}");
            if (i < fields.size() - 1) {
                sb.append(",");
            }
            sb.append("\n");
        }
        sb.append("  }\n}");
        return sb.toString();
    }

    /**
     * 调用 AI API
     */
    private String callAPI(String prompt) {
        try {
            String endpoint = getEndpoint(provider);
            String requestBody = buildRequestBody(prompt);
            
            HttpURLConnection conn = (HttpURLConnection) new URL(endpoint).openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("Authorization", "Bearer " + apiKey);
            conn.setDoOutput(true);
            conn.setConnectTimeout(30000);
            conn.setReadTimeout(60000);
            
            try (OutputStream os = conn.getOutputStream()) {
                os.write(requestBody.getBytes(StandardCharsets.UTF_8));
            }
            
            int statusCode = conn.getResponseCode();
            InputStream is = statusCode >= 200 && statusCode < 300 ? 
                conn.getInputStream() : conn.getErrorStream();
            
            String response = new String(is.readAllBytes(), StandardCharsets.UTF_8);
            
            if (statusCode >= 200 && statusCode < 300) {
                return extractContentFromResponse(response);
            } else {
                logger.error("API error: {} - {}", statusCode, response);
                throw new RuntimeException("API error: " + statusCode);
            }
        } catch (IOException e) {
            logger.error("Failed to call AI API", e);
            throw new RuntimeException("Failed to call AI API", e);
        }
    }

    private String getEndpoint(AIProvider provider) {
        switch (provider) {
            case OPENAI:
                return "https://api.openai.com/v1/chat/completions";
            case ANTHROPIC:
                return "https://api.anthropic.com/v1/messages";
            case AZURE:
                return "https://your-resource.openai.azure.com/openai/deployments/" + model + "/chat/completions";
            default:
                return "https://api.openai.com/v1/chat/completions";
        }
    }

    private String buildRequestBody(String prompt) {
        com.google.gson.Gson gson = new com.google.gson.Gson();

        if (provider == AIProvider.ANTHROPIC) {
            Map<String, Object> body = new HashMap<>();
            body.put("model", model);
            body.put("max_tokens", maxTokens);
            Map<String, String> message = new HashMap<>();
            message.put("role", "user");
            message.put("content", prompt);
            body.put("messages", Arrays.asList(message));
            return gson.toJson(body);
        } else {
            Map<String, Object> body = new HashMap<>();
            body.put("model", model);
            Map<String, String> message = new HashMap<>();
            message.put("role", "user");
            message.put("content", prompt);
            body.put("messages", Arrays.asList(message));
            body.put("temperature", temperature);
            body.put("max_tokens", maxTokens);
            return gson.toJson(body);
        }
    }

    private String extractContentFromResponse(String response) {
        try {
            com.google.gson.Gson gson = new com.google.gson.Gson();
            Map<String, Object> result = gson.fromJson(response, Map.class);
            
            if (provider == AIProvider.ANTHROPIC) {
                List<Map<String, Object>> content = (List<Map<String, Object>>) result.get("content");
                if (content != null && !content.isEmpty()) {
                    return String.valueOf(content.get(0).get("text"));
                }
            } else {
                List<Map<String, Object>> choices = (List<Map<String, Object>>) result.get("choices");
                if (choices != null && !choices.isEmpty()) {
                    Map<String, Object> message = (Map<String, Object>) choices.get(0).get("message");
                    return String.valueOf(message.get("content"));
                }
            }
        } catch (Exception e) {
            logger.error("Failed to parse response", e);
        }
        
        return response;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseResponse(String response) {
        try {
            com.google.gson.Gson gson = new com.google.gson.Gson();
            return gson.fromJson(response, Map.class);
        } catch (Exception e) {
            logger.error("Failed to parse response", e);
            return new HashMap<>();
        }
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> parseListResponse(String response) {
        try {
            com.google.gson.Gson gson = new com.google.gson.Gson();
            return gson.fromJson(response, List.class);
        } catch (Exception e) {
            logger.error("Failed to parse list response", e);
            return new ArrayList<>();
        }
    }

    /**
     * 创建 AIExtractor
     */
    public static AIExtractor openai(String apiKey) {
        return new AIExtractor(apiKey, AIProvider.OPENAI);
    }

    public static AIExtractor openai(String apiKey, String model) {
        return new AIExtractor(apiKey, AIProvider.OPENAI, model, 0.7, 2000);
    }

    public static AIExtractor anthropic(String apiKey) {
        return new AIExtractor(apiKey, AIProvider.ANTHROPIC);
    }

    public static AIExtractor azure(String apiKey, String model) {
        return new AIExtractor(apiKey, AIProvider.AZURE, model, 0.7, 2000);
    }

    /**
     * 情感分析结果
     */
    public static class SentimentResult {
        private final String sentiment;
        private final double confidence;

        public SentimentResult(String sentiment, double confidence) {
            this.sentiment = sentiment;
            this.confidence = confidence;
        }

        public String getSentiment() {
            return sentiment;
        }

        public double getConfidence() {
            return confidence;
        }

        @Override
        public String toString() {
            return String.format("Sentiment{sentiment='%s', confidence=%.2f}", sentiment, confidence);
        }
    }
}
