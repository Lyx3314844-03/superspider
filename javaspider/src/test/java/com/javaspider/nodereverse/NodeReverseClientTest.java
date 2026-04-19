package com.javaspider.nodereverse;

import com.fasterxml.jackson.databind.JsonNode;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class NodeReverseClientTest {

    @Test
    void profileAntiBotUsesProfileEndpoint() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(0), 0);
        server.createContext("/api/anti-bot/profile", exchange -> respond(exchange,
            "{\"success\":true,\"level\":\"high\",\"signals\":[\"managed-browser-challenge\"]}"
        ));
        server.start();

        try {
            NodeReverseClient client = new NodeReverseClient("http://localhost:" + server.getAddress().getPort());
            JsonNode response = client.profileAntiBot(
                "<title>Just a moment...</title>",
                "eval(function(p,a,c,k,e,d){return p;});",
                Map.of("cf-ray", "token"),
                "__cf_bm=token",
                429,
                "https://target.example/challenge"
            );

            assertTrue(response.get("success").asBoolean());
            assertEquals("high", response.get("level").asText());
            assertEquals("managed-browser-challenge", response.get("signals").get(0).asText());
        } finally {
            server.stop(0);
        }
    }

    @Test
    void detectAntiBotUsesDetectEndpoint() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(0), 0);
        server.createContext("/api/anti-bot/detect", exchange -> respond(exchange,
            "{\"success\":true,\"detection\":{\"hasCloudflare\":true},\"signals\":[\"vendor:cloudflare\"]}"
        ));
        server.start();

        try {
            NodeReverseClient client = new NodeReverseClient("http://localhost:" + server.getAddress().getPort());
            JsonNode response = client.detectAntiBot(
                "",
                "",
                Map.of("cf-ray", "token"),
                "",
                403,
                "https://target.example"
            );

            assertTrue(response.get("success").asBoolean());
            assertTrue(response.get("detection").get("hasCloudflare").asBoolean());
        } finally {
            server.stop(0);
        }
    }

    @Test
    void spoofFingerprintUsesSpoofEndpoint() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(0), 0);
        server.createContext("/api/fingerprint/spoof", exchange -> respond(exchange,
            "{\"success\":true,\"browser\":\"chrome\",\"platform\":\"windows\",\"fingerprint\":{\"userAgent\":\"mock\"}}"
        ));
        server.start();

        try {
            NodeReverseClient client = new NodeReverseClient("http://localhost:" + server.getAddress().getPort());
            JsonNode response = client.spoofFingerprint("chrome", "windows");

            assertTrue(response.get("success").asBoolean());
            assertEquals("chrome", response.get("browser").asText());
            assertEquals("windows", response.get("platform").asText());
        } finally {
            server.stop(0);
        }
    }

    @Test
    void generateTlsFingerprintUsesTlsEndpoint() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(0), 0);
        server.createContext("/api/tls/fingerprint", exchange -> respond(exchange,
            "{\"success\":true,\"browser\":\"chrome\",\"version\":\"120\",\"fingerprint\":{\"ja3\":\"mock-ja3\"}}"
        ));
        server.start();

        try {
            NodeReverseClient client = new NodeReverseClient("http://localhost:" + server.getAddress().getPort());
            JsonNode response = client.generateTlsFingerprint("chrome", "120");

            assertTrue(response.get("success").asBoolean());
            assertEquals("120", response.get("version").asText());
            assertEquals("mock-ja3", response.get("fingerprint").get("ja3").asText());
        } finally {
            server.stop(0);
        }
    }

    @Test
    void simulateBrowserUsesBrowserEndpoint() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(0), 0);
        server.createContext("/api/browser/simulate", exchange -> respond(exchange,
            "{\"success\":true,\"result\":{\"ok\":true},\"cookies\":\"session=1\"}"
        ));
        server.start();

        try {
            NodeReverseClient client = new NodeReverseClient("http://localhost:" + server.getAddress().getPort());
            JsonNode response = client.simulateBrowser(
                "navigator.userAgent",
                Map.of("userAgent", "mock", "language", "zh-CN", "platform", "Win32")
            );

            assertTrue(response.get("success").asBoolean());
            assertEquals("session=1", response.get("cookies").asText());
        } finally {
            server.stop(0);
        }
    }

    @Test
    void callFunctionUsesFunctionEndpoint() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(0), 0);
        server.createContext("/api/function/call", exchange -> respond(exchange,
            "{\"success\":true,\"result\":\"left|right\"}"
        ));
        server.start();

        try {
            NodeReverseClient client = new NodeReverseClient("http://localhost:" + server.getAddress().getPort());
            JsonNode response = client.callFunction(
                "sign",
                java.util.List.of("left", "right"),
                "function sign(a,b){return a+'|'+b;}"
            );

            assertTrue(response.get("success").asBoolean());
            assertEquals("left|right", response.get("result").asText());
        } finally {
            server.stop(0);
        }
    }

    @Test
    void canvasFingerprintUsesCanvasEndpoint() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(0), 0);
        server.createContext("/api/canvas/fingerprint", exchange -> respond(exchange,
            "{\"success\":true,\"hash\":\"mock-canvas\"}"
        ));
        server.start();

        try {
            NodeReverseClient client = new NodeReverseClient("http://localhost:" + server.getAddress().getPort());
            JsonNode response = client.canvasFingerprint();

            assertTrue(response.get("success").asBoolean());
            assertEquals("mock-canvas", response.get("hash").asText());
        } finally {
            server.stop(0);
        }
    }

    @Test
    void reverseSignatureUsesSignatureEndpoint() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(0), 0);
        server.createContext("/api/signature/reverse", exchange -> respond(exchange,
            "{\"success\":true,\"functionName\":\"sign\"}"
        ));
        server.start();

        try {
            NodeReverseClient client = new NodeReverseClient("http://localhost:" + server.getAddress().getPort());
            JsonNode response = client.reverseSignature("function sign(v){return v;}", "left", "left");

            assertTrue(response.get("success").asBoolean());
            assertEquals("sign", response.get("functionName").asText());
        } finally {
            server.stop(0);
        }
    }

    @Test
    void analyzeCryptoFallsBackToLocalMultiAlgorithmHeuristics() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(0), 0);
        server.createContext("/api/crypto/analyze", exchange -> {
            exchange.sendResponseHeaders(500, -1);
            exchange.close();
        });
        server.start();

        try {
            NodeReverseClient client = new NodeReverseClient("http://localhost:" + server.getAddress().getPort());
            JsonNode response = client.analyzeCrypto("""
                const key = "secret-key-1234";
                const iv = "nonce-001";
                const token = CryptoJS.HmacSHA256(data, key).toString();
                const cipher = sm4.encrypt(data, key, { mode: "cbc" });
                const digest = CryptoJS.SHA256(data).toString();
                const derived = CryptoJS.PBKDF2(password, salt, { keySize: 8 });
                const sessionKey = localStorage.getItem("session-key");
                const derivedKey = sha256(sessionKey || key);
                window.crypto.subtle.encrypt({ name: "AES-GCM", iv }, derivedKey, data);
                """);

            java.util.Set<String> names = new java.util.HashSet<>();
            response.get("cryptoTypes").forEach(item -> names.add(item.get("name").asText()));
            assertTrue(names.contains("AES"));
            assertTrue(names.contains("SM4"));
            assertTrue(names.contains("HMAC-SHA256"));
            assertTrue(names.contains("SHA256"));
            assertTrue(names.contains("PBKDF2"));
            assertEquals("secret-key-1234", response.get("keys").get(0).asText());
            assertEquals("nonce-001", response.get("ivs").get(0).asText());
            assertTrue(response.get("analysis").get("cryptoSinks").toString().contains("crypto.subtle.encrypt"));
            assertTrue(response.get("analysis").get("algorithmAliases").get("AES").toString().contains("aes-gcm"));
            assertTrue(response.get("analysis").get("keyFlowCandidates").toString().contains("sessionKey"));
            assertTrue(response.get("analysis").get("keyFlowCandidates").toString().contains("storage.localStorage"));
            assertTrue(response.get("analysis").get("keyFlowChains").toString().contains("derivedKey"));
            assertTrue(response.get("analysis").get("keyFlowChains").toString().contains("crypto.subtle.encrypt"));
            assertTrue(response.get("analysis").get("riskScore").asInt() >= 30);
            assertTrue(response.get("analysis").get("requiresASTDataflow").asBoolean());
            assertTrue(response.get("analysis").get("recommendedApproach").toString().contains("trace-key-materialization"));
        } finally {
            server.stop(0);
        }
    }

    private static void respond(HttpExchange exchange, String body) throws IOException {
        exchange.getResponseHeaders().add("Content-Type", "application/json");
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.sendResponseHeaders(200, bytes.length);
        try (OutputStream outputStream = exchange.getResponseBody()) {
            outputStream.write(bytes);
        }
    }
}
