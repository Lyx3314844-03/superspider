package com.javaspider.core;

import com.fasterxml.jackson.databind.JsonNode;
import com.javaspider.selector.Html;
import com.javaspider.selector.Selectable;

import lombok.Data;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Page - 页面对象
 */
@Data
public class Page {

    private Request request;
    private ResultItems resultItems = new ResultItems();
    private String rawText;
    private Html html;
    private byte[] bytes;
    private String url;
    private Map<String, String> headers;
    private int statusCode;
    private long downloadTime;
    private boolean skip;
    private List<Request> targetRequests = new ArrayList<>();
    private int depth;
    private long downloadDuration;
    private Map<String, Object> fields = new HashMap<>();
    private JsonNode json;
    private String error;

    public Html getHtml() {
        if (html == null && rawText != null) {
            html = new Html(rawText, url);
        }
        return html;
    }

    public void putField(String key, Object value) {
        fields.put(key, value);
    }

    public Object getField(String key) {
        return fields.get(key);
    }

    public Map<String, Object> getFields() {
        return fields;
    }

    public void setError(String error) {
        this.error = error;
    }

    public String getError() {
        return error;
    }

    public void setJson(JsonNode json) {
        this.json = json;
    }

    public JsonNode getJson() {
        return json;
    }

    public String $(String cssSelector) {
        return getHtml().$(cssSelector).get();
    }
    
    public List<String> $$(String cssSelector) {
        List<Selectable> selectables = getHtml().$$(cssSelector);
        List<String> result = new ArrayList<>();
        for (Selectable s : selectables) {
            if (s.get() != null) {
                result.add(s.get());
            }
        }
        return result;
    }
    
    public String xpath(String xpath) {
        return getHtml().xpath(xpath).get();
    }
    
    public List<String> xpathAll(String xpath) {
        return getHtml().xpath(xpath).all();
    }
    
    public String regex(String regex) {
        return getHtml().regex(regex).get();
    }
    
    public List<String> regexAll(String regex) {
        Selectable selectable = getHtml().regex(regex);
        List<String> result = new ArrayList<>();
        if (selectable.get() != null) {
            result.add(selectable.get());
        }
        return result;
    }
    
    public void addTargetRequest(Request request) {
        targetRequests.add(request);
    }
    
    public void addTargetRequest(String url) {
        if (url != null && !url.isEmpty()) {
            targetRequests.add(new Request(url));
        }
    }
    
    public void addTargetRequests(List<String> urls) {
        for (String url : urls) {
            addTargetRequest(url);
        }
    }
    
    public void setSkip(boolean skip) {
        this.skip = skip;
    }
}
