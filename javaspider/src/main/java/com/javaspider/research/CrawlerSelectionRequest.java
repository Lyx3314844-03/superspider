package com.javaspider.research;

public class CrawlerSelectionRequest {
    private final String url;
    private final String content;
    private final String scenarioHint;

    public CrawlerSelectionRequest(String url) {
        this(url, "", "");
    }

    public CrawlerSelectionRequest(String url, String content) {
        this(url, content, "");
    }

    public CrawlerSelectionRequest(String url, String content, String scenarioHint) {
        this.url = url == null ? "" : url;
        this.content = content == null ? "" : content;
        this.scenarioHint = scenarioHint == null ? "" : scenarioHint;
    }

    public String getUrl() {
        return url;
    }

    public String getContent() {
        return content;
    }

    public String getScenarioHint() {
        return scenarioHint;
    }
}
