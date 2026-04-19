package com.javaspider.research;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ResearchRuntimeTest {

    @Test
    void researchJobIsConstructible() {
        ResearchJob job = new ResearchJob(List.of("https://example.com"));
        assertEquals(List.of("https://example.com"), job.getSeedUrls());
    }

    @Test
    void researchRuntimeRunsJob() {
        ResearchRuntime runtime = new ResearchRuntime();
        Map<String, Object> result = runtime.run(
            new ResearchJob(
                List.of("https://example.com"),
                Map.of(),
                Map.of("properties", Map.of("title", Map.of("type", "string"))),
                List.of(),
                Map.of(),
                Map.of()
            ),
            "<title>Java Research Demo</title>"
        );

        @SuppressWarnings("unchecked")
        Map<String, Object> extract = (Map<String, Object>) result.get("extract");
        assertEquals("Java Research Demo", extract.get("title"));
    }

    @Test
    void researchRuntimeWritesJsonlDataset() throws Exception {
        ResearchRuntime runtime = new ResearchRuntime();
        Path output = Files.createTempDirectory("java-research").resolve("rows.jsonl");
        Map<String, Object> result = runtime.run(
            new ResearchJob(
                List.of("https://example.com"),
                Map.of(),
                Map.of("properties", Map.of("title", Map.of("type", "string"))),
                List.of(),
                Map.of(),
                Map.of("format", "jsonl", "path", output.toString())
            ),
            "<title>Java Dataset Demo</title>"
        );

        @SuppressWarnings("unchecked")
        Map<String, Object> dataset = (Map<String, Object>) result.get("dataset");
        assertEquals(output.toString(), dataset.get("path"));
        assertTrue(Files.exists(output));
    }

    @Test
    void researchRuntimeValidatesRequiredAndSchemaForSpecs() {
        ResearchRuntime runtime = new ResearchRuntime();
        IllegalArgumentException error = assertThrows(
            IllegalArgumentException.class,
            () -> runtime.run(
                new ResearchJob(
                    List.of("https://example.com"),
                    Map.of(),
                    Map.of("properties", Map.of("price", Map.of("type", "number"))),
                    List.of(Map.of(
                        "field", "price",
                        "type", "regex",
                        "expr", "price:\\s*(\\w+)",
                        "required", true
                    )),
                    Map.of(),
                    Map.of()
                ),
                "<title>Demo</title>\nprice: free"
            )
        );
        assertTrue(error.getMessage().contains("schema.type=number"));
    }

    @Test
    void researchRuntimeSupportsXPathAndJsonPathSpecs() {
        ResearchRuntime runtime = new ResearchRuntime();
        Map<String, Object> cssResult = runtime.run(
            new ResearchJob(
                List.of("https://example.com"),
                Map.of(),
                Map.of(),
                List.of(
                    Map.of("field", "title", "type", "css", "expr", "title", "required", true),
                    Map.of("field", "cover", "type", "css_attr", "expr", "meta[name=og:image]", "attr", "content", "required", true)
                ),
                Map.of(),
                Map.of()
            ),
            "<html><head><title>CSS Demo</title><meta name=\"og:image\" content=\"https://img.example.com/cover.jpg\" /></head></html>"
        );
        @SuppressWarnings("unchecked")
        Map<String, Object> cssExtract = (Map<String, Object>) cssResult.get("extract");
        assertEquals("CSS Demo", cssExtract.get("title"));
        assertEquals("https://img.example.com/cover.jpg", cssExtract.get("cover"));

        Map<String, Object> xpathResult = runtime.run(
            new ResearchJob(
                List.of("https://example.com"),
                Map.of(),
                Map.of(),
                List.of(Map.of("field", "title", "type", "xpath", "expr", "//title/text()", "required", true)),
                Map.of(),
                Map.of()
            ),
            "<html><title>XPath Demo</title></html>"
        );
        @SuppressWarnings("unchecked")
        Map<String, Object> xpathExtract = (Map<String, Object>) xpathResult.get("extract");
        assertEquals("XPath Demo", xpathExtract.get("title"));

        Map<String, Object> jsonResult = runtime.run(
            new ResearchJob(
                List.of("https://example.com"),
                Map.of(),
                Map.of(),
                List.of(Map.of("field", "name", "type", "json_path", "path", "$.product.name", "required", true)),
                Map.of(),
                Map.of()
            ),
            "{\"product\":{\"name\":\"Capsule\"}}"
        );
        @SuppressWarnings("unchecked")
        Map<String, Object> jsonExtract = (Map<String, Object>) jsonResult.get("extract");
        assertEquals("Capsule", jsonExtract.get("name"));
    }

    @Test
    void asyncResearchRuntimeRunsMultipleJobs() {
        try (AsyncResearchRuntime runtime = new AsyncResearchRuntime(new AsyncResearchConfig(2, 10.0, false))) {
            List<AsyncResearchResult> results = runtime.runMultiple(
                List.of(
                    new ResearchJob(List.of("https://example.com/1"), Map.of(), Map.of("properties", Map.of("title", Map.of("type", "string"))), List.of(), Map.of(), Map.of()),
                    new ResearchJob(List.of("https://example.com/2"), Map.of(), Map.of("properties", Map.of("title", Map.of("type", "string"))), List.of(), Map.of(), Map.of())
                ),
                List.of("<title>One</title>", "<title>Two</title>")
            );

            assertEquals(2, results.size());
            assertTrue(results.stream().allMatch(result -> result.error().isBlank()));
            assertEquals(2, runtime.snapshotMetrics().get("tasks_completed"));
            assertFalse(results.isEmpty());
        }
    }

    @Test
    void asyncResearchRuntimeSupportsStreamAndSoak() {
        try (AsyncResearchRuntime runtime = new AsyncResearchRuntime(new AsyncResearchConfig(2, 10.0, false))) {
            List<ResearchJob> jobs = List.of(
                new ResearchJob(List.of("https://example.com/1"), Map.of(), Map.of("properties", Map.of("title", Map.of("type", "string"))), List.of(), Map.of("simulate_delay_ms", 10), Map.of()),
                new ResearchJob(List.of("https://example.com/2"), Map.of(), Map.of("properties", Map.of("title", Map.of("type", "string"))), List.of(), Map.of("simulate_delay_ms", 10), Map.of())
            );
            int streamCount = 0;
            for (AsyncResearchResult result : runtime.runStream(jobs, List.of("<title>One</title>", "<title>Two</title>"))) {
                assertTrue(result.error().isBlank());
                streamCount++;
            }
            assertEquals(2, streamCount);

            Map<String, Object> soak = runtime.runSoak(jobs, List.of("<title>One</title>", "<title>Two</title>"), 2);
            assertEquals(4, soak.get("results"));
            assertEquals(Boolean.TRUE, soak.get("stable"));
        }
    }

    @Test
    void experimentTrackerRecordsAndCompares() {
        ExperimentTracker tracker = new ExperimentTracker();
        ExperimentRecord record = tracker.record(
            "exp-1",
            List.of("https://example.com"),
            List.of(Map.of("seed", "https://example.com", "extract", Map.of("title", "Demo"), "duration_ms", 100.0)),
            Map.of("type", "object"),
            Map.of()
        );

        assertEquals("exp-001", record.id());
        assertEquals(1, tracker.getExperiments().size());
        assertTrue(tracker.getExperiment("exp-1").isPresent());
        assertEquals(1, tracker.toRows().size());
        assertEquals(1, ((Map<?, ?>) tracker.compare().get("summary")).get("total_experiments"));
    }
}
