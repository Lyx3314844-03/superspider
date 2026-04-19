package com.javaspider.encrypted;

import com.fasterxml.jackson.databind.JsonNode;
import com.javaspider.core.Page;
import com.javaspider.core.Request;
import com.javaspider.core.Site;
import com.javaspider.core.Spider;
import com.javaspider.nodereverse.NodeReverseClient;
import com.javaspider.processor.BasePageProcessor;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 加密网站爬取处理器
 * 
 * 功能:
 * 1. 自动检测页面加密类型
 * 2. 自动解密加密内容
 * 3. 浏览器环境模拟
 * 4. 签名算法逆向
 * 5. 混淆代码执行
 * 6. Webpack 打包分析
 * 
 * @author JavaSpider Team
 * @version 2.0.0
 */
public class EncryptedSiteProcessor extends BasePageProcessor {

    private final NodeReverseClient reverseClient;
    private Site site;
    
    // 加密检测模式
    private static final List<Pattern> ENCRYPTION_PATTERNS = Arrays.asList(
        Pattern.compile("CryptoJS\\.(AES|DES|TripleDES|MD5|SHA(?:1|256|512|3)?|HmacSHA(?:1|256|512)|RC4|Rabbit|PBKDF2|Base64)"),
        Pattern.compile("encrypt\\(|decrypt\\("),
        Pattern.compile("createCipheriv|createDecipheriv"),
        Pattern.compile("createHmac|createHash|pbkdf2|scrypt|bcrypt|hkdf"),
        Pattern.compile("publicEncrypt|privateDecrypt"),
        Pattern.compile("JSEncrypt|NodeRSA|jsrsasign|elliptic|secp256k1|ed25519|x25519"),
        Pattern.compile("sm2|sm3|sm4|sm-crypto"),
        Pattern.compile("ChaCha20|XChaCha20|Salsa20|Blowfish|Twofish|XXTEA|XTEA|TEA"),
        Pattern.compile("crypto\\.subtle|subtle\\.(encrypt|decrypt|digest|sign|verify)"),
        Pattern.compile("btoa\\(|atob\\("),
        Pattern.compile("window\\[.*\\]\\s*="),
        Pattern.compile("eval\\(function\\(p,a,c,k,e,d\\)"),
        Pattern.compile("\\\\x[0-9a-fA-F]{2}"),
        Pattern.compile("atob\\(['\"][A-Za-z0-9+/=]+['\"]\\)")
    );

    public EncryptedSiteProcessor() {
        this.reverseClient = new NodeReverseClient("http://localhost:3000");
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
                .addHeader("Sec-Ch-Ua", "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"")
                .addHeader("Sec-Ch-Ua-Mobile", "?0")
                .addHeader("Sec-Ch-Ua-Platform", "\"Windows\"");
    }

    @Override
    public Site getSite() {
        return site;
    }

    public void setSite(Site site) {
        this.site = site;
    }

    @Override
    public void process(Page page) {
        try {
            System.out.println("\n" + "=".repeat(80));
            System.out.println("🔐 加密网站爬取处理器");
            System.out.println("=".repeat(80));

            // 步骤 1: 检查 Node.js 逆向服务
            if (!checkReverseService()) {
                System.err.println("❌ Node.js 逆向服务不可用");
                page.setSkip(true);
                return;
            }

            // 步骤 2: 检测页面加密
            String html = page.getHtml().getDocumentHtml();
            if (html == null || html.isEmpty()) {
                System.err.println("❌ 页面为空");
                page.setSkip(true);
                return;
            }

            System.out.println("\n[1/7] 生成反爬画像...");
            profileAntiBot(page, html);
            System.out.println("✅ 反爬画像完成");

            System.out.println("\n[2/7] 检测页面加密...");
            EncryptionInfo encryptionInfo = detectEncryption(html);
            System.out.println("✅ 检测完成");
            
            if (!encryptionInfo.isEmpty()) {
                System.out.println("📊 加密信息:");
                encryptionInfo.print();
            }

            // 步骤 3: 浏览器环境模拟
            System.out.println("\n[3/7] 模拟浏览器环境...");
            simulateBrowser(page, html);
            System.out.println("✅ 浏览器模拟完成");

            // 步骤 4: 分析加密算法
            System.out.println("\n[4/7] 分析加密算法...");
            if (!encryptionInfo.isEmpty()) {
                analyzeEncryption(html, encryptionInfo);
            } else {
                System.out.println("ℹ️  未检测到明显加密");
            }
            System.out.println("✅ 加密分析完成");

            // 步骤 5: 执行混淆代码
            System.out.println("\n[5/7] 执行混淆代码...");
            executeObfuscatedCode(html);
            System.out.println("✅ 混淆代码执行完成");

            // 步骤 6: 提取解密后的数据
            System.out.println("\n[6/7] 提取解密数据...");
            extractDecryptedData(page, html, encryptionInfo);
            System.out.println("✅ 数据提取完成");

            // 步骤 7: 分析 Webpack 打包
            System.out.println("\n[7/7] 分析 Webpack 打包...");
            analyzeWebpack(html);
            System.out.println("✅ Webpack 分析完成");

            System.out.println("\n" + "=".repeat(80));
            System.out.println("✅ 加密网站爬取完成！");
            System.out.println("=".repeat(80) + "\n");

        } catch (Exception e) {
            System.err.println("❌ 处理加密网站时出错: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * 检查逆向服务
     */
    private boolean checkReverseService() {
        try {
            return reverseClient.healthCheck();
        } catch (Exception e) {
            return false;
        }
    }

    private void profileAntiBot(Page page, String html) {
        try {
            Map<String, Object> requestHeaders = new LinkedHashMap<>();
            if (page.getHeaders() != null) {
                requestHeaders.putAll(page.getHeaders());
            }
            JsonNode profile = reverseClient.profileAntiBot(
                html,
                "",
                requestHeaders,
                "",
                page.getStatusCode(),
                page.getUrl()
            );
            if (!profile.path("success").asBoolean(false)) {
                return;
            }

            page.putField("antiBotProfile", profile);
            page.putField("antiBotLevel", profile.path("level").asText(""));
            System.out.printf(
                "  🛡️  Anti-bot profile: level=%s score=%d%n",
                profile.path("level").asText("unknown"),
                profile.path("score").asInt(0)
            );

            if (profile.path("signals").isArray() && profile.path("signals").size() > 0) {
                List<String> signals = new ArrayList<>();
                for (JsonNode signal : profile.path("signals")) {
                    signals.add(signal.asText());
                }
                System.out.println("  signals: " + String.join(", ", signals));
            }

            if (profile.path("recommendations").isArray() && profile.path("recommendations").size() > 0) {
                System.out.println("  next: " + profile.path("recommendations").get(0).asText());
            }

            JsonNode headersNode = profile.path("requestBlueprint").path("headers");
            if (headersNode.isObject()) {
                Iterator<Map.Entry<String, JsonNode>> fields = headersNode.fields();
                while (fields.hasNext()) {
                    Map.Entry<String, JsonNode> field = fields.next();
                    site.addHeader(field.getKey(), field.getValue().asText());
                }
            }
        } catch (Exception e) {
            System.out.println("  ⚠️  反爬画像失败: " + e.getMessage());
        }
    }

    /**
     * 检测页面加密
     */
    private EncryptionInfo detectEncryption(String html) {
        EncryptionInfo info = new EncryptionInfo();
        
        // 检测加密算法
        for (Pattern pattern : ENCRYPTION_PATTERNS) {
            Matcher matcher = pattern.matcher(html);
            if (matcher.find()) {
                info.addPattern(pattern.pattern());
            }
        }

        // 提取 script 标签中的代码
        List<String> scripts = extractScripts(html);
        info.setScriptCount(scripts.size());

        // 分析每个脚本
        for (int i = 0; i < Math.min(scripts.size(), 20); i++) {
            String script = scripts.get(i);
            if (isEncrypted(script)) {
                info.addEncryptedScript(i, script);
            }
        }

        return info;
    }

    /**
     * 检查代码是否被加密
     */
    private boolean isEncrypted(String code) {
        // 检测混淆特征
        if (code.contains("eval(function(") || 
            code.contains("\\x") ||
            code.length() > 1000 && !code.contains(" ")) {
            return true;
        }
        
        // 检测加密调用
        return code.contains("CryptoJS.") ||
               code.contains("encrypt(") ||
               code.contains("decrypt(") ||
               code.contains("atob(") ||
               code.contains("btoa(") ||
               code.toLowerCase().contains("createhmac(") ||
               code.toLowerCase().contains("createhash(") ||
               code.toLowerCase().contains("crypto.subtle") ||
               code.toLowerCase().contains("sm4") ||
               code.toLowerCase().contains("sm2") ||
               code.toLowerCase().contains("sm3") ||
               code.toLowerCase().contains("jsencrypt") ||
               code.toLowerCase().contains("nodersa") ||
               code.toLowerCase().contains("chacha20") ||
               code.toLowerCase().contains("pbkdf2") ||
               code.toLowerCase().contains("bcrypt");
    }

    /**
     * 模拟浏览器环境
     */
    private void simulateBrowser(Page page, String html) {
        try {
            // 提取并执行浏览器指纹代码
            Pattern fingerprintPattern = Pattern.compile(
                "(navigator\\.(userAgent|platform|language|vendor))",
                Pattern.MULTILINE
            );
            Matcher matcher = fingerprintPattern.matcher(html);
            
            if (matcher.find()) {
                System.out.println("  🌐 检测到浏览器指纹检测");

                // 模拟浏览器环境
                try {
                    Map<String, Object> payload = new HashMap<>();
                    payload.put("code", "return JSON.stringify({userAgent: navigator.userAgent, platform: navigator.platform});");
                    payload.put("browserConfig", Map.of(
                        "userAgent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "language", "zh-CN",
                        "platform", "Win32",
                        "vendor", "Google Inc."
                    ));
                    
                    JsonNode result = reverseClient.simulateBrowser(
                        String.valueOf(payload.get("code")),
                        Map.of(
                            "userAgent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "language", "zh-CN",
                            "platform", "Win32",
                            "vendor", "Google Inc."
                        )
                    );
                    System.out.println("  ✅ 浏览器环境模拟成功");
                } catch (Exception e) {
                    System.out.println("  ⚠️  浏览器模拟失败: " + e.getMessage());
                }
            }
        } catch (Exception e) {
            System.out.println("  ⚠️  浏览器模拟失败: " + e.getMessage());
        }
    }

    /**
     * 分析加密算法
     */
    private void analyzeEncryption(String html, EncryptionInfo info) {
        // 对加密的脚本进行分析
        for (Map.Entry<Integer, String> entry : info.getEncryptedScripts().entrySet()) {
            int index = entry.getKey();
            String script = entry.getValue();
            
            try {
                System.out.println("  🔍 分析脚本 #" + index + "...");
                
                // 使用 Node.js 逆向服务分析
                JsonNode result = reverseClient.analyzeCrypto(script);
                
                if (result.get("success").asBoolean()) {
                    JsonNode cryptoTypes = result.get("cryptoTypes");
                    if (cryptoTypes != null && cryptoTypes.isArray() && cryptoTypes.size() > 0) {
                        System.out.println("    ✅ 检测到加密算法:");
                        for (JsonNode crypto : cryptoTypes) {
                            System.out.printf("      - %s (置信度: %.2f)\n",
                                crypto.get("name").asText(),
                                crypto.get("confidence").asDouble());
                        }
                    }
                    
                    // 输出检测到的密钥
                    if (result.get("keys") != null && result.get("keys").isArray() && result.get("keys").size() > 0) {
                        System.out.println("    🔑 密钥:");
                        for (JsonNode key : result.get("keys")) {
                            System.out.println("      - " + key.asText());
                        }
                    }
                }
            } catch (Exception e) {
                System.out.println("    ❌ 分析失败: " + e.getMessage());
            }
        }
    }

    /**
     * 执行混淆代码
     */
    private void executeObfuscatedCode(String html) {
        // 查找 eval 混淆的代码
        Pattern evalPattern = Pattern.compile(
            "eval\\(function\\(p,a,c,k,e,d\\)\\{(.*?)\\}",
            Pattern.DOTALL
        );
        Matcher matcher = evalPattern.matcher(html);
        
        int count = 0;
        while (matcher.find() && count < 5) {
            String obfuscatedCode = matcher.group(0);
            count++;
            
            try {
                System.out.println("  📦 执行混淆代码块 #" + count + "...");
                
                JsonNode result = reverseClient.executeJS(
                    obfuscatedCode,
                    Map.of(
                        "window", Map.of(),
                        "document", Map.of(),
                        "navigator", Map.of("userAgent", "Mozilla/5.0")
                    ),
                    10000
                );
                
                if (result.get("success").asBoolean()) {
                    System.out.println("    ✅ 执行成功");
                    String resultText = result.get("result").asText();
                    if (resultText != null && !resultText.isEmpty()) {
                        System.out.println("    📝 结果: " + resultText.substring(0,
                            Math.min(100, resultText.length())));
                    }
                }
            } catch (Exception e) {
                System.out.println("    ❌ 执行失败: " + e.getMessage());
            }
        }
        
        if (count == 0) {
            System.out.println("  ℹ️  未找到 eval 混淆代码");
        }
    }

    /**
     * 提取解密后的数据
     */
    private void extractDecryptedData(Page page, String html, EncryptionInfo info) {
        try {
            // 查找可能的加密数据
            Pattern encryptedDataPattern = Pattern.compile(
                "(?:data|response|result)\\s*[:=]\\s*['\"]([A-Za-z0-9+/=]{100,})['\"]",
                Pattern.DOTALL
            );
            Matcher matcher = encryptedDataPattern.matcher(html);
            
            int count = 0;
            while (matcher.find() && count < 3) {
                String encryptedData = matcher.group(1);
                count++;
                
                System.out.println("  🔓 尝试解密数据块 #" + count + "...");
                
                // 尝试 Base64 解密
                try {
                    JsonNode result = reverseClient.decrypt(
                        "BASE64",
                        encryptedData,
                        "",
                        "",
                        ""
                    );
                    
                    if (result.get("success").asBoolean() && result.has("decrypted")) {
                        String decrypted = result.get("decrypted").asText();
                        System.out.println("    ✅ 解密成功 (前 100 字符):");
                        System.out.println("    " + decrypted.substring(0, Math.min(100, decrypted.length())));
                    }
                } catch (Exception e) {
                    System.out.println("    ⚠️  Base64 解密失败，可能是其他加密");
                }
            }
            
            if (count == 0) {
                System.out.println("  ℹ️  未找到明显的加密数据");
            }
        } catch (Exception e) {
            System.out.println("  ❌ 数据提取失败: " + e.getMessage());
        }
    }

    /**
     * 分析 Webpack 打包
     */
    private void analyzeWebpack(String html) {
        // 查找 Webpack 打包特征
        Pattern webpackPattern = Pattern.compile(
            "function\\s*\\(\\s*modules\\s*\\)\\s*\\{"
        );
        Matcher matcher = webpackPattern.matcher(html);
        
        if (matcher.find()) {
            System.out.println("  📦 检测到 Webpack 打包");
            
            // 提取打包代码
            int start = matcher.start();
            String webpackCode = html.substring(start, Math.min(start + 5000, html.length()));
            
            try {
                JsonNode result = reverseClient.analyzeWebpack(webpackCode);
                if (result.get("success").asBoolean()) {
                    int moduleCount = result.get("totalModules").asInt();
                    System.out.println("    ✅ 找到 " + moduleCount + " 个模块");
                }
            } catch (Exception e) {
                System.out.println("    ⚠️  Webpack 分析失败: " + e.getMessage());
            }
        } else {
            System.out.println("  ℹ️  未检测到 Webpack 打包");
        }
    }

    /**
     * 提取 <script> 标签内容
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
     * 加密信息类
     */
    private static class EncryptionInfo {
        private final List<String> patterns = new ArrayList<>();
        private final Map<Integer, String> encryptedScripts = new LinkedHashMap<>();
        private int scriptCount = 0;

        public void addPattern(String pattern) {
            if (!patterns.contains(pattern)) {
                patterns.add(pattern);
            }
        }

        public void addEncryptedScript(int index, String script) {
            encryptedScripts.put(index, script);
        }

        public void setScriptCount(int count) {
            this.scriptCount = count;
        }

        public boolean isEmpty() {
            return patterns.isEmpty() && encryptedScripts.isEmpty();
        }

        public Map<Integer, String> getEncryptedScripts() {
            return encryptedScripts;
        }

        public void print() {
            if (!patterns.isEmpty()) {
                System.out.println("  🔐 检测到加密模式:");
                for (String pattern : patterns) {
                    System.out.println("    - " + pattern);
                }
            }
            if (!encryptedScripts.isEmpty()) {
                System.out.println("  📜 加密脚本数: " + encryptedScripts.size());
            }
            System.out.println("  📄 总脚本数: " + scriptCount);
        }
    }

    /**
     * 主函数 - 启动加密网站爬虫
     */
    public static void main(String[] args) {
        if (args.length < 1) {
            System.out.println("用法: java EncryptedSiteProcessor <URL>");
            System.out.println("示例: java EncryptedSiteProcessor https://encrypted-site.com");
            return;
        }

        String targetUrl = args[0];
        
        System.out.println("🚀 启动加密网站爬取...");
        System.out.println("目标URL: " + targetUrl);
        System.out.println("逆向服务: http://localhost:3000");
        System.out.println();

        EncryptedSiteProcessor processor = new EncryptedSiteProcessor();

        Spider spider = Spider.create(processor)
                .name("EncryptedSiteSpider")
                .addUrl(targetUrl)
                .thread(1);

        System.out.println("爬虫配置:");
        System.out.println("  - 名称: EncryptedSiteSpider");
        System.out.println("  - 线程数: 1");
        System.out.println("  - 目标: " + targetUrl);
        System.out.println();

        System.out.println("开始爬取...\n");
        spider.start();
    }
}
