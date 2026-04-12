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

    private static void respond(HttpExchange exchange, String body) throws IOException {
        exchange.getResponseHeaders().add("Content-Type", "application/json");
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.sendResponseHeaders(200, bytes.length);
        try (OutputStream outputStream = exchange.getResponseBody()) {
            outputStream.write(bytes);
        }
    }
}
