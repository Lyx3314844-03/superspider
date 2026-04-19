package com.javaspider.ai;

import java.io.IOException;
import java.util.*;

/**
 * 智能爬虫助手
 * 提供高级 AI 功能
 */
public class SpiderAssistant {
    
    private final AIExtractor extractor;
    
    public SpiderAssistant(String apiKey) {
        this(new AIExtractor(
            apiKey,
            "https://api.openai.com/v1",
            "gpt-5.2"
        ));
    }

    private SpiderAssistant(AIExtractor extractor) {
        this.extractor = extractor;
    }
    
    public static SpiderAssistant fromEnv() {
        return new SpiderAssistant(AIExtractor.fromEnv());
    }
    
    /**
     * 页面分析结果
     */
    public static class PageAnalysis {
        public String pageType;
        public String mainContent;
        public List<LinkInfo> links;
        public List<Entity> entities;
        
        @Override
        public String toString() {
            return "PageAnalysis{type=" + pageType + ", content=" + mainContent + "}";
        }
    }
    
    /**
     * 链接信息
     */
    public static class LinkInfo {
        public String url;
        public String text;
        public String linkType;
    }
    
    /**
     * 实体信息
     */
    public static class Entity {
        public String name;
        public String entityType;
        public String value;
    }
    
    /**
     * 分析页面
     */
    public PageAnalysis analyzePage(String content) throws IOException {
        String prompt = String.format(
            "请分析以下网页内容，返回结构化信息。\n\n" +
            "页面内容：\n%s\n\n" +
            "请返回以下格式的 JSON：\n" +
            "{\n" +
            "  \"page_type\": \"页面类型（如：文章页、列表页、商品页等）\",\n" +
            "  \"main_content\": \"主要内容摘要\",\n" +
            "  \"links\": [{\"url\": \"链接\", \"text\": \"链接文本\", \"link_type\": \"链接类型\"}],\n" +
            "  \"entities\": [{\"name\": \"实体名\", \"entity_type\": \"实体类型\", \"value\": \"值\"}]\n" +
            "}",
            content
        );
        
        String response = extractor.callLLM(prompt);
        return parsePageAnalysis(response);
    }
    
    /**
     * 判断是否需要爬取
     */
    public boolean shouldCrawl(String content, String criteria) throws IOException {
        String prompt = String.format(
            "请判断是否应该爬取以下页面。\n\n" +
            "爬取标准：%s\n\n" +
            "页面内容：\n%s\n\n" +
            "请只返回 true 或 false。",
            criteria, content
        );
        
        String response = extractor.callLLM(prompt);
        return response.trim().equalsIgnoreCase("true");
    }
    
    /**
     * 提取指定字段
     */
    public Map<String, Object> extractFields(String content, List<String> fields) throws IOException {
        String prompt = String.format(
            "请从以下内容中提取指定字段。\n\n" +
            "需要提取的字段：%s\n\n" +
            "页面内容：\n%s\n\n" +
            "请返回包含这些字段的 JSON 对象。",
            fields, content
        );
        
        return extractor.callLLM(prompt).isEmpty() ? 
            new HashMap<>() : 
            extractor.parseJson(extractor.callLLM(prompt));
    }
    
    @SuppressWarnings("unchecked")
    private PageAnalysis parsePageAnalysis(String json) {
        PageAnalysis analysis = new PageAnalysis();
        
        try {
            Map<String, Object> data = extractor.parseJson(json);
            analysis.pageType = (String) data.get("page_type");
            analysis.mainContent = (String) data.get("main_content");
            
            List<Object> links = (List<Object>) data.get("links");
            if (links != null) {
                analysis.links = new ArrayList<>();
                for (Object link : links) {
                    if (link instanceof Map) {
                        Map<String, Object> linkMap = (Map<String, Object>) link;
                        LinkInfo info = new LinkInfo();
                        info.url = String.valueOf(linkMap.get("url"));
                        info.text = String.valueOf(linkMap.get("text"));
                        info.linkType = String.valueOf(linkMap.get("link_type"));
                        analysis.links.add(info);
                    }
                }
            }
            
            List<Object> entities = (List<Object>) data.get("entities");
            if (entities != null) {
                analysis.entities = new ArrayList<>();
                for (Object entity : entities) {
                    if (entity instanceof Map) {
                        Map<String, Object> entityMap = (Map<String, Object>) entity;
                        Entity e = new Entity();
                        e.name = String.valueOf(entityMap.get("name"));
                        e.entityType = String.valueOf(entityMap.get("entity_type"));
                        e.value = String.valueOf(entityMap.get("value"));
                        analysis.entities.add(e);
                    }
                }
            }
        } catch (Exception e) {
            // Ignore parsing errors
        }
        
        return analysis;
    }
}
