package com.javaspider.web.controller;

import com.javaspider.core.Spider;
import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpExchange;

import java.io.*;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Spider 管理控制器 - 纯 Java 实现 (无需 Spring)
 * 使用 Java 内置的 HttpServer
 */
public class SpiderController {
    
    private final Map<String, SpiderInstance> spiders = new ConcurrentHashMap<>();
    private HttpServer server;
    private ExecutorService executor;
    
    /**
     * 启动 Web 服务器
     */
    public void start(int port) throws IOException {
        server = HttpServer.create(new InetSocketAddress(port), 0);
        executor = Executors.newFixedThreadPool(4);
        server.setExecutor(executor);
        
        // 设置路由
        server.createContext("/api/spiders", new SpidersHandler());
        server.createContext("/api/spiders/", new SpiderDetailHandler());
        server.createContext("/api/stats", new StatsHandler());
        server.createContext("/", new IndexHandler());
        
        server.start();
        System.out.println("Web UI started at http://localhost:" + port);
    }
    
    /**
     * 停止 Web 服务器
     */
    public void stop() {
        if (server != null) {
            server.stop(0);
        }
        if (executor != null) {
            executor.shutdown();
        }
    }
    
    /**
     * 注册爬虫实例
     */
    public void registerSpider(String id, Spider spider) {
        spiders.put(id, new SpiderInstance(spider));
    }
    
    // ==================== Request Handlers ====================
    
    private class IndexHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String response = "<html><body><h1>JavaSpider Web UI</h1><p>Visit /api/spiders for API</p></body></html>";
            sendResponse(exchange, 200, response, "text/html");
        }
    }
    
    private class SpidersHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String method = exchange.getRequestMethod();
            
            if ("GET".equals(method)) {
                listSpiders(exchange);
            } else if ("POST".equals(method)) {
                createSpider(exchange);
            } else {
                sendError(exchange, 405, "Method not allowed");
            }
        }
        
        private void listSpiders(HttpExchange exchange) throws IOException {
            List<Map<String, Object>> list = new ArrayList<>();
            for (Map.Entry<String, SpiderInstance> entry : spiders.entrySet()) {
                Map<String, Object> info = new HashMap<>();
                info.put("id", entry.getKey());
                info.put("name", entry.getValue().spider.getClass().getSimpleName());
                info.put("running", entry.getValue().running);
                info.put("stats", entry.getValue().getStats());
                list.add(info);
            }
            
            String response = toJson(list);
            sendResponse(exchange, 200, response, "application/json");
        }
        
        private void createSpider(HttpExchange exchange) throws IOException {
            // 简化实现，实际应该解析请求体
            String id = "spider_" + System.currentTimeMillis();
            String response = "{\"success\":true,\"data\":{\"id\":\"" + id + "\"}}";
            sendResponse(exchange, 200, response, "application/json");
        }
    }
    
    private class SpiderDetailHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String path = exchange.getRequestURI().getPath();
            String[] parts = path.split("/");
            
            if (parts.length < 4) {
                sendError(exchange, 400, "Invalid path");
                return;
            }
            
            String id = parts[3];
            String action = parts.length > 4 ? parts[4] : "";
            
            if ("".equals(action)) {
                getSpider(exchange, id);
            } else if ("start".equals(action) && "POST".equals(exchange.getRequestMethod())) {
                startSpider(exchange, id);
            } else if ("stop".equals(action) && "POST".equals(exchange.getRequestMethod())) {
                stopSpider(exchange, id);
            } else if ("status".equals(action)) {
                getStatus(exchange, id);
            } else {
                sendError(exchange, 404, "Not found");
            }
        }
        
        private void getSpider(HttpExchange exchange, String id) throws IOException {
            SpiderInstance instance = spiders.get(id);
            if (instance == null) {
                sendError(exchange, 404, "Spider not found");
                return;
            }
            
            Map<String, Object> info = new HashMap<>();
            info.put("id", id);
            info.put("name", instance.spider.getClass().getSimpleName());
            info.put("running", instance.running);
            info.put("stats", instance.getStats());
            
            String response = toJson(info);
            sendResponse(exchange, 200, response, "application/json");
        }
        
        private void startSpider(HttpExchange exchange, String id) throws IOException {
            SpiderInstance instance = spiders.get(id);
            if (instance == null) {
                sendError(exchange, 404, "Spider not found");
                return;
            }
            
            instance.start();
            String response = "{\"success\":true,\"message\":\"Spider started\"}";
            sendResponse(exchange, 200, response, "application/json");
        }
        
        private void stopSpider(HttpExchange exchange, String id) throws IOException {
            SpiderInstance instance = spiders.get(id);
            if (instance == null) {
                sendError(exchange, 404, "Spider not found");
                return;
            }
            
            instance.stop();
            String response = "{\"success\":true,\"message\":\"Spider stopped\"}";
            sendResponse(exchange, 200, response, "application/json");
        }
        
        private void getStatus(HttpExchange exchange, String id) throws IOException {
            SpiderInstance instance = spiders.get(id);
            if (instance == null) {
                sendError(exchange, 404, "Spider not found");
                return;
            }
            
            Map<String, Object> status = new HashMap<>();
            status.put("id", id);
            status.put("running", instance.running);
            status.put("stats", instance.getStats());
            
            String response = toJson(status);
            sendResponse(exchange, 200, response, "application/json");
        }
    }
    
    private class StatsHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            Map<String, Object> stats = new HashMap<>();
            stats.put("total_spiders", spiders.size());
            stats.put("running_spiders", countRunning());
            
            String response = toJson(stats);
            sendResponse(exchange, 200, response, "application/json");
        }
        
        private int countRunning() {
            int count = 0;
            for (SpiderInstance instance : spiders.values()) {
                if (instance.running) count++;
            }
            return count;
        }
    }
    
    // ==================== Helper Methods ====================
    
    private void sendResponse(HttpExchange exchange, int code, String body, String contentType) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", contentType);
        exchange.getResponseHeaders().set("Access-Control-Allow-Origin", "*");
        exchange.sendResponseHeaders(code, bytes.length);
        
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(bytes);
        }
    }
    
    private void sendError(HttpExchange exchange, int code, String message) throws IOException {
        String response = "{\"success\":false,\"error\":\"" + message + "\"}";
        sendResponse(exchange, code, response, "application/json");
    }
    
    private String toJson(Object obj) {
        if (obj instanceof List) {
            return listToJson((List<?>) obj);
        } else if (obj instanceof Map) {
            return mapToJson((Map<?, ?>) obj);
        }
        return "{}";
    }
    
    private String listToJson(List<?> list) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < list.size(); i++) {
            if (i > 0) sb.append(",");
            sb.append(toJson(list.get(i)));
        }
        sb.append("]");
        return sb.toString();
    }
    
    private String mapToJson(Map<?, ?> map) {
        StringBuilder sb = new StringBuilder("{");
        boolean first = true;
        for (Map.Entry<?, ?> entry : map.entrySet()) {
            if (!first) sb.append(",");
            first = false;
            sb.append("\"").append(entry.getKey()).append("\":");
            Object value = entry.getValue();
            if (value instanceof String) {
                sb.append("\"").append(value).append("\"");
            } else if (value instanceof Boolean || value instanceof Number) {
                sb.append(value);
            } else if (value instanceof Map) {
                sb.append(mapToJson((Map<?, ?>) value));
            } else {
                sb.append("\"").append(String.valueOf(value)).append("\"");
            }
        }
        sb.append("}");
        return sb.toString();
    }
    
    // ==================== Inner Classes ====================
    
    static class SpiderInstance {
        private final Spider spider;
        private Thread thread;
        private volatile boolean running;
        
        SpiderInstance(Spider spider) {
            this.spider = spider;
        }
        
        void start() {
            if (!running) {
                running = true;
                thread = new Thread(() -> {
                    try {
                        spider.run();
                    } finally {
                        running = false;
                    }
                });
                thread.start();
            }
        }
        
        void stop() {
            running = false;
            spider.stop();
        }
        
        Map<String, Object> getStats() {
            Map<String, Object> stats = new HashMap<>();
            stats.put("totalRequests", spider.getTotalRequests());
            stats.put("successRequests", spider.getSuccessRequests());
            stats.put("failedRequests", spider.getFailedRequests());
            stats.put("qps", 0); // Placeholder
            return stats;
        }
    }
}
