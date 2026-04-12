package com.javaspider.scrapy;

import com.javaspider.scrapy.item.Item;
import com.javaspider.scrapy.selector.Selector;

import java.net.URI;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public abstract class Spider {
    protected String name = "spider";
    protected final List<String> startUrls = new ArrayList<>();
    protected final Map<String, Object> startMeta = new LinkedHashMap<>();
    protected final Map<String, String> startHeaders = new LinkedHashMap<>();

    public String getName() {
        return name;
    }

    public Spider setName(String name) {
        this.name = name;
        return this;
    }

    public Spider addStartUrl(String url) {
        this.startUrls.add(url);
        return this;
    }

    public Spider startMeta(String key, Object value) {
        this.startMeta.put(key, value);
        return this;
    }

    public Spider startHeader(String key, String value) {
        this.startHeaders.put(key, value);
        return this;
    }

    public List<Request> startRequests() {
        List<Request> requests = new ArrayList<>();
        for (String url : startUrls) {
            requests.add(new Request(url, "GET", new LinkedHashMap<>(startHeaders), null, new LinkedHashMap<>(startMeta), this::parse));
        }
        return requests;
    }

    public abstract List<Object> parse(Response response);

    @FunctionalInterface
    public interface Callback {
        List<Object> handle(Response response);
    }

    @FunctionalInterface
    public interface ItemPipeline {
        Item processItem(Item item, Spider spider);
    }

    public static final class Request {
        private final String url;
        private final String method;
        private final Map<String, String> headers;
        private final String body;
        private final Map<String, Object> meta;
        private final Callback callback;

        public Request(String url, Callback callback) {
            this(url, "GET", new LinkedHashMap<>(), null, new LinkedHashMap<>(), callback);
        }

        public Request(String url, String method, Map<String, String> headers, String body, Map<String, Object> meta, Callback callback) {
            this.url = url;
            this.method = method == null || method.isBlank() ? "GET" : method;
            this.headers = headers == null ? new LinkedHashMap<>() : new LinkedHashMap<>(headers);
            this.body = body;
            this.meta = meta == null ? new LinkedHashMap<>() : new LinkedHashMap<>(meta);
            this.callback = callback;
        }

        public String getUrl() {
            return url;
        }

        public String getMethod() {
            return method;
        }

        public Map<String, String> getHeaders() {
            return new LinkedHashMap<>(headers);
        }

        public String getBody() {
            return body;
        }

        public Map<String, Object> getMeta() {
            return new LinkedHashMap<>(meta);
        }

        public Callback getCallback() {
            return callback;
        }

        public Request header(String key, String value) {
            Map<String, String> nextHeaders = new LinkedHashMap<>(headers);
            nextHeaders.put(key, value);
            return new Request(url, method, nextHeaders, body, meta, callback);
        }

        public Request meta(String key, Object value) {
            Map<String, Object> nextMeta = new LinkedHashMap<>(meta);
            nextMeta.put(key, value);
            return new Request(url, method, headers, body, nextMeta, callback);
        }
    }

    public static final class Response {
        private final String url;
        private final int statusCode;
        private final Map<String, String> headers;
        private final String body;
        private final Request request;

        public Response(String url, int statusCode, Map<String, String> headers, String body, Request request) {
            this.url = url;
            this.statusCode = statusCode;
            this.headers = headers == null ? new LinkedHashMap<>() : new LinkedHashMap<>(headers);
            this.body = body == null ? "" : body;
            this.request = request;
        }

        public String getUrl() {
            return url;
        }

        public int getStatusCode() {
            return statusCode;
        }

        public Map<String, String> getHeaders() {
            return new LinkedHashMap<>(headers);
        }

        public String getBody() {
            return body;
        }

        public Request getRequest() {
            return request;
        }

        public Selector selector() {
            return Selector.select(body);
        }

        public Request follow(String target, Callback callback) {
            String resolved = URI.create(url).resolve(target).toString();
            return new Request(resolved, callback);
        }
    }
}
