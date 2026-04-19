package com.javaspider.scheduler;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.Producer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;

import java.io.IOException;
import java.net.URI;
import java.net.URLDecoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;

public final class QueueBackends {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private QueueBackends() {
    }

    public enum Kind {
        MEMORY,
        FILE_JSON,
        REDIS,
        RABBITMQ,
        KAFKA
    }

    public record Config(
        Kind kind,
        String endpoint,
        String routingKey,
        String topic,
        Map<String, String> headers,
        String username,
        String password
    ) {
        public Config(Kind kind, String endpoint) {
            this(kind, endpoint, "", "", new LinkedHashMap<>(), "", "");
        }
    }

    public static Kind detect(String endpoint) {
        String lower = endpoint == null ? "" : endpoint.trim().toLowerCase();
        if (lower.startsWith("memory://")) return Kind.MEMORY;
        if (lower.startsWith("file://")) return Kind.FILE_JSON;
        if (lower.startsWith("redis://")) return Kind.REDIS;
        if (lower.startsWith("rabbitmq://")) return Kind.RABBITMQ;
        if (lower.startsWith("kafka://")) return Kind.KAFKA;
        if (lower.startsWith("rabbitmq+http://") || lower.startsWith("rabbitmq+https://") || lower.contains("/api/exchanges/")) return Kind.RABBITMQ;
        if (lower.startsWith("kafka+http://") || lower.startsWith("kafka+https://") || lower.contains("/topics/")) return Kind.KAFKA;
        throw new IllegalArgumentException("Unsupported queue backend endpoint: " + endpoint);
    }

    public static Map<String, Object> support() {
        return Map.of(
            "native", java.util.List.of("memory", "file-json", "redis", "rabbitmq", "kafka"),
            "native_driver", Map.of(
                "rabbitmq", Map.of("mode", "broker-sdk", "adapter_engine", "amqp-client"),
                "kafka", Map.of("mode", "broker-sdk", "adapter_engine", "kafka-clients")
            ),
            "native_process", Map.of(
                "rabbitmq", Map.of("mode", "cli-adapter", "commands", java.util.List.of("amqp-publish", "rabbitmqadmin")),
                "kafka", Map.of("mode", "cli-adapter", "commands", java.util.List.of("kcat", "kafka-console-producer"))
            ),
            "bridged", Map.of(
                "rabbitmq", Map.of("mode", "http-management-bridge", "adapter_engine", "rabbitmq-management-api"),
                "kafka", Map.of("mode", "rest-proxy-bridge", "adapter_engine", "kafka-rest-proxy")
            )
        );
    }

    public record CommandSpec(String program, List<String> args, String stdin) {
    }

    public record RabbitPublishRequest(String exchange, String routingKey, byte[] body, String contentType, int deliveryMode) {
    }

    public record KafkaPublishRequest(String topic, String key, String value, Properties properties) {
    }

    @FunctionalInterface
    interface RabbitPublisher {
        void publish(RabbitPublishRequest request) throws Exception;
    }

    @FunctionalInterface
    interface KafkaPublisher {
        void publish(KafkaPublishRequest request) throws Exception;
    }

    public static final class QueueBridgeClient {
        private final HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build();
        private final Config config;

        public QueueBridgeClient(Config config) {
            this.config = config;
        }

        public void publishJson(Map<String, Object> payload) {
            try {
                String endpoint = normalize(config.endpoint());
                Map<String, Object> body = switch (config.kind()) {
                    case RABBITMQ -> Map.of(
                        "properties", Map.of(),
                        "routing_key", config.routingKey(),
                        "payload", MAPPER.writeValueAsString(payload),
                        "payload_encoding", "string"
                    );
                    case KAFKA -> Map.of(
                        "records", java.util.List.of(Map.of("value", payload))
                    );
                    default -> throw new IllegalArgumentException("Queue bridge client only supports RabbitMQ/Kafka");
                };
                HttpRequest.Builder builder = HttpRequest.newBuilder()
                    .uri(URI.create(endpoint))
                    .timeout(Duration.ofSeconds(30))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(MAPPER.writeValueAsString(body)));
                for (Map.Entry<String, String> entry : config.headers().entrySet()) {
                    builder.header(entry.getKey(), entry.getValue());
                }
                if (!config.username().isBlank() || !config.password().isBlank()) {
                    String basic = java.util.Base64.getEncoder().encodeToString((config.username() + ":" + config.password()).getBytes(java.nio.charset.StandardCharsets.UTF_8));
                    builder.header("Authorization", "Basic " + basic);
                }
                HttpResponse<String> response = client.send(builder.build(), HttpResponse.BodyHandlers.ofString());
                if (response.statusCode() < 200 || response.statusCode() >= 300) {
                    throw new IllegalStateException("Queue publish failed: " + response.statusCode());
                }
            } catch (IOException | InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new RuntimeException("Queue publish failed", e);
            }
        }

        private String normalize(String endpoint) {
            if (endpoint.startsWith("rabbitmq+http://")) return "http://" + endpoint.substring("rabbitmq+http://".length());
            if (endpoint.startsWith("rabbitmq+https://")) return "https://" + endpoint.substring("rabbitmq+https://".length());
            if (endpoint.startsWith("kafka+http://")) return "http://" + endpoint.substring("kafka+http://".length());
            if (endpoint.startsWith("kafka+https://")) return "https://" + endpoint.substring("kafka+https://".length());
            return endpoint;
        }
    }

    public static final class NativeQueueClient {
        private final Config config;

        public NativeQueueClient(Config config) {
            this.config = config;
        }

        public List<CommandSpec> buildPublishCommands(Map<String, Object> payload) {
            return switch (config.kind()) {
                case RABBITMQ -> buildRabbitMqCommands(payload);
                case KAFKA -> buildKafkaCommands(payload);
                default -> throw new IllegalArgumentException("Native queue client only supports RabbitMQ/Kafka");
            };
        }

        public void publishJson(Map<String, Object> payload) {
            IOException lastIo = null;
            InterruptedException lastInterrupted = null;
            for (CommandSpec spec : buildPublishCommands(payload)) {
                List<String> command = new ArrayList<>();
                command.add(spec.program());
                command.addAll(spec.args());
                ProcessBuilder builder = new ProcessBuilder(command);
                try {
                    Process process = builder.start();
                    if (spec.stdin() != null && !spec.stdin().isBlank()) {
                        process.getOutputStream().write(spec.stdin().getBytes(StandardCharsets.UTF_8));
                    }
                    process.getOutputStream().close();
                    int exit = process.waitFor();
                    if (exit == 0) {
                        return;
                    }
                } catch (IOException e) {
                    lastIo = e;
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    lastInterrupted = e;
                    break;
                }
            }
            if (lastInterrupted != null) {
                throw new RuntimeException("Native queue publish interrupted", lastInterrupted);
            }
            throw new RuntimeException("No native queue command succeeded", lastIo);
        }

        private List<CommandSpec> buildRabbitMqCommands(Map<String, Object> payload) {
            URI uri = URI.create(config.endpoint());
            String host = uri.getHost() == null ? "localhost" : uri.getHost();
            int port = uri.getPort() == -1 ? 5672 : uri.getPort();
            Map<String, String> query = parseQuery(uri.getRawQuery());
            List<String> segments = pathSegments(uri.getPath());
            String vhost = decode(query.getOrDefault("vhost", segments.isEmpty() ? "/" : segments.get(0)));
            String exchange = decode(query.getOrDefault("exchange", segments.size() > 1 ? segments.get(1) : "amq.default"));
            String routingKey = !config.routingKey().isBlank()
                ? config.routingKey()
                : decode(query.getOrDefault("routing_key", ""));
            String body = toJson(payload);
            String amqpUrl = "amqp://" + host + ":" + port + "/" + encodePathVhost(vhost);

            return List.of(
                new CommandSpec(
                    "amqp-publish",
                    List.of("--url", amqpUrl, "--exchange", exchange, "--routing-key", routingKey, "--body", body),
                    ""
                ),
                new CommandSpec(
                    "rabbitmqadmin",
                    List.of(
                        "--host", host,
                        "--port", String.valueOf(port),
                        "--username", blankToDefault(config.username(), "guest"),
                        "--password", blankToDefault(config.password(), "guest"),
                        "--vhost", vhost,
                        "publish",
                        "exchange=" + exchange,
                        "routing_key=" + routingKey,
                        "payload=" + body
                    ),
                    ""
                )
            );
        }

        private List<CommandSpec> buildKafkaCommands(Map<String, Object> payload) {
            URI uri = URI.create(config.endpoint());
            String hostPort = uri.getHost() == null
                ? "localhost:9092"
                : uri.getHost() + ":" + (uri.getPort() == -1 ? 9092 : uri.getPort());
            List<String> segments = pathSegments(uri.getPath());
            String topic = !config.topic().isBlank()
                ? config.topic()
                : (segments.isEmpty() ? "spider-tasks" : decode(segments.get(0)));
            String body = toJson(payload);
            return List.of(
                new CommandSpec("kcat", List.of("-b", hostPort, "-t", topic, "-P"), body),
                new CommandSpec("kafka-console-producer", List.of("--bootstrap-server", hostPort, "--topic", topic), body)
            );
        }

        private List<String> pathSegments(String path) {
            if (path == null || path.isBlank() || "/".equals(path)) {
                return List.of();
            }
            List<String> segments = new ArrayList<>();
            for (String part : path.split("/")) {
                if (!part.isBlank()) {
                    segments.add(part);
                }
            }
            return segments;
        }

        private Map<String, String> parseQuery(String rawQuery) {
            Map<String, String> query = new LinkedHashMap<>();
            if (rawQuery == null || rawQuery.isBlank()) {
                return query;
            }
            for (String pair : rawQuery.split("&")) {
                String[] parts = pair.split("=", 2);
                String key = decode(parts[0]);
                String value = parts.length > 1 ? decode(parts[1]) : "";
                query.put(key, value);
            }
            return query;
        }

        private String toJson(Map<String, Object> payload) {
            try {
                return MAPPER.writeValueAsString(payload);
            } catch (JsonProcessingException e) {
                throw new RuntimeException("Failed to serialize payload", e);
            }
        }

        private String decode(String value) {
            return URLDecoder.decode(value == null ? "" : value, StandardCharsets.UTF_8);
        }

        private String encodePathVhost(String value) {
            if (value == null || value.isBlank() || "/".equals(value)) {
                return "%2F";
            }
            return value.replace("/", "%2F");
        }

        private String blankToDefault(String value, String fallback) {
            return value == null || value.isBlank() ? fallback : value;
        }
    }

    public static final class NativeDriverQueueClient {
        private final Config config;

        public NativeDriverQueueClient(Config config) {
            this.config = config;
        }

        public void publishJson(Map<String, Object> payload) {
            try {
                switch (config.kind()) {
                    case RABBITMQ -> publishRabbitJson(payload, this::publishRabbitViaDriver);
                    case KAFKA -> publishKafkaJson(payload, this::publishKafkaViaDriver);
                    default -> throw new IllegalArgumentException("Native driver queue client only supports RabbitMQ/Kafka");
                }
            } catch (Exception e) {
                throw new RuntimeException("Native driver queue publish failed", e);
            }
        }

        void publishRabbitJson(Map<String, Object> payload, RabbitPublisher publisher) throws Exception {
            publisher.publish(buildRabbitPublishRequest(payload));
        }

        void publishKafkaJson(Map<String, Object> payload, KafkaPublisher publisher) throws Exception {
            publisher.publish(buildKafkaPublishRequest(payload));
        }

        RabbitPublishRequest buildRabbitPublishRequest(Map<String, Object> payload) {
            URI uri = URI.create(config.endpoint());
            Map<String, String> query = parseQuery(uri.getRawQuery());
            List<String> segments = pathSegments(uri.getPath());
            String vhost = decode(query.getOrDefault("vhost", "/"));
            String exchange = decode(query.getOrDefault("exchange", segments.isEmpty() ? "amq.default" : segments.get(segments.size() - 1)));
            String routingKey = !config.routingKey().isBlank()
                ? config.routingKey()
                : decode(query.getOrDefault("routing_key", ""));
            String body = toJson(payload);
            return new RabbitPublishRequest(exchange, routingKey, body.getBytes(StandardCharsets.UTF_8), "application/json", 2);
        }

        KafkaPublishRequest buildKafkaPublishRequest(Map<String, Object> payload) {
            URI uri = URI.create(config.endpoint());
            List<String> segments = pathSegments(uri.getPath());
            String topic = !config.topic().isBlank()
                ? config.topic()
                : (segments.isEmpty() ? "spider-tasks" : decode(segments.get(0)));
            Properties properties = new Properties();
            properties.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG,
                (uri.getHost() == null ? "localhost" : uri.getHost()) + ":" + (uri.getPort() == -1 ? 9092 : uri.getPort()));
            properties.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
            properties.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
            properties.put(ProducerConfig.ACKS_CONFIG, "all");
            return new KafkaPublishRequest(topic, null, toJson(payload), properties);
        }

        private void publishRabbitViaDriver(RabbitPublishRequest request) throws Exception {
            ConnectionFactory factory = new ConnectionFactory();
            factory.setUri(normalizeAmqpEndpoint(config.endpoint()));
            try (Connection connection = factory.newConnection(); Channel channel = connection.createChannel()) {
                AMQP.BasicProperties props = new AMQP.BasicProperties.Builder()
                    .contentType(request.contentType())
                    .deliveryMode(request.deliveryMode())
                    .build();
                channel.basicPublish(request.exchange(), request.routingKey(), props, request.body());
            }
        }

        private void publishKafkaViaDriver(KafkaPublishRequest request) throws Exception {
            try (Producer<String, String> producer = new KafkaProducer<>(request.properties())) {
                producer.send(new ProducerRecord<>(request.topic(), request.key(), request.value())).get();
                producer.flush();
            }
        }

        private String toJson(Map<String, Object> payload) {
            try {
                return MAPPER.writeValueAsString(payload);
            } catch (JsonProcessingException e) {
                throw new RuntimeException("Failed to serialize payload", e);
            }
        }

        private String normalizeAmqpEndpoint(String endpoint) {
            if (endpoint.startsWith("rabbitmq://")) {
                return "amqp://" + endpoint.substring("rabbitmq://".length());
            }
            return endpoint;
        }
    }

    private static List<String> pathSegments(String path) {
        if (path == null || path.isBlank() || "/".equals(path)) {
            return List.of();
        }
        List<String> segments = new ArrayList<>();
        for (String part : path.split("/")) {
            if (!part.isBlank()) {
                segments.add(part);
            }
        }
        return segments;
    }

    private static Map<String, String> parseQuery(String rawQuery) {
        Map<String, String> query = new LinkedHashMap<>();
        if (rawQuery == null || rawQuery.isBlank()) {
            return query;
        }
        for (String pair : rawQuery.split("&")) {
            String[] parts = pair.split("=", 2);
            String key = decode(parts[0]);
            String value = parts.length > 1 ? decode(parts[1]) : "";
            query.put(key, value);
        }
        return query;
    }

    private static String decode(String value) {
        return URLDecoder.decode(value == null ? "" : value, StandardCharsets.UTF_8);
    }
}
