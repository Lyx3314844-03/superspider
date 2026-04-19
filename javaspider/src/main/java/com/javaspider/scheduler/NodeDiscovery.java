package com.javaspider.scheduler;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import javax.naming.directory.InitialDirContext;
import javax.naming.directory.Attributes;
import javax.naming.directory.Attribute;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Hashtable;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public final class NodeDiscovery {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final HttpClient HTTP = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();

    private NodeDiscovery() {
    }

    public record DiscoveredNode(String address, String source, Map<String, String> meta) {}

    public static List<DiscoveredNode> discoverFromEnv(String envVar) {
        String raw = System.getenv(envVar);
        if (raw == null || raw.isBlank()) {
            return List.of();
        }
        List<DiscoveredNode> nodes = new ArrayList<>();
        for (String part : raw.split(",")) {
            String address = part.trim();
            if (!address.isBlank()) {
                nodes.add(new DiscoveredNode(address, "env", Map.of()));
            }
        }
        return nodes;
    }

    public static List<DiscoveredNode> discoverFromFile(Path path) throws IOException {
        List<DiscoveredNode> nodes = new ArrayList<>();
        for (String line : Files.readAllLines(path)) {
            String address = line.trim();
            if (!address.isBlank() && !address.startsWith("#")) {
                nodes.add(new DiscoveredNode(address, "file", Map.of()));
            }
        }
        return nodes;
    }

    public static List<DiscoveredNode> discoverFromDNSSrv(String service, String proto, String name) throws Exception {
        Hashtable<String, String> env = new Hashtable<>();
        env.put("java.naming.factory.initial", "com.sun.jndi.dns.DnsContextFactory");
        InitialDirContext context = new InitialDirContext(env);
        Attributes attributes = context.getAttributes("_" + service + "._" + proto + "." + name, new String[]{"SRV"});
        Attribute attribute = attributes.get("SRV");
        if (attribute == null) {
            return List.of();
        }
        List<DiscoveredNode> nodes = new ArrayList<>();
        for (int i = 0; i < attribute.size(); i++) {
            String[] parts = String.valueOf(attribute.get(i)).split(" ");
            if (parts.length >= 4) {
                String target = parts[3].replaceAll("\\.$", "");
                nodes.add(new DiscoveredNode(target + ":" + parts[2], "dns-srv", Map.of(
                    "priority", parts[0],
                    "weight", parts[1]
                )));
            }
        }
        return nodes;
    }

    public static List<DiscoveredNode> discoverFromConsul(String endpoint) throws IOException, InterruptedException {
        HttpResponse<String> response = HTTP.send(
            HttpRequest.newBuilder(URI.create(endpoint)).GET().timeout(Duration.ofSeconds(10)).build(),
            HttpResponse.BodyHandlers.ofString()
        );
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new IOException("consul discovery failed: " + response.statusCode());
        }
        List<Map<String, Object>> payload = MAPPER.readValue(response.body(), new TypeReference<List<Map<String, Object>>>() {});
        List<DiscoveredNode> nodes = new ArrayList<>();
        for (Map<String, Object> item : payload) {
            String address = String.valueOf(item.getOrDefault("Address", "")).trim();
            String port = String.valueOf(item.getOrDefault("ServicePort", "")).trim();
            if (!address.isBlank() && !port.isBlank() && !"null".equals(port)) {
                nodes.add(new DiscoveredNode(address + ":" + port, "consul", Map.of()));
            }
        }
        return nodes;
    }

    public static List<DiscoveredNode> discoverFromEtcd(String endpoint) throws IOException, InterruptedException {
        HttpResponse<String> response = HTTP.send(
            HttpRequest.newBuilder(URI.create(endpoint)).GET().timeout(Duration.ofSeconds(10)).build(),
            HttpResponse.BodyHandlers.ofString()
        );
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new IOException("etcd discovery failed: " + response.statusCode());
        }
        Map<String, Object> payload = MAPPER.readValue(response.body(), new TypeReference<Map<String, Object>>() {});
        Map<String, Object> node = mapValue(payload.get("node"));
        Object rawNodes = node.get("nodes");
        List<DiscoveredNode> discovered = new ArrayList<>();
        if (rawNodes instanceof List<?> list) {
            for (Object item : list) {
                Map<String, Object> child = mapValue(item);
                String value = String.valueOf(child.getOrDefault("value", "")).trim();
                if (!value.isBlank() && !"null".equalsIgnoreCase(value)) {
                    discovered.add(new DiscoveredNode(value, "etcd", Map.of()));
                }
            }
        }
        return discovered;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            Map<String, Object> result = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                result.put(String.valueOf(entry.getKey()), entry.getValue());
            }
            return result;
        }
        return Map.of();
    }
}
