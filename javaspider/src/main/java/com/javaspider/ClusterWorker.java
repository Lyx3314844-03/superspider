package com.javaspider;

import com.google.gson.Gson;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Omega-Spider Cluster - Java Worker 专家版
 */
public class ClusterWorker {
    private final String id;
    private final String masterUrl;
    private final HttpClient httpClient;
    private final Gson gson = new Gson();
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();

    public ClusterWorker(String masterUrl) {
        this.id = "java-worker-" + UUID.randomUUID().toString().substring(0, 8);
        this.masterUrl = masterUrl;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .build();
    }

    public void run() {
        System.out.println("❖ Java Expert Worker [" + id + "] 启动 ❖");
        
        // 启动后台心跳
        startHeartbeat();

        while (true) {
            try {
                Task task = pullTask();
                if (task == null) {
                    Thread.sleep(5000);
                    continue;
                }

                System.out.println("处理任务: " + task.url);
                Map<String, Object> result = executeTask(task);
                submitResult(task.url, "completed", result);

            } catch (Exception e) {
                System.err.println("错误: " + e.getMessage());
                try { Thread.sleep(10000); } catch (InterruptedException ignored) {}
            }
        }
    }

    private void startHeartbeat() {
        scheduler.scheduleAtFixedRate(() -> {
            try {
                Map<String, Object> payload = new HashMap<>();
                payload.put("id", id);
                payload.put("lang", "java");
                payload.put("stats", Map.of("running", true));

                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(masterUrl + "/worker/heartbeat"))
                        .header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(gson.toJson(payload)))
                        .build();

                httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            } catch (Exception ignored) {}
        }, 0, 30, TimeUnit.SECONDS);
    }

    private Task pullTask() throws Exception {
        HttpRequest request = HttpRequest.newBuilder().uri(URI.create(masterUrl + "/task/get")).GET().build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return response.statusCode() == 200 ? gson.fromJson(response.body(), Task.class) : null;
    }

    private Map<String, Object> executeTask(Task task) throws Exception {
        HttpRequest request = HttpRequest.newBuilder().uri(URI.create(task.url)).GET().build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        
        Map<String, Object> data = new HashMap<>();
        data.put("content_length", response.body().length());
        data.put("worker_lang", "java");
        return data;
    }

    private void submitResult(String url, String status, Map<String, Object> data) throws Exception {
        Map<String, Object> payload = new HashMap<>();
        payload.put("url", url);
        payload.put("status", status);
        payload.put("data", data);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(masterUrl + "/task/submit"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(gson.toJson(payload)))
                .build();
        httpClient.send(request, HttpResponse.BodyHandlers.ofString());
    }

    private static class Task { String url; int id; }

    public static void main(String[] args) {
        new ClusterWorker("http://localhost:5000").run();
    }
}
