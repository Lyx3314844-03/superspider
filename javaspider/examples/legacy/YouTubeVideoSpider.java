package com.javaspider.examples;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javaspider.core.Page;
import com.javaspider.core.Request;
import com.javaspider.core.Site;
import com.javaspider.core.Spider;
import com.javaspider.nodereverse.NodeReverseClient;
import com.javaspider.processor.BasePageProcessor;
import com.javaspider.selector.Selectable;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * YouTube 视频爬取与 Node.js 逆向分析示例
 * 
 * 功能:
 * 1. 爬取 YouTube 视频页面
 * 2. 使用 Node.js 逆向服务分析加密算法
 * 3. 提取视频信息和播放列表
 * 4. 解密视频流 URL
 * 
 * @author JavaSpider
 * @version 1.0.0
 */
@Deprecated(since = "2.1.0", forRemoval = false)
public class YouTubeVideoSpider extends BasePageProcessor {

    private final NodeReverseClient reverseClient;
    private final ObjectMapper objectMapper;
    private Site site;
    
    // YouTube 视频 URL
    private static final String TARGET_URL = "https://www.youtube.com/watch?v=Qk-ROQkkloE&list=RDQk-ROQkkloE&start_radio=1";
    private static final String REVERSE_SERVICE_URL = "http://localhost:3000";

    public YouTubeVideoSpider() {
        this.reverseClient = new NodeReverseClient(REVERSE_SERVICE_URL);
        this.objectMapper = new ObjectMapper();
        this.site = Site.me()
                .setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                .setRetryTimes(3)
                .addHeader("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8")
                .addHeader("Accept-Language", "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7")
                .addHeader("Accept-Encoding", "gzip, deflate, br")
                .addHeader("Connection", "keep-alive")
                .addHeader("Upgrade-Insecure-Requests", "1")
                .addHeader("Sec-Fetch-Dest", "document")
                .addHeader("Sec-Fetch-Mode", "navigate")
                .addHeader("Sec-Fetch-Site", "none")
                .addHeader("Sec-Fetch-User", "?1")
                .addHeader("Sec-Ch-Ua", "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"")
                .addHeader("Sec-Ch-Ua-Mobile", "?0")
                .addHeader("Sec-Ch-Ua-Platform", "\"Windows\"")
                .addCookie("CONSENT", "YES+cb.20210720-07-p0.en+FX+111");
    }

    @Override
    public Site getSite() {
        return site;
    }

    @Override
    public void process(Page page) {
        try {
            System.out.println("=".repeat(80));
            System.out.println("🎬 YouTube 视频爬取与 Node.js 逆向分析");
            System.out.println("=".repeat(80));
            
            // 步骤 1: 检查 Node.js 逆向服务是否可用
            System.out.println("\n[步骤 1] 检查 Node.js 逆向服务...");
            boolean serviceAvailable = reverseClient.healthCheck();
            if (!serviceAvailable) {
                System.err.println("❌ Node.js 逆向服务不可用，请先启动服务:");
                System.err.println("   cd C:\\Users\\Administrator\\spider\\node-reverse-server");
                System.err.println("   npm start");
                page.setSkip(true);
                return;
            }
            System.out.println("✅ Node.js 逆向服务正常运行");

            // 步骤 2: 获取页面 HTML
            System.out.println("\n[步骤 2] 获取 YouTube 视频页面...");
            String html = page.getHtml().getDocumentHtml();
            if (html == null || html.isEmpty()) {
                System.out.println("⚠️  页面为空，可能是反爬限制");
                // 尝试分析是否有加密
                analyzePageEncryption(page);
                return;
            }
            System.out.println("✅ 页面获取成功，大小: " + html.length() + " 字节");

            // 步骤 3: 分析页面中的加密算法
            System.out.println("\n[步骤 3] 使用 Node.js 逆向服务分析加密...");
            analyzeYouTubeEncryption(html);

            // 步骤 4: 提取视频基本信息
            System.out.println("\n[步骤 4] 提取视频基本信息...");
            extractVideoInfo(page, html);

            // 步骤 5: 提取播放列表信息
            System.out.println("\n[步骤 5] 提取播放列表信息...");
            extractPlaylistInfo(html);

            // 步骤 6: 尝试提取视频流信息
            System.out.println("\n[步骤 6] 分析视频流加密...");
            analyzeVideoStreams(html);

            // 步骤 7: 执行混淆的 JavaScript 代码
            System.out.println("\n[步骤 7] 执行页面中的混淆代码...");
            executeObfuscatedJS(html);

            System.out.println("\n" + "=".repeat(80));
            System.out.println("✅ 爬取和逆向分析完成！");
            System.out.println("=".repeat(80));

        } catch (Exception e) {
            System.err.println("❌ 处理页面时出错: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * 分析页面是否被加密
     */
    private void analyzePageEncryption(Page page) {
        try {
            String content = page.getRawText();
            if (content != null && !content.isEmpty()) {
                JsonNode result = reverseClient.analyzeCrypto(content);
                if (result.get("success").asBoolean()) {
                    JsonNode cryptoTypes = result.get("cryptoTypes");
                    if (cryptoTypes != null && cryptoTypes.isArray() && cryptoTypes.size() > 0) {
                        System.out.println("🔒 检测到页面加密:");
                        for (JsonNode crypto : cryptoTypes) {
                            System.out.printf("  - 算法: %s (置信度: %.2f)\n", 
                                crypto.get("name").asText(), 
                                crypto.get("confidence").asDouble());
                        }
                    }
                }
            }
        } catch (IOException e) {
            System.err.println("分析加密失败: " + e.getMessage());
        }
    }

    /**
     * 分析 YouTube 页面的加密算法
     */
    private void analyzeYouTubeEncryption(String html) throws IOException {
        // 提取 <script> 标签中的代码
        List<String> scripts = extractScripts(html);
        
        System.out.println("📊 共找到 " + scripts.size() + " 个 <script> 标签");
        
        // 分析包含 CryptoJS 或加密相关代码的脚本
        int encryptedCount = 0;
        for (int i = 0; i < Math.min(scripts.size(), 10); i++) {
            String script = scripts.get(i);
            
            // 只分析包含加密关键字的脚本
            if (script.contains("CryptoJS") || script.contains("encrypt") || 
                script.contains("decrypt") || script.contains("signature") ||
                script.contains("cipher")) {
                
                System.out.println("\n🔍 分析脚本 #" + (i+1) + "...");
                JsonNode result = reverseClient.analyzeCrypto(script);

                if (result.get("success").asBoolean()) {
                    JsonNode cryptoTypes = result.get("cryptoTypes");
                    if (cryptoTypes != null && cryptoTypes.isArray() && cryptoTypes.size() > 0) {
                        encryptedCount++;
                        System.out.println("  ✅ 检测到加密算法:");
                        for (JsonNode crypto : cryptoTypes) {
                            System.out.printf("    - %s (置信度: %.2f)\n", 
                                crypto.get("name").asText(), 
                                crypto.get("confidence").asDouble());
                        }
                    }
                    
                    // 输出检测到的密钥
                    if (result.get("keys") != null && result.get("keys").isArray() && result.get("keys").size() > 0) {
                        System.out.println("  🔑 检测到的密钥:");
                        for (JsonNode key : result.get("keys")) {
                            System.out.println("    - " + key.asText());
                        }
                    }
                }
            }
        }
        
        if (encryptedCount == 0) {
            System.out.println("ℹ️  未在前 10 个脚本中检测到明显的加密算法");
        } else {
            System.out.println("\n📈 总计检测到 " + encryptedCount + " 个加密脚本");
        }
    }

    /**
     * 提取视频基本信息
     */
    private void extractVideoInfo(Page page, String html) {
        try {
            // 提取视频标题
            String title = extractPattern(html, "<title>(.*?)</title>");
            if (title != null) {
                title = title.replace(" - YouTube", "").trim();
                System.out.println("📹 视频标题: " + title);
            }

            // 提取视频 ID
            String videoId = extractPattern(html, "\"videoId\":\"([^\"]+)\"");
            if (videoId != null) {
                System.out.println("🆔 视频 ID: " + videoId);
            }

            // 提取频道名称
            String channel = extractPattern(html, "\"ownerProfileUrl\":\"[^\"]+\",\"text\":\"([^\"]+)\"");
            if (channel != null) {
                System.out.println("👤 频道: " + channel);
            }

            // 提取观看次数
            String views = extractPattern(html, "\"viewCount\":\"?(\\d+)\"?");
            if (views != null) {
                System.out.println("👁️  观看次数: " + views);
            }

        } catch (Exception e) {
            System.err.println("提取视频信息失败: " + e.getMessage());
        }
    }

    /**
     * 提取播放列表信息
     */
    private void extractPlaylistInfo(String html) {
        try {
            // 提取播放列表 ID
            String playlistId = extractPattern(html, "\"playlistId\":\"([^\"]+)\"");
            if (playlistId != null) {
                System.out.println("📋 播放列表 ID: " + playlistId);
            }

            // 提取播放列表视频数量
            String videoCount = extractPattern(html, "\"videoCount\":(\\d+)");
            if (videoCount != null) {
                System.out.println("📊 播放列表视频数: " + videoCount);
            }

            // 提取播放列表中的视频
            Pattern videoPattern = Pattern.compile("\"videoId\":\"([^\"]+)\"");
            Matcher matcher = videoPattern.matcher(html);
            List<String> videoIds = new ArrayList<>();
            
            while (matcher.find() && videoIds.size() < 10) {
                String vid = matcher.group(1);
                if (!videoIds.contains(vid)) {
                    videoIds.add(vid);
                }
            }
            
            if (!videoIds.isEmpty()) {
                System.out.println("🎬 播放列表中的视频:");
                for (int i = 0; i < videoIds.size(); i++) {
                    System.out.printf("  %d. https://www.youtube.com/watch?v=%s\n", 
                        i+1, videoIds.get(i));
                }
            }

        } catch (Exception e) {
            System.err.println("提取播放列表信息失败: " + e.getMessage());
        }
    }

    /**
     * 分析视频流加密
     */
    private void analyzeVideoStreams(String html) throws IOException {
        // 查找 cipher 或 signature 相关代码
        Pattern cipherPattern = Pattern.compile(
            "(function.*?cipher.*?\\{.*?\\})", 
            Pattern.DOTALL
        );
        Matcher matcher = cipherPattern.matcher(html);
        
        if (matcher.find()) {
            String cipherCode = matcher.group(1);
            System.out.println("🔐 找到 cipher 函数代码 (前200字符):");
            System.out.println(cipherCode.substring(0, Math.min(200, cipherCode.length())));
            
            // 使用 AST 分析
            JsonNode astResult = reverseClient.analyzeAST(cipherCode, 
                List.of("crypto", "obfuscation"));
            
            if (astResult.get("success").asBoolean()) {
                JsonNode results = astResult.get("results");
                if (results.get("crypto").isArray() && results.get("crypto").size() > 0) {
                    System.out.println("🔍 AST 分析结果 - 加密调用:");
                    for (JsonNode crypto : results.get("crypto")) {
                        System.out.printf("  - %s (行 %d)\n", 
                            crypto.get("name").asText(),
                            crypto.get("line").asInt());
                    }
                }
            }
            
            // 尝试执行 cipher 函数
            System.out.println("\n🧪 尝试执行 cipher 函数...");
            try {
                JsonNode execResult = reverseClient.executeJS(
                    cipherCode + "\n_cipher('test');",
                    null,
                    5000
                );
                System.out.println("执行结果: " + execResult);
            } catch (Exception e) {
                System.out.println("执行失败 (预期): " + e.getMessage());
            }
        } else {
            System.out.println("ℹ️  未找到 cipher 函数");
        }
    }

    /**
     * 执行页面中的混淆 JavaScript 代码
     */
    private void executeObfuscatedJS(String html) throws IOException {
        // 查找 eval 或混淆的代码
        Pattern evalPattern = Pattern.compile(
            "eval\\(function\\(p,a,c,k,e,d\\).*?\\)",
            Pattern.DOTALL
        );
        Matcher matcher = evalPattern.matcher(html);
        
        if (matcher.find()) {
            String evalCode = matcher.group();
            System.out.println("📦 找到混淆代码 (前100字符):");
            System.out.println(evalCode.substring(0, Math.min(100, evalCode.length())));
            
            // 尝试执行
            System.out.println("\n🧪 尝试执行混淆代码...");
            try {
                JsonNode result = reverseClient.executeJS(
                    evalCode,
                    null,
                    5000
                );
                System.out.println("✅ 执行成功!");
                System.out.println("结果: " + result.get("result"));
            } catch (Exception e) {
                System.out.println("❌ 执行失败: " + e.getMessage());
            }
        } else {
            System.out.println("ℹ️  未找到 eval 混淆代码");
        }
    }

    /**
     * 从 HTML 中提取 <script> 标签内容
     */
    private List<String> extractScripts(String html) {
        List<String> scripts = new ArrayList<>();
        Pattern scriptPattern = Pattern.compile(
            "<script[^>]*>(.*?)</script>",
            Pattern.DOTALL
        );
        Matcher matcher = scriptPattern.matcher(html);
        
        while (matcher.find()) {
            String script = matcher.group(1).trim();
            if (!script.isEmpty() && !script.startsWith("<!--")) {
                scripts.add(script);
            }
        }
        
        return scripts;
    }

    /**
     * 使用正则表达式提取内容
     */
    private String extractPattern(String html, String pattern) {
        Pattern p = Pattern.compile(pattern);
        Matcher m = p.matcher(html);
        if (m.find()) {
            return m.group(1);
        }
        return null;
    }

    /**
     * 主函数 - 启动爬虫
     */
    public static void main(String[] args) {
        System.out.println("🚀 启动 YouTube 视频爬取与 Node.js 逆向分析...");
        System.out.println("目标URL: " + TARGET_URL);
        System.out.println("逆向服务: " + REVERSE_SERVICE_URL);
        System.out.println();

        // 创建爬虫实例
        YouTubeVideoSpider processor = new YouTubeVideoSpider();

        // 创建并配置爬虫
        Spider spider = Spider.create(processor)
                .name("YouTubeVideoSpider")
                .addUrl(TARGET_URL)
                .thread(1);

        System.out.println("爬虫配置:");
        System.out.println("  - 名称: YouTubeVideoSpider");
        System.out.println("  - 线程数: 1");
        System.out.println("  - 目标: " + TARGET_URL);
        System.out.println();

        // 开始爬取
        System.out.println("开始爬取...\n");
        spider.start();
    }
}
