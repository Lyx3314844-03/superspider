package com.javaspider.encrypted;

import com.fasterxml.jackson.databind.JsonNode;
import com.javaspider.nodereverse.NodeReverseClient;

import java.io.IOException;
import java.util.*;

/**
 * 加密网站爬取增强模块
 * 
 * 新增功能 (v3.0):
 * 1. 自动签名逆向 - 自动分析并还原网站签名算法
 * 2. 动态参数解密 - 解密动态生成的请求参数
 * 3. TLS 指纹伪造 - 生成真实浏览器 TLS 指纹
 * 4. 反调试绕过 - 绕过 debugger/反调试保护
 * 5. Cookie 加密处理 - 解密加密的 Cookie
 * 6. WebSocket 消息加解密
 * 7. Canvas 指纹生成
 * 
 * @author JavaSpider Team
 * @version 3.0.0
 */
public class EncryptedSiteCrawlerEnhanced {

    private final NodeReverseClient reverseClient;

    public EncryptedSiteCrawlerEnhanced(String reverseServiceUrl) {
        this.reverseClient = new NodeReverseClient(reverseServiceUrl);
    }

    public EncryptedSiteCrawlerEnhanced() {
        this("http://localhost:3000");
    }

    /**
     * 1. 自动签名逆向
     * 分析代码并自动还原签名算法
     * 
     * @param code 包含签名函数的代码
     * @param sampleInputs 样本输入（用于验证）
     * @param sampleOutput 样本输出（用于验证）
     * @return 签名函数信息
     */
    public SignatureReverseResult autoReverseSignature(String code, 
                                                       String sampleInputs, 
                                                       String sampleOutput) throws IOException {
        Map<String, Object> payload = new HashMap<>();
        payload.put("code", code);
        payload.put("sampleInputs", sampleInputs);
        payload.put("sampleOutput", sampleOutput);

        JsonNode result = reverseClient.reverseSignature(code, sampleInputs, sampleOutput);

        SignatureReverseResult signatureResult = new SignatureReverseResult();
        signatureResult.success = result.get("success").asBoolean();
        
        if (result.has("signatureFunction") && !result.get("signatureFunction").isNull()) {
            JsonNode func = result.get("signatureFunction");
            signatureResult.functionName = func.get("name").asText();
            signatureResult.input = func.has("input") ? func.get("input").asText() : null;
            signatureResult.output = func.has("output") ? func.get("output").asText() : null;
        }

        if (result.has("analysis")) {
            JsonNode analysis = result.get("analysis");
            signatureResult.totalFunctions = analysis.get("totalFunctions").asInt();
            signatureResult.successCount = analysis.get("successCount").asInt();
        }

        return signatureResult;
    }

    /**
     * 2. 动态参数解密
     * 解密动态生成的请求参数
     * 
     * @param encryptedParams 加密的参数
     * @param algorithm 加密算法 (AES/Base64)
     * @param key 密钥
     * @param iv 初始化向量
     * @return 解密后的参数
     */
    public DecryptedParams decryptDynamicParams(String encryptedParams,
                                                 String algorithm,
                                                 String key,
                                                 String iv) throws IOException {
        Map<String, Object> payload = new HashMap<>();
        payload.put("encryptedParams", encryptedParams);
        payload.put("algorithm", algorithm);
        payload.put("key", key);
        payload.put("iv", iv);

        JsonNode result = reverseClient.doPost("/api/param/decrypt", payload);

        DecryptedParams decryptedParams = new DecryptedParams();
        decryptedParams.success = result.get("success").asBoolean();
        decryptedParams.rawData = result.get("decrypted").asText();
        
        if (result.has("params")) {
            JsonNode params = result.get("params");
            Iterator<Map.Entry<String, JsonNode>> fields = params.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                decryptedParams.params.put(field.getKey(), field.getValue().asText());
            }
        }

        return decryptedParams;
    }

    /**
     * 3. TLS 指纹生成
     * 生成真实浏览器的 TLS 指纹
     * 
     * @param browser 浏览器类型 (chrome/firefox)
     * @param version 浏览器版本
     * @return TLS 指纹信息
     */
    public TLSFingerprint generateTLSFingerprint(String browser, String version) throws IOException {
        Map<String, Object> payload = new HashMap<>();
        payload.put("browser", browser);
        payload.put("version", version);

        JsonNode result = reverseClient.doPost("/api/tls/fingerprint", payload);

        TLSFingerprint fingerprint = new TLSFingerprint();
        fingerprint.success = result.get("success").asBoolean();
        
        if (result.has("fingerprint")) {
            JsonNode fp = result.get("fingerprint");
            
            if (fp.has("cipherSuites")) {
                for (JsonNode suite : fp.get("cipherSuites")) {
                    fingerprint.cipherSuites.add(suite.asText());
                }
            }
            
            if (fp.has("ja3")) {
                fingerprint.ja3 = fp.get("ja3").asText();
            }
        }

        return fingerprint;
    }

    /**
     * 4. 反调试绕过
     * 生成绕过反调试保护的代码
     * 
     * @param code 需要执行的代码
     * @param bypassType 绕过类型 (all/debugger/devtools/time)
     * @return 执行结果
     */
    public AntiDebugBypassResult bypassAntiDebug(String code, String bypassType) throws IOException {
        Map<String, Object> payload = new HashMap<>();
        payload.put("code", code);
        payload.put("type", bypassType != null ? bypassType : "all");

        JsonNode result = reverseClient.doPost("/api/anti-debug/bypass", payload);

        AntiDebugBypassResult bypassResult = new AntiDebugBypassResult();
        bypassResult.success = result.get("success").asBoolean();
        bypassResult.bypassType = result.get("bypassType").asText();
        
        if (result.has("result")) {
            bypassResult.result = result.get("result").toString();
        }

        return bypassResult;
    }

    /**
     * 5. Cookie 加密处理
     * 解密加密的 Cookie
     * 
     * @param encryptedCookie 加密的 Cookie
     * @param key 密钥
     * @param algorithm 加密算法
     * @return 解密后的 Cookie
     */
    public DecryptedCookies decryptCookie(String encryptedCookie,
                                         String key,
                                         String algorithm) throws IOException {
        Map<String, Object> payload = new HashMap<>();
        payload.put("encryptedCookie", encryptedCookie);
        payload.put("key", key);
        payload.put("algorithm", algorithm != null ? algorithm : "AES");

        JsonNode result = reverseClient.doPost("/api/cookie/decrypt", payload);

        DecryptedCookies decryptedCookies = new DecryptedCookies();
        decryptedCookies.success = result.get("success").asBoolean();
        decryptedCookies.rawData = result.get("decrypted").asText();
        
        if (result.has("cookies")) {
            JsonNode cookies = result.get("cookies");
            Iterator<Map.Entry<String, JsonNode>> fields = cookies.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                decryptedCookies.cookies.put(field.getKey(), field.getValue().asText());
            }
        }

        return decryptedCookies;
    }

    /**
     * 6. WebSocket 消息解密
     * 处理 WebSocket 加密消息
     * 
     * @param encryptedMessage 加密的消息
     * @param key 密钥
     * @param algorithm 加密算法
     * @return 解密后的消息
     */
    public DecryptedWebSocketMessage decryptWebSocketMessage(String encryptedMessage,
                                                            String key,
                                                            String algorithm) throws IOException {
        Map<String, Object> payload = new HashMap<>();
        payload.put("encryptedMessage", encryptedMessage);
        payload.put("key", key);
        payload.put("algorithm", algorithm != null ? algorithm : "AES");

        JsonNode result = reverseClient.doPost("/api/websocket/decrypt", payload);

        DecryptedWebSocketMessage decryptedMessage = new DecryptedWebSocketMessage();
        decryptedMessage.success = result.get("success").asBoolean();
        decryptedMessage.rawData = result.get("decrypted").asText();
        
        if (result.has("parsed")) {
            decryptedMessage.parsedData = result.get("parsed").toString();
        }

        return decryptedMessage;
    }

    /**
     * 7. Canvas 指纹生成
     * 生成 Canvas 浏览器指纹
     * 
     * @return Canvas 指纹信息
     */
    public CanvasFingerprint generateCanvasFingerprint() throws IOException {
        JsonNode result = reverseClient.canvasFingerprint();

        CanvasFingerprint fingerprint = new CanvasFingerprint();
        fingerprint.success = result.get("success").asBoolean();
        fingerprint.fingerprint = result.get("fingerprint").asText();
        fingerprint.hash = result.get("hash").asText();

        return fingerprint;
    }

    // ==================== 结果类 ====================

    public static class SignatureReverseResult {
        public boolean success;
        public String functionName;
        public String input;
        public String output;
        public int totalFunctions;
        public int successCount;

        @Override
        public String toString() {
            return String.format("SignatureReverseResult{success=%b, function='%s', total=%d, successCount=%d}",
                    success, functionName, totalFunctions, successCount);
        }
    }

    public static class DecryptedParams {
        public boolean success;
        public String rawData;
        public Map<String, String> params = new HashMap<>();

        @Override
        public String toString() {
            return String.format("DecryptedParams{success=%b, params=%s}", success, params);
        }
    }

    public static class TLSFingerprint {
        public boolean success;
        public List<String> cipherSuites = new ArrayList<>();
        public String ja3;

        @Override
        public String toString() {
            return String.format("TLSFingerprint{success=%b, ja3='%s', cipherCount=%d}",
                    success, ja3, cipherSuites.size());
        }
    }

    public static class AntiDebugBypassResult {
        public boolean success;
        public String bypassType;
        public String result;

        @Override
        public String toString() {
            return String.format("AntiDebugBypassResult{success=%b, type='%s'}", success, bypassType);
        }
    }

    public static class DecryptedCookies {
        public boolean success;
        public String rawData;
        public Map<String, String> cookies = new HashMap<>();

        @Override
        public String toString() {
            return String.format("DecryptedCookies{success=%b, cookieCount=%d}", success, cookies.size());
        }
    }

    public static class DecryptedWebSocketMessage {
        public boolean success;
        public String rawData;
        public String parsedData;

        @Override
        public String toString() {
            return String.format("DecryptedWebSocketMessage{success=%b}", success);
        }
    }

    public static class CanvasFingerprint {
        public boolean success;
        public String fingerprint;
        public String hash;

        @Override
        public String toString() {
            return String.format("CanvasFingerprint{success=%b, hash='%s'}", success, hash);
        }
    }
}
