package com.javaspider.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import okhttp3.*;

import java.io.IOException;
import java.util.List;
import java.util.Map;

/**
 * Crawlee 桥接客户端
 * 允许 Java Spider 调用 Crawlee 的动态渲染和反爬能力
 */
public class CrawleeBridgeClient {
    private final OkHttpClient httpClient;
    private final String bridgeUrl;
    private final ObjectMapper mapper;

    public CrawleeBridgeClient(String bridgeUrl) {
        this.bridgeUrl = bridgeUrl;
        this.httpClient = new OkHttpClient();
        this.mapper = new ObjectMapper();
    }

    /**
     * 执行 Crawlee 抓取任务
     * 
     * @param urls 目标 URL 列表
     * @param script 可选的页面执行脚本
     * @return 抓取结果
     */
    public JsonNode crawl(List<String> urls, String script) throws IOException {
        Map<String, Object> payload = Map.of(
            "urls", urls,
            "onPageScript", script != null ? script : "",
            "maxConcurrency", 2
        );

        RequestBody body = RequestBody.create(
            mapper.writeValueAsString(payload),
            MediaType.parse("application/json")
        );

        Request request = new Request.Builder()
            .url(bridgeUrl + "/api/crawl")
            .post(body)
            .build();

        try (Response response = httpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("Crawlee Bridge Error: " + response);
            }
            return mapper.readTree(response.body().string());
        }
    }
}
