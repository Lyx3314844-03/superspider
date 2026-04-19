package com.javaspider.distributed;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import javax.naming.Context;
import javax.naming.NamingEnumeration;
import javax.naming.NamingException;
import javax.naming.directory.Attribute;
import javax.naming.directory.Attributes;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;
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
import java.util.Map;

/**
 * 分布式节点发现
 * 支持 env / file / dns-srv 三种来源，与 gospider 的能力面保持一致。
 */
public final class NodeDiscovery {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final HttpClient HTTP = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();

    private NodeDiscovery() {
    }

    public record DiscoveredNode(String address, String source, Map<String, String> meta) {
        public DiscoveredNode {
            meta = meta == null ? Map.of() : Map.copyOf(meta);
        }
    }

    public static List<DiscoveredNode> discoverFromEnv(String envVar) {
        return parseAddressList(System.getenv(envVar), "env");
    }

    public static List<DiscoveredNode> discoverFromFile(Path path) throws IOException {
        List<DiscoveredNode> nodes = new ArrayList<>();
        for (String line : Files.readAllLines(path)) {
            String trimmed = line.trim();
            if (trimmed.isEmpty() || trimmed.startsWith("#")) {
                continue;
            }
            nodes.add(new DiscoveredNode(trimmed, "file", Map.of()));
        }
        return nodes;
    }

    public static List<DiscoveredNode> discoverFromDnsSrv(String service, String protocol, String name) throws NamingException {
        Hashtable<String, String> env = new Hashtable<>();
        env.put(Context.INITIAL_CONTEXT_FACTORY, "com.sun.jndi.dns.DnsContextFactory");
        DirContext context = new InitialDirContext(env);
        try {
            String query = normalizeSrvQuery(service, protocol, name);
            Attributes attrs = context.getAttributes("dns:/" + query, new String[]{"SRV"});
            Attribute srv = attrs.get("SRV");
            if (srv == null) {
                return List.of();
            }
            List<String> records = new ArrayList<>();
            NamingEnumeration<?> values = srv.getAll();
            while (values.hasMore()) {
                records.add(String.valueOf(values.next()));
            }
            return discoverFromDnsSrvRecords(records);
        } finally {
            context.close();
        }
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

    static List<DiscoveredNode> parseAddressList(String raw, String source) {
        if (raw == null || raw.isBlank()) {
            return List.of();
        }
        List<DiscoveredNode> nodes = new ArrayList<>();
        for (String part : raw.split(",")) {
            String address = part.trim();
            if (!address.isEmpty()) {
                nodes.add(new DiscoveredNode(address, source, Map.of()));
            }
        }
        return nodes;
    }

    static List<DiscoveredNode> discoverFromDnsSrvRecords(Iterable<String> records) {
        List<DiscoveredNode> nodes = new ArrayList<>();
        for (String record : records) {
            if (record == null || record.isBlank()) {
                continue;
            }
            String[] parts = record.trim().split("\\s+");
            if (parts.length < 4) {
                continue;
            }
            String target = parts[3];
            if (target.endsWith(".")) {
                target = target.substring(0, target.length() - 1);
            }
            Map<String, String> meta = new LinkedHashMap<>();
            meta.put("priority", parts[0]);
            meta.put("weight", parts[1]);
            nodes.add(new DiscoveredNode(target + ":" + parts[2], "dns-srv", meta));
        }
        return nodes;
    }

    static String normalizeSrvQuery(String service, String protocol, String name) {
        String normalizedService = service == null ? "" : service.trim().replaceFirst("^_+", "");
        String normalizedProtocol = protocol == null ? "" : protocol.trim().replaceFirst("^_+", "");
        String normalizedName = name == null ? "" : name.trim().replaceFirst("\\.$", "");
        return "_" + normalizedService + "._" + normalizedProtocol + "." + normalizedName;
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
