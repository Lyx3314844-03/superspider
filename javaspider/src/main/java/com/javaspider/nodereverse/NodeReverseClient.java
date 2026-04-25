package com.javaspider.nodereverse;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import okhttp3.*;

import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

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
                .dispatcher(new Dispatcher(java.util.concurrent.Executors.newCachedThreadPool(r -> {
                    Thread thread = new Thread(r, "node-reverse-okhttp");
                    thread.setDaemon(true);
                    return thread;
                })))
                .connectionPool(new ConnectionPool(0, 1, TimeUnit.SECONDS))
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
        JsonNode local = localCryptoAnalysis(code);
        // 本地分析已经可用时直接返回，远端 Node 服务只作为无法判定时的增强路径。
        if (local.path("success").asBoolean(false)) {
            return local;
        }
        try {
            JsonNode remote = doPost("/api/crypto/analyze", Map.of("code", code));
            return mergeCryptoAnalysis(remote, local);
        } catch (IOException error) {
            throw error;
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

    public JsonNode callFunction(String functionName, List<?> args, String code) throws IOException {
        java.util.Map<String, Object> payload = new java.util.HashMap<>();
        payload.put("functionName", functionName);
        payload.put("args", args == null ? List.of() : args);
        payload.put("code", code);
        return doPost("/api/function/call", payload);
    }

    public JsonNode simulateBrowser(String code, Map<String, ?> browserConfig) throws IOException {
        java.util.Map<String, Object> payload = new java.util.HashMap<>();
        payload.put("code", code);
        if (browserConfig != null) {
            payload.put("browserConfig", browserConfig);
        }
        return doPost("/api/browser/simulate", payload);
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

    public JsonNode canvasFingerprint() throws IOException {
        return doPost("/api/canvas/fingerprint", java.util.Collections.emptyMap());
    }

    public JsonNode reverseSignature(String code, String inputData, String expectedOutput) throws IOException {
        java.util.Map<String, Object> payload = new java.util.HashMap<>();
        payload.put("code", code);
        payload.put("input", inputData);
        payload.put("expectedOutput", expectedOutput);
        return doPost("/api/signature/reverse", payload);
    }

    private JsonNode localCryptoAnalysis(String code) {
        String sourceCode = code == null ? "" : code;
        String lowered = sourceCode.toLowerCase();
        Map<String, List<String>> libraries = new LinkedHashMap<>();
        libraries.put("CryptoJS", List.of("cryptojs."));
        libraries.put("NodeCrypto", List.of("require('crypto')", "require(\"crypto\")", "createcipheriv", "createhmac", "createhash"));
        libraries.put("WebCrypto", List.of("crypto.subtle", "subtle.encrypt", "subtle.decrypt", "subtle.digest", "subtle.sign"));
        libraries.put("Forge", List.of("forge.", "node-forge"));
        libraries.put("SJCL", List.of("sjcl."));
        libraries.put("sm-crypto", List.of("sm2", "sm3", "sm4", "sm-crypto"));
        libraries.put("JSEncrypt", List.of("jsencrypt", "node-rsa"));
        libraries.put("jsrsasign", List.of("jsrsasign", "rsasign"));
        libraries.put("tweetnacl", List.of("tweetnacl", "nacl.sign", "nacl.box"));
        libraries.put("elliptic", List.of("secp256k1", "elliptic.ec", "ecdh", "ecdsa"));
        libraries.put("sodium", List.of("libsodium", "sodium.", "xchacha20", "ed25519", "x25519"));
        Map<String, List<String>> operations = new LinkedHashMap<>();
        operations.put("encrypt", List.of("encrypt(", "subtle.encrypt", "createcipheriv", ".encrypt("));
        operations.put("decrypt", List.of("decrypt(", "subtle.decrypt", "createdecipheriv", ".decrypt("));
        operations.put("sign", List.of("sign(", "subtle.sign", "jsonwebtoken.sign", "jws.sign"));
        operations.put("verify", List.of("verify(", "subtle.verify", "jsonwebtoken.verify", "jws.verify"));
        operations.put("hash", List.of("createhash", "subtle.digest", "md5(", "sha1(", "sha256(", "sha512(", "sha3", "ripemd160"));
        operations.put("kdf", List.of("pbkdf2", "scrypt", "bcrypt", "hkdf"));
        operations.put("encode", List.of("btoa(", "atob(", "base64", "base64url", "jwt"));
        Map<String, List<String>> modeMarkers = new LinkedHashMap<>();
        modeMarkers.put("CBC", List.of("cbc"));
        modeMarkers.put("GCM", List.of("gcm"));
        modeMarkers.put("CTR", List.of("ctr"));
        modeMarkers.put("ECB", List.of("ecb"));
        modeMarkers.put("CFB", List.of("cfb"));
        modeMarkers.put("OFB", List.of("ofb"));
        modeMarkers.put("CCM", List.of("ccm"));
        modeMarkers.put("XTS", List.of("xts"));
        Map<String, List<String>> dynamicSourceMarkers = new LinkedHashMap<>();
        dynamicSourceMarkers.put("storage", List.of("localstorage", "sessionstorage", "indexeddb"));
        dynamicSourceMarkers.put("cookie", List.of("document.cookie"));
        dynamicSourceMarkers.put("navigator", List.of("navigator."));
        dynamicSourceMarkers.put("time", List.of("date.now", "new date(", "performance.now"));
        dynamicSourceMarkers.put("random", List.of("math.random", "getrandomvalues", "randombytes"));
        dynamicSourceMarkers.put("env", List.of("process.env", "import.meta.env"));
        dynamicSourceMarkers.put("window_state", List.of("window.__", "globalthis.", "window["));
        dynamicSourceMarkers.put("network", List.of("fetch(", "axios.", "xmlhttprequest", ".response", "await fetch"));
        Map<String, List<String>> runtimeSelectorMarkers = new LinkedHashMap<>();
        runtimeSelectorMarkers.put("algorithm_variable", List.of("algorithm", "algo", "ciphername"));
        runtimeSelectorMarkers.put("mode_variable", List.of("mode =", "mode:", "ciphermode"));
        runtimeSelectorMarkers.put("switch_dispatch", List.of("switch(", "case 'aes", "case \"aes"));
        runtimeSelectorMarkers.put("computed_lookup", List.of("[algo]", "[algorithm]", "algorithms[", "ciphers["));
        Map<String, List<String>> obfuscationLoaderMarkers = new LinkedHashMap<>();
        obfuscationLoaderMarkers.put("eval_packer", List.of("eval(function(p,a,c,k,e,d)"));
        obfuscationLoaderMarkers.put("hex_array", List.of("_0x", "\\x"));
        obfuscationLoaderMarkers.put("base64_loader", List.of("atob(", "buffer.from(", "base64"));
        obfuscationLoaderMarkers.put("function_constructor", List.of("function(", "constructor(\"return this\")", "constructor('return this')"));
        obfuscationLoaderMarkers.put("webpack_loader", List.of("__webpack_require__", "webpackjsonp", "webpackchunk"));
        obfuscationLoaderMarkers.put("anti_debug", List.of("debugger", "devtools", "setinterval(function(){debugger"));
        Map<String, List<String>> sinkCatalog = new LinkedHashMap<>();
        sinkCatalog.put("CryptoJS.AES.encrypt", List.of("cryptojs.aes.encrypt"));
        sinkCatalog.put("CryptoJS.AES.decrypt", List.of("cryptojs.aes.decrypt"));
        sinkCatalog.put("CryptoJS.DES.encrypt", List.of("cryptojs.des.encrypt"));
        sinkCatalog.put("CryptoJS.TripleDES.encrypt", List.of("cryptojs.tripledes.encrypt"));
        sinkCatalog.put("CryptoJS.HmacSHA256", List.of("cryptojs.hmacsha256", "hmacsha256("));
        sinkCatalog.put("CryptoJS.PBKDF2", List.of("cryptojs.pbkdf2", "pbkdf2("));
        sinkCatalog.put("crypto.createCipheriv", List.of("createcipheriv"));
        sinkCatalog.put("crypto.createDecipheriv", List.of("createdecipheriv"));
        sinkCatalog.put("crypto.createHmac", List.of("createhmac"));
        sinkCatalog.put("crypto.createHash", List.of("createhash"));
        sinkCatalog.put("crypto.subtle.encrypt", List.of("subtle.encrypt"));
        sinkCatalog.put("crypto.subtle.decrypt", List.of("subtle.decrypt"));
        sinkCatalog.put("crypto.subtle.sign", List.of("subtle.sign"));
        sinkCatalog.put("crypto.subtle.digest", List.of("subtle.digest"));
        sinkCatalog.put("sm4.encrypt", List.of("sm4.encrypt"));
        sinkCatalog.put("sm2.doSignature", List.of("sm2.dosignature"));
        sinkCatalog.put("jwt.sign", List.of("jsonwebtoken.sign", "jwt.sign"));
        sinkCatalog.put("jwt.verify", List.of("jsonwebtoken.verify", "jwt.verify"));
        List<Map<String, Object>> algorithms = List.of(
            Map.of("name", "AES", "markers", List.of("cryptojs.aes", "aes-gcm", "aes-cbc", "aes-ctr", "aes-ecb", "createcipheriv", "createdecipheriv", "subtle.encrypt", "subtle.decrypt")),
            Map.of("name", "DES", "markers", List.of("cryptojs.des", "des-cbc", "des-ecb")),
            Map.of("name", "TripleDES", "markers", List.of("cryptojs.tripledes", "des-ede3", "3des", "tripledes")),
            Map.of("name", "RSA", "markers", List.of("jsencrypt", "node-rsa", "publicencrypt", "privatedecrypt", "rsa-oaep", "rsa-pss", "rsasign")),
            Map.of("name", "ECDSA", "markers", List.of("ecdsa", "secp256k1", "elliptic.ec")),
            Map.of("name", "Ed25519", "markers", List.of("ed25519")),
            Map.of("name", "X25519", "markers", List.of("x25519")),
            Map.of("name", "SM2", "markers", List.of("sm2")),
            Map.of("name", "SM3", "markers", List.of("sm3")),
            Map.of("name", "SM4", "markers", List.of("sm4")),
            Map.of("name", "RC4", "markers", List.of("cryptojs.rc4", "rc4")),
            Map.of("name", "Rabbit", "markers", List.of("cryptojs.rabbit", "rabbit")),
            Map.of("name", "ChaCha20", "markers", List.of("chacha20", "xchacha20")),
            Map.of("name", "Salsa20", "markers", List.of("salsa20")),
            Map.of("name", "Blowfish", "markers", List.of("blowfish")),
            Map.of("name", "Twofish", "markers", List.of("twofish")),
            Map.of("name", "TEA", "markers", List.of("tea.encrypt", "tea.decrypt")),
            Map.of("name", "XTEA", "markers", List.of("xtea")),
            Map.of("name", "XXTEA", "markers", List.of("xxtea")),
            Map.of("name", "HMAC-SHA1", "markers", List.of("hmacsha1", "createhmac('sha1", "createhmac(\"sha1")),
            Map.of("name", "HMAC-SHA256", "markers", List.of("hmacsha256", "createhmac('sha256", "createhmac(\"sha256")),
            Map.of("name", "HMAC-SHA512", "markers", List.of("hmacsha512", "createhmac('sha512", "createhmac(\"sha512")),
            Map.of("name", "MD5", "markers", List.of("cryptojs.md5", "md5(")),
            Map.of("name", "SHA1", "markers", List.of("cryptojs.sha1", "sha1(")),
            Map.of("name", "SHA256", "markers", List.of("cryptojs.sha256", "sha256(")),
            Map.of("name", "SHA512", "markers", List.of("cryptojs.sha512", "sha512(")),
            Map.of("name", "SHA3", "markers", List.of("cryptojs.sha3", "sha3")),
            Map.of("name", "RIPEMD160", "markers", List.of("ripemd160")),
            Map.of("name", "PBKDF2", "markers", List.of("cryptojs.pbkdf2", "pbkdf2")),
            Map.of("name", "scrypt", "markers", List.of("scrypt")),
            Map.of("name", "bcrypt", "markers", List.of("bcrypt")),
            Map.of("name", "HKDF", "markers", List.of("hkdf")),
            Map.of("name", "Base64", "markers", List.of("btoa(", "atob(", "base64")),
            Map.of("name", "JWT", "markers", List.of("jsonwebtoken.sign", "jsonwebtoken.verify", "jwt.sign", "jwt.verify", "jws.sign"))
        );

        ObjectNode root = objectMapper.createObjectNode();
        ArrayNode cryptoTypes = root.putArray("cryptoTypes");
        ArrayNode librariesNode = objectMapper.createArrayNode();
        ArrayNode operationsNode = objectMapper.createArrayNode();
        ArrayNode modesNode = objectMapper.createArrayNode();

        for (Map<String, Object> algorithm : algorithms) {
            @SuppressWarnings("unchecked")
            List<String> markers = (List<String>) algorithm.get("markers");
            int hits = countMatches(lowered, markers);
            if (hits == 0) {
                continue;
            }
            ArrayNode algModes = objectMapper.createArrayNode();
            for (Map.Entry<String, List<String>> entry : modeMarkers.entrySet()) {
                if (countMatches(lowered, entry.getValue()) > 0) {
                    algModes.add(entry.getKey());
                }
            }
            double confidence = Math.min(0.99, 0.55 + 0.12 * Math.min(hits, 3) + 0.03 * Math.min(algModes.size(), 3));
            ObjectNode crypto = cryptoTypes.addObject();
            crypto.put("name", String.valueOf(algorithm.get("name")));
            crypto.put("confidence", Math.round(confidence * 100.0) / 100.0);
            crypto.set("modes", algModes);
        }

        libraries.forEach((name, markers) -> {
            if (countMatches(lowered, markers) > 0) {
                librariesNode.add(name);
            }
        });
        operations.forEach((name, markers) -> {
            if (countMatches(lowered, markers) > 0) {
                operationsNode.add(name);
            }
        });
        modeMarkers.forEach((name, markers) -> {
            if (countMatches(lowered, markers) > 0) {
                modesNode.add(name);
            }
        });
        ArrayNode dynamicSourcesNode = objectMapper.createArrayNode();
        dynamicSourceMarkers.forEach((name, markers) -> {
            if (countMatches(lowered, markers) > 0) {
                dynamicSourcesNode.add(name);
            }
        });
        ArrayNode runtimeSelectorsNode = objectMapper.createArrayNode();
        runtimeSelectorMarkers.forEach((name, markers) -> {
            if (countMatches(lowered, markers) > 0) {
                runtimeSelectorsNode.add(name);
            }
        });
        ArrayNode obfuscationLoadersNode = objectMapper.createArrayNode();
        obfuscationLoaderMarkers.forEach((name, markers) -> {
            if (countMatches(lowered, markers) > 0) {
                obfuscationLoadersNode.add(name);
            }
        });
        ObjectNode algorithmAliases = objectMapper.createObjectNode();
        for (Map<String, Object> algorithm : algorithms) {
            @SuppressWarnings("unchecked")
            List<String> markers = (List<String>) algorithm.get("markers");
            java.util.Set<String> aliases = new java.util.TreeSet<>();
            for (String marker : markers) {
                if (lowered.contains(marker)) {
                    aliases.add(marker);
                }
            }
            if (!aliases.isEmpty()) {
                ArrayNode aliasNode = objectMapper.createArrayNode();
                aliases.forEach(aliasNode::add);
                algorithmAliases.set(String.valueOf(algorithm.get("name")), aliasNode);
            }
        }
        ArrayNode cryptoSinksNode = objectMapper.createArrayNode();
        sinkCatalog.forEach((name, markers) -> {
            if (countMatches(lowered, markers) > 0) {
                cryptoSinksNode.add(name);
            }
        });
        ArrayNode keyFlowCandidates = objectMapper.createArrayNode();
        Pattern assignmentPattern = Pattern.compile(
            "(?im)^\\s*(?:(?:const|let|var)\\s+)?([A-Za-z_$][\\w$]*(?:key|iv|nonce|salt|secret|token)[A-Za-z0-9_$]*)\\s*[:=]\\s*([^;\\r\\n]+)"
        );
        Map<String, List<String>> sourceDetailTokens = new LinkedHashMap<>();
        sourceDetailTokens.put("storage.localStorage", List.of("localstorage"));
        sourceDetailTokens.put("storage.sessionStorage", List.of("sessionstorage"));
        sourceDetailTokens.put("storage.indexedDB", List.of("indexeddb"));
        sourceDetailTokens.put("cookie.document", List.of("document.cookie"));
        sourceDetailTokens.put("navigator", List.of("navigator."));
        sourceDetailTokens.put("time.date", List.of("date.now", "new date("));
        sourceDetailTokens.put("time.performance", List.of("performance.now"));
        sourceDetailTokens.put("random.math", List.of("math.random"));
        sourceDetailTokens.put("random.crypto", List.of("getrandomvalues", "randombytes"));
        sourceDetailTokens.put("env.process", List.of("process.env"));
        sourceDetailTokens.put("env.import_meta", List.of("import.meta.env"));
        sourceDetailTokens.put("window.bootstrap", List.of("window.__", "globalthis.", "window["));
        sourceDetailTokens.put("network.fetch", List.of("fetch(", "await fetch"));
        sourceDetailTokens.put("network.xhr", List.of("xmlhttprequest", ".response"));
        sourceDetailTokens.put("network.axios", List.of("axios."));
        sourceDetailTokens.put("dom.querySelector", List.of("queryselector(", "queryselectorall("));
        sourceDetailTokens.put("dom.getElementById", List.of("getelementbyid("));
        sourceDetailTokens.put("url.searchParams", List.of("urlsearchparams", "searchparams.get("));
        Matcher assignmentMatcher = assignmentPattern.matcher(sourceCode);
        while (assignmentMatcher.find()) {
            String variable = assignmentMatcher.group(1).trim();
            String expression = assignmentMatcher.group(2).trim();
            String expressionLower = expression.toLowerCase();
            ArrayNode sourcesNode = objectMapper.createArrayNode();
            sourceDetailTokens.forEach((source, tokens) -> {
                if (tokens.stream().anyMatch(expressionLower::contains)) {
                    sourcesNode.add(source);
                }
            });
            if (!sourcesNode.isEmpty()) {
                ObjectNode flow = keyFlowCandidates.addObject();
                flow.put("variable", variable);
                flow.put("expression", expression.length() > 160 ? expression.substring(0, 160) : expression);
                flow.set("sources", sourcesNode);
                flow.put("dynamic", true);
            }
        }
        ArrayNode keyFlowChains = objectMapper.createArrayNode();
        Map<String, List<String>> derivationTokens = new LinkedHashMap<>();
        derivationTokens.put("hash", List.of("sha", "md5(", "ripemd", "digest("));
        derivationTokens.put("hmac", List.of("hmac"));
        derivationTokens.put("kdf", List.of("pbkdf2", "scrypt", "bcrypt", "hkdf"));
        derivationTokens.put("encode", List.of("btoa(", "atob(", "base64", "buffer.from", "tostring("));
        derivationTokens.put("concat", List.of("concat(", "+", "join("));
        derivationTokens.put("json", List.of("json.stringify", "json.parse"));
        derivationTokens.put("url", List.of("encodeuricomponent", "decodeuricomponent", "urlsearchparams"));
        List<String> codeLines = List.of(sourceCode.split("\\R"));
        Matcher seedMatcher = assignmentPattern.matcher(sourceCode);
        while (seedMatcher.find()) {
            String seedVariable = seedMatcher.group(1).trim();
            String seedExpression = seedMatcher.group(2).trim();
            ArrayNode sourceKinds = objectMapper.createArrayNode();
            sourceDetailTokens.forEach((source, tokens) -> {
                if (tokens.stream().anyMatch(seedExpression.toLowerCase()::contains)) {
                    sourceKinds.add(source);
                }
            });
            if (sourceKinds.isEmpty()) {
                continue;
            }
            java.util.Set<String> tracked = new java.util.LinkedHashSet<>();
            tracked.add(seedVariable);
            ArrayNode derivationsNode = objectMapper.createArrayNode();
            Matcher chainMatcher = assignmentPattern.matcher(sourceCode);
            chainMatcher.reset();
            while (chainMatcher.find()) {
                String targetVar = chainMatcher.group(1).trim();
                String expression = chainMatcher.group(2).trim();
                if (tracked.contains(targetVar)) {
                    continue;
                }
                boolean referencesTracked = tracked.stream().anyMatch(variable -> containsIdentifier(expression, variable));
                if (!referencesTracked) {
                    continue;
                }
                String kind = "propagate";
                String expressionLower = expression.toLowerCase();
                for (Map.Entry<String, List<String>> entry : derivationTokens.entrySet()) {
                    if (entry.getValue().stream().anyMatch(expressionLower::contains)) {
                        kind = entry.getKey();
                        break;
                    }
                }
                ObjectNode derivation = derivationsNode.addObject();
                derivation.put("variable", targetVar);
                derivation.put("kind", kind);
                derivation.put("expression", expression.length() > 160 ? expression.substring(0, 160) : expression);
                tracked.add(targetVar);
            }
            ArrayNode sinksNode = objectMapper.createArrayNode();
            sinkCatalog.forEach((sink, markers) -> {
                boolean matched = codeLines.stream().anyMatch(line -> {
                    String lowerLine = line.toLowerCase();
                    if (markers.stream().noneMatch(lowerLine::contains)) {
                        return false;
                    }
                    return tracked.stream().anyMatch(variable -> containsIdentifier(line, variable));
                });
                if (matched) {
                    sinksNode.add(sink);
                }
            });
            if (derivationsNode.isEmpty() && sinksNode.isEmpty()) {
                continue;
            }
            ObjectNode chain = keyFlowChains.addObject();
            chain.put("variable", seedVariable);
            ObjectNode source = chain.putObject("source");
            source.put("kind", sourceKinds.get(0).asText("unknown"));
            source.put("expression", seedExpression.length() > 160 ? seedExpression.substring(0, 160) : seedExpression);
            chain.set("derivations", derivationsNode);
            chain.set("sinks", sinksNode);
            double confidence = Math.min(0.99, 0.55 + (sinksNode.isEmpty() ? 0.0 : 0.10) + Math.min(0.18, derivationsNode.size() * 0.06) + (sourceKinds.isEmpty() ? 0.0 : 0.06));
            chain.put("confidence", Math.round(confidence * 100.0) / 100.0);
        }
        ArrayNode normalizedAlgorithms = objectMapper.createArrayNode();
        cryptoTypes.forEach(item -> normalizedAlgorithms.add(item.path("name").asText()));
        int riskScore = Math.min(
            100,
            (cryptoTypes.size() > 0 ? 18 : 0)
                + Math.min(20, dynamicSourcesNode.size() * 8)
                + Math.min(18, runtimeSelectorsNode.size() * 6)
                + Math.min(24, obfuscationLoadersNode.size() * 8)
                + Math.min(16, keyFlowCandidates.size() * 4)
                + Math.min(12, cryptoSinksNode.size() * 2)
                + (containsAnyNodeValue(normalizedAlgorithms, List.of("RSA", "ECDSA", "Ed25519", "X25519", "SM2")) ? 8 : 0)
                + (containsAnyNodeValue(librariesNode, List.of("WebCrypto", "NodeCrypto", "sodium")) ? 6 : 0)
                + (containsAnyNodeValue(normalizedAlgorithms, List.of("PBKDF2", "scrypt", "bcrypt", "HKDF")) ? 6 : 0)
        );
        ArrayNode recommendedApproach = objectMapper.createArrayNode();
        if (obfuscationLoadersNode.size() > 0) {
            recommendedApproach.add("unpack-loader-first");
        }
        if (dynamicSourcesNode.size() > 0) {
            recommendedApproach.add("trace-key-materialization");
        }
        if (runtimeSelectorsNode.size() > 0) {
            recommendedApproach.add("trace-algorithm-branch");
        }
        if (containsAnyNodeValue(librariesNode, List.of("WebCrypto"))) {
            recommendedApproach.add("hook-webcrypto");
        }
        if (containsAnyNodeValue(normalizedAlgorithms, List.of("JWT", "HMAC-SHA1", "HMAC-SHA256", "HMAC-SHA512"))) {
            recommendedApproach.add("rebuild-signing-canonicalization");
        }
        if (containsAnyNodeValue(normalizedAlgorithms, List.of("RSA", "ECDSA", "Ed25519", "X25519", "SM2"))) {
            recommendedApproach.add("capture-key-import-and-padding");
        }
        if (recommendedApproach.isEmpty()) {
            recommendedApproach.add("static-analysis-sufficient");
        }

        root.put("success", cryptoTypes.size() > 0);
        root.set("keys", valuesArray(code, "(?i)(?:const|let|var)?\\s*(?:appSecret|secret|privateKey|publicKey|aesKey|desKey|rsaKey|signKey|hmacKey|key)\\w*\\s*[:=]\\s*['\"`]([^'\"`\\r\\n]{4,128})['\"`]"));
        root.set("ivs", valuesArray(code, "(?i)(?:const|let|var)?\\s*(?:iv|nonce|salt)\\w*\\s*[:=]\\s*['\"`]([^'\"`\\r\\n]{4,128})['\"`]"));
        ObjectNode analysis = root.putObject("analysis");
        analysis.put("hasKeyDerivation", countMatches(lowered, operations.get("kdf")) > 0);
        analysis.put("hasRandomIV", lowered.contains("wordarray.random") || lowered.contains("randombytes") || lowered.contains("getrandomvalues") || lowered.contains("nonce") || lowered.contains("iv"));
        analysis.set("detectedLibraries", librariesNode);
        analysis.set("detectedOperations", operationsNode);
        analysis.set("detectedModes", modesNode);
        analysis.set("normalizedAlgorithms", normalizedAlgorithms);
        analysis.set("algorithmAliases", algorithmAliases);
        analysis.set("dynamicKeySources", dynamicSourcesNode);
        analysis.set("keyFlowCandidates", keyFlowCandidates);
        analysis.set("keyFlowChains", keyFlowChains);
        analysis.set("runtimeAlgorithmSelection", runtimeSelectorsNode);
        analysis.set("obfuscationLoaders", obfuscationLoadersNode);
        analysis.set("cryptoSinks", cryptoSinksNode);
        analysis.put("riskScore", riskScore);
        analysis.put("reverseComplexity", complexityLabel(riskScore));
        analysis.set("recommendedApproach", recommendedApproach);
        analysis.put("requiresASTDataflow", dynamicSourcesNode.size() > 0 || runtimeSelectorsNode.size() > 0 || obfuscationLoadersNode.size() > 0 || keyFlowCandidates.size() > 0);
        analysis.put("requiresRuntimeExecution", dynamicSourcesNode.size() > 0 || obfuscationLoadersNode.size() > 0 || containsAnyNodeValue(librariesNode, List.of("WebCrypto")) || cryptoSinksNode.size() > 0);
        analysis.put("requiresLoaderUnpack", obfuscationLoadersNode.size() > 0);
        return root;
    }

    private JsonNode mergeCryptoAnalysis(JsonNode remote, JsonNode local) {
        ObjectNode merged = remote != null && remote.isObject()
            ? ((ObjectNode) remote).deepCopy()
            : objectMapper.createObjectNode();
        ObjectNode localNode = local != null && local.isObject()
            ? (ObjectNode) local
            : objectMapper.createObjectNode();
        Map<String, ObjectNode> byName = new LinkedHashMap<>();

        for (JsonNode source : List.of(merged.path("cryptoTypes"), localNode.path("cryptoTypes"))) {
            if (!source.isArray()) {
                continue;
            }
            for (JsonNode node : source) {
                if (!node.isObject()) {
                    continue;
                }
                String name = node.path("name").asText("");
                if (name.isBlank()) {
                    continue;
                }
                ObjectNode target = byName.computeIfAbsent(name, key -> {
                    ObjectNode created = objectMapper.createObjectNode();
                    created.put("name", key);
                    created.put("confidence", 0.0);
                    created.putArray("modes");
                    return created;
                });
                target.put("confidence", Math.max(target.path("confidence").asDouble(0.0), node.path("confidence").asDouble(0.0)));
                ArrayNode modes = objectMapper.createArrayNode();
                Set<String> uniqueModes = new java.util.TreeSet<>();
                if (target.path("modes").isArray()) {
                    target.path("modes").forEach(item -> uniqueModes.add(item.asText()));
                }
                if (node.path("modes").isArray()) {
                    node.path("modes").forEach(item -> uniqueModes.add(item.asText()));
                }
                uniqueModes.forEach(modes::add);
                target.set("modes", modes);
            }
        }

        ArrayNode mergedTypes = objectMapper.createArrayNode();
        byName.values().stream()
            .sorted((left, right) -> {
                int confidenceCompare = Double.compare(right.path("confidence").asDouble(0.0), left.path("confidence").asDouble(0.0));
                return confidenceCompare != 0 ? confidenceCompare : left.path("name").asText("").compareTo(right.path("name").asText(""));
            })
            .forEach(mergedTypes::add);
        merged.set("cryptoTypes", mergedTypes);
        merged.set("keys", mergeUniqueArrays(merged.path("keys"), localNode.path("keys")));
        merged.set("ivs", mergeUniqueArrays(merged.path("ivs"), localNode.path("ivs")));

        ObjectNode analysis = merged.with("analysis");
        ObjectNode localAnalysis = localNode.path("analysis").isObject() ? (ObjectNode) localNode.path("analysis") : objectMapper.createObjectNode();
        analysis.put("hasKeyDerivation", analysis.path("hasKeyDerivation").asBoolean(false) || localAnalysis.path("hasKeyDerivation").asBoolean(false));
        analysis.put("hasRandomIV", analysis.path("hasRandomIV").asBoolean(false) || localAnalysis.path("hasRandomIV").asBoolean(false));
        analysis.set("detectedLibraries", mergeUniqueArrays(analysis.path("detectedLibraries"), localAnalysis.path("detectedLibraries")));
        analysis.set("detectedOperations", mergeUniqueArrays(analysis.path("detectedOperations"), localAnalysis.path("detectedOperations")));
        analysis.set("detectedModes", mergeUniqueArrays(analysis.path("detectedModes"), localAnalysis.path("detectedModes")));
        analysis.set("normalizedAlgorithms", mergeUniqueArrays(analysis.path("normalizedAlgorithms"), localAnalysis.path("normalizedAlgorithms")));
        analysis.set("algorithmAliases", mergeAliasMap(analysis.path("algorithmAliases"), localAnalysis.path("algorithmAliases")));
        analysis.set("dynamicKeySources", mergeUniqueArrays(analysis.path("dynamicKeySources"), localAnalysis.path("dynamicKeySources")));
        analysis.set("keyFlowCandidates", mergeFlowCandidates(analysis.path("keyFlowCandidates"), localAnalysis.path("keyFlowCandidates")));
        analysis.set("keyFlowChains", mergeFlowCandidates(analysis.path("keyFlowChains"), localAnalysis.path("keyFlowChains")));
        analysis.set("runtimeAlgorithmSelection", mergeUniqueArrays(analysis.path("runtimeAlgorithmSelection"), localAnalysis.path("runtimeAlgorithmSelection")));
        analysis.set("obfuscationLoaders", mergeUniqueArrays(analysis.path("obfuscationLoaders"), localAnalysis.path("obfuscationLoaders")));
        analysis.set("recommendedApproach", mergeUniqueArrays(analysis.path("recommendedApproach"), localAnalysis.path("recommendedApproach")));
        analysis.set("cryptoSinks", mergeUniqueArrays(analysis.path("cryptoSinks"), localAnalysis.path("cryptoSinks")));
        analysis.put("requiresASTDataflow", analysis.path("requiresASTDataflow").asBoolean(false) || localAnalysis.path("requiresASTDataflow").asBoolean(false));
        analysis.put("requiresRuntimeExecution", analysis.path("requiresRuntimeExecution").asBoolean(false) || localAnalysis.path("requiresRuntimeExecution").asBoolean(false));
        analysis.put("requiresLoaderUnpack", analysis.path("requiresLoaderUnpack").asBoolean(false) || localAnalysis.path("requiresLoaderUnpack").asBoolean(false));
        analysis.put("riskScore", Math.max(analysis.path("riskScore").asInt(0), localAnalysis.path("riskScore").asInt(0)));
        analysis.put("reverseComplexity", complexityLabel(analysis.path("riskScore").asInt(0)));

        if (merged.path("cryptoTypes").isArray() && merged.path("cryptoTypes").size() > 0 && !merged.path("success").asBoolean(false)) {
            merged.put("success", true);
        }
        return merged;
    }

    private int countMatches(String lowered, List<String> markers) {
        int total = 0;
        for (String marker : markers) {
            if (lowered.contains(marker)) {
                total++;
            }
        }
        return total;
    }

    private boolean containsIdentifier(String text, String identifier) {
        if (text == null || identifier == null || identifier.isBlank()) {
            return false;
        }
        int index = text.indexOf(identifier);
        while (index >= 0) {
            int before = index - 1;
            int after = index + identifier.length();
            boolean leftBoundary = before < 0 || !isIdentifierPart(text.charAt(before));
            boolean rightBoundary = after >= text.length() || !isIdentifierPart(text.charAt(after));
            if (leftBoundary && rightBoundary) {
                return true;
            }
            index = text.indexOf(identifier, index + 1);
        }
        return false;
    }

    private boolean isIdentifierPart(char value) {
        return Character.isLetterOrDigit(value) || value == '_' || value == '$';
    }

    private ArrayNode valuesArray(String code, String regex) {
        ArrayNode values = objectMapper.createArrayNode();
        Set<String> seen = new java.util.LinkedHashSet<>();
        Matcher matcher = Pattern.compile(regex).matcher(code == null ? "" : code);
        while (matcher.find() && seen.size() < 8) {
            String value = matcher.group(1).trim();
            if (value.length() < 4 || value.length() > 128 || !seen.add(value)) {
                continue;
            }
            values.add(value);
        }
        return values;
    }

    private ArrayNode mergeUniqueArrays(JsonNode first, JsonNode second) {
        Set<String> values = new java.util.TreeSet<>();
        if (first.isArray()) {
            first.forEach(item -> values.add(item.asText()));
        }
        if (second.isArray()) {
            second.forEach(item -> values.add(item.asText()));
        }
        ArrayNode merged = objectMapper.createArrayNode();
        values.forEach(merged::add);
        return merged;
    }

    private boolean containsAnyNodeValue(JsonNode values, List<String> expected) {
        if (!values.isArray()) {
            return false;
        }
        java.util.Set<String> actual = new java.util.HashSet<>();
        values.forEach(item -> actual.add(item.asText()));
        return expected.stream().anyMatch(actual::contains);
    }

    private String complexityLabel(int score) {
        if (score >= 80) {
            return "extreme";
        }
        if (score >= 55) {
            return "high";
        }
        if (score >= 30) {
            return "medium";
        }
        return "low";
    }

    private ObjectNode mergeAliasMap(JsonNode first, JsonNode second) {
        ObjectNode merged = objectMapper.createObjectNode();
        java.util.Map<String, java.util.Set<String>> aliases = new LinkedHashMap<>();
        for (JsonNode node : List.of(first, second)) {
            if (!node.isObject()) {
                continue;
            }
            node.fields().forEachRemaining(entry -> {
                java.util.Set<String> values = aliases.computeIfAbsent(entry.getKey(), key -> new java.util.TreeSet<>());
                if (entry.getValue().isArray()) {
                    entry.getValue().forEach(item -> values.add(item.asText()));
                }
            });
        }
        aliases.forEach((name, values) -> {
            ArrayNode valueNode = objectMapper.createArrayNode();
            values.forEach(valueNode::add);
            merged.set(name, valueNode);
        });
        return merged;
    }

    private ArrayNode mergeFlowCandidates(JsonNode first, JsonNode second) {
        ArrayNode merged = objectMapper.createArrayNode();
        java.util.Set<String> seen = new java.util.LinkedHashSet<>();
        for (JsonNode source : List.of(first, second)) {
            if (!source.isArray()) {
                continue;
            }
            for (JsonNode item : source) {
                String key = item.path("variable").asText("") + "|" + item.path("expression").asText("");
                if (!seen.add(key)) {
                    continue;
                }
                merged.add(item);
            }
        }
        return merged;
    }
}
