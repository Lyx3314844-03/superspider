package com.javaspider.nodereverse;

import com.fasterxml.jackson.databind.JsonNode;
import com.javaspider.core.Page;
import com.javaspider.core.Request;
import com.javaspider.core.Site;
import com.javaspider.core.Spider;
import com.javaspider.processor.BasePageProcessor;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

/**
 * Node.js 逆向处理器示例
 * 演示如何在爬虫流程中集成逆向能力
 */
public class NodeReverseProcessor extends BasePageProcessor {

    private final NodeReverseClient reverseClient;
    private Site site = Site.me();

    public NodeReverseProcessor() {
        this.reverseClient = new NodeReverseClient();
    }

    public NodeReverseProcessor(String baseUrl) {
        this.reverseClient = new NodeReverseClient(baseUrl);
    }

    @Override
    public Site getSite() {
        return site;
    }

    public NodeReverseProcessor setSite(Site site) {
        this.site = site;
        return this;
    }

    @Override
    public void process(Page page) {
        // 获取页面内容
        String html = page.getHtml().toString();
        
        // 示例1: 分析页面中的加密算法
        analyzePageCrypto(page, html);
        
        // 示例2: 提取加密参数并解密
        decryptRequestParams(page);
        
        // 示例3: 分析JavaScript代码
        analyzeJavaScript(page);
    }
    
    /**
     * 分析页面中的加密算法
     */
    private void analyzePageCrypto(Page page, String html) {
        try {
            // 提取<script>标签中的代码
            String jsCode = extractJavaScriptCode(html);
            
            if (jsCode != null && !jsCode.isEmpty()) {
                JsonNode result = reverseClient.analyzeCrypto(jsCode);
                
                if (result.get("success").asBoolean()) {
                    JsonNode cryptoTypes = result.get("data").get("cryptoTypes");
                    if (cryptoTypes.size() > 0) {
                        page.putField("crypto_detected", cryptoTypes);
                        System.out.println("检测到加密算法: " + cryptoTypes);
                    }
                }
            }
        } catch (IOException e) {
            page.setError("Crypto analysis failed: " + e.getMessage());
        }
    }
    
    /**
     * 解密请求参数
     */
    private void decryptRequestParams(Page page) {
        try {
            // 假设我们从某个API获取了加密数据
            JsonNode json = page.getJson();
            if (json == null) return;
            
            // 使用 Jackson 的 at() 方法访问 JSON 路径
            JsonNode encryptedNode = json.at("/encrypted_data");
            if (encryptedNode.isMissingNode() || encryptedNode.isNull()) return;
            
            String encryptedData = encryptedNode.asText();
            String key = "mysecretkey12345";
            String iv = "myiv123456789012";

            if (encryptedData != null && !encryptedData.isEmpty()) {
                JsonNode result = reverseClient.decrypt("AES", encryptedData, key, iv, "CBC");

                if (result != null && result.has("success") && result.get("success").asBoolean()) {
                    String decrypted = result.at("/data/decrypted").asText();
                    page.putField("decrypted_data", decrypted);
                    System.out.println("解密成功: " + decrypted);
                }
            }
        } catch (Exception e) {
            // 解密失败，继续正常流程
        }
    }
    
    /**
     * 分析JavaScript代码
     */
    private void analyzeJavaScript(Page page) {
        try {
            String jsCode = page.getHtml().css("script").toString();
            
            if (jsCode != null) {
                Map<String, Object> options = new HashMap<>();
                options.put("functions", true);
                options.put("calls", true);
                options.put("crypto", true);
                
                JsonNode result = reverseClient.extractAST(jsCode, options);
                
                if (result.get("success").asBoolean()) {
                    page.putField("ast_analysis", result.get("data"));
                }
            }
        } catch (Exception e) {
            // AST分析失败，不影响正常流程
        }
    }
    
    /**
     * 从HTML中提取JavaScript代码
     */
    private String extractJavaScriptCode(String html) {
        // 简化实现，实际应该使用正则或HTML解析器
        int start = html.indexOf("<script");
        int end = html.indexOf("</script>");
        
        if (start != -1 && end != -1) {
            int codeStart = html.indexOf(">", start) + 1;
            return html.substring(codeStart, end);
        }
        
        return null;
    }
    
    /**
     * 创建并启动爬虫示例
     */
    public static void main(String[] args) {
        NodeReverseProcessor processor = new NodeReverseProcessor();
        
        Spider.create(processor)
                .name("NodeReverseExample")
                .thread(5)
                .addUrl("https://example.com")
                .start();
    }
}
