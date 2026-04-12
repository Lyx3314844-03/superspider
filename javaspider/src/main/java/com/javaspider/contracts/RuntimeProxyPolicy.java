package com.javaspider.contracts;

import java.util.LinkedHashMap;
import java.util.Map;

public final class RuntimeProxyPolicy {
    private RuntimeProxyPolicy() {
    }

    public static final class ProxyEndpoint {
        private final String proxyId;
        private final String url;
        private int successCount;
        private int failureCount;
        private boolean available = true;
        private String lastError = "";

        public ProxyEndpoint(String proxyId, String url) {
            this.proxyId = proxyId;
            this.url = url;
        }

        public String getProxyId() {
            return proxyId;
        }

        public String getUrl() {
            return url;
        }

        public double score() {
            int total = successCount + failureCount;
            return total == 0 ? 1.0d : (double) successCount / total;
        }
    }

    public static final class ProxyPolicy {
        private final Map<String, ProxyEndpoint> proxies = new LinkedHashMap<>();

        public synchronized ProxyEndpoint addProxy(String proxyId, String url) {
            ProxyEndpoint endpoint = new ProxyEndpoint(proxyId, url);
            proxies.put(proxyId, endpoint);
            return endpoint;
        }

        public synchronized ProxyEndpoint choose() {
            return proxies.values().stream()
                .filter(endpoint -> endpoint.available)
                .max((left, right) -> Double.compare(left.score(), right.score()))
                .orElse(null);
        }

        public synchronized void record(String proxyId, boolean success, String error) {
            ProxyEndpoint endpoint = proxies.get(proxyId);
            if (endpoint == null) {
                return;
            }
            if (success) {
                endpoint.successCount += 1;
                endpoint.available = true;
                endpoint.lastError = "";
            } else {
                endpoint.failureCount += 1;
                endpoint.lastError = error == null ? "" : error;
                if (endpoint.failureCount >= 3 && endpoint.failureCount > endpoint.successCount) {
                    endpoint.available = false;
                }
            }
        }
    }
}
