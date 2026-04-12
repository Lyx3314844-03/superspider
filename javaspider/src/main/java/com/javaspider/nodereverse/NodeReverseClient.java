package com.javaspider.nodereverse;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import okhttp3.*;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * Node.js 逆向服务客户端
 * 为 JavaSpider 提供统一的逆向能力接口
 */
public class NodeReverseClient {
    
    private static final String DEFAULT_BASE_URL = "http://localhost:3000";
    
    private final String baseUrl;
    private final OkHttpClient httpClient;
    private final ObjectMapper objectMapper;
    
    /**
     * 创建默认客户端
     */
    public NodeReverseClient() {
        this(DEFAULT_BASE_URL);
    }
    
    /**
     * 创建指定URL的客户端
     */
    public NodeReverseClient(String baseUrl) {
        this.baseUrl = baseUrl;
        this.httpClient = new OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .build();
        this.objectMapper = new ObjectMapper();
    }
    
    /**
     * 分析代码中的加密算法
     */
    public JsonNode analyzeCrypto(String code) throws IOException {
        RequestBody body = RequestBody.create(
                objectMapper.writeValueAsString(new CryptoRequest(code)),
                MediaType.parse("application/json")
        );
        
        Request request = new Request.Builder()
                .url(baseUrl + "/api/crypto/analyze")
                .post(body)
                .build();
        
        try (Response response = httpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("Unexpected code " + response);
            }
            return objectMapper.readTree(response.body().string());
        }
    }
    
    /**
     * 执行加密操作
     */
    public JsonNode encrypt(String algorithm, String data, String key, String iv, String mode) throws IOException {
        EncryptRequest req = new EncryptRequest(algorithm, data, key, iv, mode);
        RequestBody body = RequestBody.create(
                objectMapper.writeValueAsString(req),
                MediaType.parse("application/json")
        );
        
        Request request = new Request.Builder()
                .url(baseUrl + "/api/crypto/encrypt")
                .post(body)
                .build();
        
        try (Response response = httpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("Unexpected code " + response);
            }
            return objectMapper.readTree(response.body().string());
        }
    }
    
    /**
     * 执行解密操作
     */
    public JsonNode decrypt(String algorithm, String data, String key, String iv, String mode) throws IOException {
        DecryptRequest req = new DecryptRequest(algorithm, data, key, iv, mode);
        RequestBody body = RequestBody.create(
                objectMapper.writeValueAsString(req),
                MediaType.parse("application/json")
        );
        
        Request request = new Request.Builder()
                .url(baseUrl + "/api/crypto/decrypt")
                .post(body)
                .build();
        
        try (Response response = httpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("Unexpected code " + response);
            }
            return objectMapper.readTree(response.body().string());
        }
    }
    
    /**
     * 提取AST结构
     */
    public JsonNode extractAST(String code, Map<String, Object> options) throws IOException {
        ASTRequest req = new ASTRequest(code, options);
        RequestBody body = RequestBody.create(
                objectMapper.writeValueAsString(req),
                MediaType.parse("application/json")
        );
        
        Request request = new Request.Builder()
                .url(baseUrl + "/api/ast/extract")
                .post(body)
                .build();
        
        try (Response response = httpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("Unexpected code " + response);
            }
            return objectMapper.readTree(response.body().string());
        }
    }
    
    /**
     * 查找函数调用
     */
    public JsonNode findFunctionCalls(String code, String functionName) throws IOException {
        FunctionCallRequest req = new FunctionCallRequest(code, functionName);
        RequestBody body = RequestBody.create(
                objectMapper.writeValueAsString(req),
                MediaType.parse("application/json")
        );
        
        Request request = new Request.Builder()
                .url(baseUrl + "/api/ast/find-calls")
                .post(body)
                .build();
        
        try (Response response = httpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("Unexpected code " + response);
            }
            return objectMapper.readTree(response.body().string());
        }
    }
    
    /**
     * 分析Webpack Bundle
     */
    public JsonNode analyzeWebpack(String code) throws IOException {
        WebpackRequest req = new WebpackRequest(code);
        RequestBody body = RequestBody.create(
                objectMapper.writeValueAsString(req),
                MediaType.parse("application/json")
        );
        
        Request request = new Request.Builder()
                .url(baseUrl + "/api/webpack/analyze")
                .post(body)
                .build();
        
        try (Response response = httpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("Unexpected code " + response);
            }
            return objectMapper.readTree(response.body().string());
        }
    }
    
    /**
     * 健康检查
     */
    public boolean healthCheck() {
        try {
            Request request = new Request.Builder()
                    .url(baseUrl + "/health")
                    .get()
                    .build();
            
            try (Response response = httpClient.newCall(request).execute()) {
                if (!response.isSuccessful()) {
                    return false;
                }
                JsonNode health = objectMapper.readTree(response.body().string());
                return "ok".equals(health.get("status").asText());
            }
        } catch (IOException e) {
            return false;
        }
    }
    
    // 请求体类
    private static class CryptoRequest {
        public String code;
        
        public CryptoRequest(String code) {
            this.code = code;
        }
    }
    
    private static class EncryptRequest {
        public String algorithm;
        public String data;
        public String key;
        public String iv;
        public String mode;
        
        public EncryptRequest(String algorithm, String data, String key, String iv, String mode) {
            this.algorithm = algorithm;
            this.data = data;
            this.key = key;
            this.iv = iv;
            this.mode = mode;
        }
    }
    
    private static class DecryptRequest {
        public String algorithm;
        public String data;
        public String key;
        public String iv;
        public String mode;
        
        public DecryptRequest(String algorithm, String data, String key, String iv, String mode) {
            this.algorithm = algorithm;
            this.data = data;
            this.key = key;
            this.iv = iv;
            this.mode = mode;
        }
    }
    
    private static class ASTRequest {
        public String code;
        public Map<String, Object> options;
        
        public ASTRequest(String code, Map<String, Object> options) {
            this.code = code;
            this.options = options;
        }
    }

    private static class FunctionCallRequest {
        public String code;
        public String functionName;

        public FunctionCallRequest(String code, String functionName) {
            this.code = code;
            this.functionName = functionName;
        }
    }

    private static class WebpackRequest {
        public String code;

        public WebpackRequest(String code) {
            this.code = code;
        }
    }

    /**
     * 执行 POST 请求（通用方法）
     */
    public JsonNode doPost(String path, java.util.Map<String, Object> payload) throws IOException {
        RequestBody body = RequestBody.create(
                objectMapper.writeValueAsString(payload),
                MediaType.parse("application/json")
        );

        Request request = new Request.Builder()
                .url(baseUrl + path)
                .post(body)
                .build();

        try (Response response = httpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("Unexpected code " + response);
            }
            return objectMapper.readTree(response.body().string());
        }
    }

    /**
     * AST 语法分析
     */
    public JsonNode analyzeAST(String code, List<String> analysisTypes) throws IOException {
        java.util.Map<String, Object> payload = new java.util.HashMap<>();
        payload.put("code", code);
        payload.put("analysis", analysisTypes);

        return doPost("/api/ast/analyze", payload);
    }

    /**
     * 执行 JavaScript 代码
     */
    public JsonNode executeJS(String code, java.util.Map<String, Object> context, int timeout) throws IOException {
        java.util.Map<String, Object> payload = new java.util.HashMap<>();
        payload.put("code", code);
        if (context != null) {
            payload.put("context", context);
        }
        payload.put("timeout", timeout);

        RequestBody body = RequestBody.create(
                objectMapper.writeValueAsString(payload),
                MediaType.parse("application/json")
        );

        Request request = new Request.Builder()
                .url(baseUrl + "/api/js/execute")
                .post(body)
                .build();

        try (Response response = httpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("Unexpected code " + response);
            }
            return objectMapper.readTree(response.body().string());
        }
    }

    /**
     * 检测页面中的反爬挑战特征
     */
    public JsonNode detectAntiBot(
            String html,
            String js,
            Map<String, Object> headers,
            String cookies,
            Integer statusCode,
            String url
    ) throws IOException {
        java.util.Map<String, Object> payload = new java.util.HashMap<>();
        payload.put("html", html);
        payload.put("js", js);
        payload.put("headers", headers != null ? headers : java.util.Collections.emptyMap());
        payload.put("cookies", cookies);
        payload.put("url", url);
        if (statusCode != null) {
            payload.put("statusCode", statusCode);
        }
        return doPost("/api/anti-bot/detect", payload);
    }

    /**
     * 生成完整的反爬画像、请求蓝图和规避计划
     */
    public JsonNode profileAntiBot(
            String html,
            String js,
            Map<String, Object> headers,
            String cookies,
            Integer statusCode,
            String url
    ) throws IOException {
        java.util.Map<String, Object> payload = new java.util.HashMap<>();
        payload.put("html", html);
        payload.put("js", js);
        payload.put("headers", headers != null ? headers : java.util.Collections.emptyMap());
        payload.put("cookies", cookies);
        payload.put("url", url);
        if (statusCode != null) {
            payload.put("statusCode", statusCode);
        }
        return doPost("/api/anti-bot/profile", payload);
    }

    public JsonNode spoofFingerprint(String browser, String platform) throws IOException {
        java.util.Map<String, Object> payload = new java.util.HashMap<>();
        payload.put("browser", browser);
        payload.put("platform", platform);
        return doPost("/api/fingerprint/spoof", payload);
    }

    public JsonNode generateTlsFingerprint(String browser, String version) throws IOException {
        java.util.Map<String, Object> payload = new java.util.HashMap<>();
        payload.put("browser", browser);
        payload.put("version", version);
        return doPost("/api/tls/fingerprint", payload);
    }
}
