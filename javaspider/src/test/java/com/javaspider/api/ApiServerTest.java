package com.javaspider.api;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ApiServerTest {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Test
    void servesHealthAndJobEndpoints() throws Exception {
        ApiServer server = new ApiServer("127.0.0.1", 0);
        server.start();
        try {
            HttpClient client = HttpClient.newHttpClient();
            String base = "http://127.0.0.1:" + server.port();

            HttpResponse<String> health = client.send(
                HttpRequest.newBuilder(URI.create(base + "/health")).GET().build(),
                HttpResponse.BodyHandlers.ofString()
            );
            assertEquals(200, health.statusCode());
            assertTrue(health.body().contains("\"status\":\"ok\""));

            HttpResponse<String> created = client.send(
                HttpRequest.newBuilder(URI.create(base + "/jobs"))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString("""
                        {
                          "name": "api-job",
                          "runtime": "browser",
                          "target": { "url": "https://example.com" },
                          "metadata": {
                            "mock_extract": { "title": "API Job Result" }
                          }
                        }
                        """))
                    .build(),
                HttpResponse.BodyHandlers.ofString()
            );
            assertEquals(202, created.statusCode());
            Map<String, Object> payload = MAPPER.readValue(created.body(), new TypeReference<Map<String, Object>>() {});
            assertTrue(java.util.Set.of("accepted", "running", "succeeded").contains(String.valueOf(payload.get("status"))));
            assertEquals("browser", payload.get("runtime"));

            String jobId = String.valueOf(payload.get("job_id"));
            HttpResponse<String> listed = client.send(
                HttpRequest.newBuilder(URI.create(base + "/jobs")).GET().build(),
                HttpResponse.BodyHandlers.ofString()
            );
            assertEquals(200, listed.statusCode());
            assertTrue(listed.body().contains(jobId));

            HttpResponse<String> detail = client.send(
                HttpRequest.newBuilder(URI.create(base + "/jobs/" + jobId)).GET().build(),
                HttpResponse.BodyHandlers.ofString()
            );
            assertEquals(200, detail.statusCode());
            assertTrue(detail.body().contains("\"job_id\":\"" + jobId + "\""));

            Map<String, Object> finished = awaitJob(client, base, jobId);
            assertEquals("succeeded", finished.get("status"));
            assertTrue(String.valueOf(finished.get("result")).contains("API Job Result"));

            HttpResponse<String> result = client.send(
                HttpRequest.newBuilder(URI.create(base + "/jobs/" + jobId + "/result")).GET().build(),
                HttpResponse.BodyHandlers.ofString()
            );
            assertEquals(200, result.statusCode());
            assertTrue(result.body().contains("\"state\":\"succeeded\""));
        } finally {
            server.stop();
        }
    }

    private Map<String, Object> awaitJob(HttpClient client, String base, String jobId) throws Exception {
        for (int attempt = 0; attempt < 100; attempt++) {
            HttpResponse<String> detail = client.send(
                HttpRequest.newBuilder(URI.create(base + "/jobs/" + jobId)).GET().build(),
                HttpResponse.BodyHandlers.ofString()
            );
            Map<String, Object> payload = MAPPER.readValue(detail.body(), new TypeReference<Map<String, Object>>() {});
            if (!"accepted".equals(payload.get("status")) && !"running".equals(payload.get("status"))) {
                return payload;
            }
            Thread.sleep(50);
        }
        throw new AssertionError("job did not finish in time");
    }
}
