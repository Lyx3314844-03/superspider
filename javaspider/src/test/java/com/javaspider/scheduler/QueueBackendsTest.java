package com.javaspider.scheduler;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.InputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;

class QueueBackendsTest {

    @Test
    void detectsBridgeKinds() {
        assertEquals(QueueBackends.Kind.RABBITMQ, QueueBackends.detect("rabbitmq://localhost:5672/amq.default?routing_key=spider-tasks"));
        assertEquals(QueueBackends.Kind.KAFKA, QueueBackends.detect("kafka://localhost:9092/spider-tasks"));
        assertEquals(QueueBackends.Kind.RABBITMQ, QueueBackends.detect("rabbitmq+http://localhost:15672/api/exchanges/%2F/amq.default/publish"));
        assertEquals(QueueBackends.Kind.KAFKA, QueueBackends.detect("kafka+http://localhost:8082/topics/spider-tasks"));
    }

    @Test
    void publishesRabbitMqBridgePayload() throws Exception {
        AtomicReference<String> bodyRef = new AtomicReference<>("");
        try (StubServer server = new StubServer(bodyRef)) {
            QueueBackends.QueueBridgeClient client = new QueueBackends.QueueBridgeClient(
                new QueueBackends.Config(QueueBackends.Kind.RABBITMQ, "rabbitmq+" + server.url() + "/api/exchanges/%2F/amq.default/publish")
            );
            client.publishJson(Map.of("job", "demo"));
            assertTrue(bodyRef.get().contains("\"payload\""));
        }
    }

    @Test
    void supportPayloadIncludesBridgedBackends() {
        Map<String, Object> support = QueueBackends.support();
        @SuppressWarnings("unchecked")
        Map<String, Object> nativeProcess = (Map<String, Object>) support.get("native_process");
        @SuppressWarnings("unchecked")
        Map<String, Object> bridged = (Map<String, Object>) support.get("bridged");
        assertTrue(nativeProcess.containsKey("rabbitmq"));
        assertTrue(nativeProcess.containsKey("kafka"));
        assertTrue(bridged.containsKey("rabbitmq"));
        assertTrue(bridged.containsKey("kafka"));
    }

    @Test
    void buildsNativeRabbitMqAndKafkaCommands() {
        QueueBackends.NativeQueueClient rabbit = new QueueBackends.NativeQueueClient(
            new QueueBackends.Config(
                QueueBackends.Kind.RABBITMQ,
                "rabbitmq://localhost:5672/amq.default?routing_key=spider-tasks",
                "spider-tasks",
                "",
                Map.of(),
                "guest",
                "guest"
            )
        );
        QueueBackends.CommandSpec rabbitSpec = rabbit.buildPublishCommands(Map.of("job", "demo")).get(0);
        assertEquals("amqp-publish", rabbitSpec.program());
        assertTrue(rabbitSpec.args().contains("--routing-key"));

        QueueBackends.NativeQueueClient kafka = new QueueBackends.NativeQueueClient(
            new QueueBackends.Config(
                QueueBackends.Kind.KAFKA,
                "kafka://localhost:9092/spider-tasks",
                "",
                "spider-tasks",
                Map.of(),
                "",
                ""
            )
        );
        QueueBackends.CommandSpec kafkaSpec = kafka.buildPublishCommands(Map.of("job", "demo")).get(0);
        assertEquals("kcat", kafkaSpec.program());
        assertEquals("{\"job\":\"demo\"}", kafkaSpec.stdin());
    }

    @Test
    void buildsNativeDriverRabbitMqAndKafkaPublishRequests() throws Exception {
        QueueBackends.NativeDriverQueueClient rabbit = new QueueBackends.NativeDriverQueueClient(
            new QueueBackends.Config(
                QueueBackends.Kind.RABBITMQ,
                "rabbitmq://localhost:5672/amq.default?routing_key=spider-tasks",
                "spider-tasks",
                "",
                Map.of(),
                "guest",
                "guest"
            )
        );
        AtomicReference<QueueBackends.RabbitPublishRequest> rabbitRef = new AtomicReference<>();
        rabbit.publishRabbitJson(Map.of("job", "demo"), rabbitRef::set);
        assertEquals("amq.default", rabbitRef.get().exchange());
        assertEquals("spider-tasks", rabbitRef.get().routingKey());
        assertEquals("application/json", rabbitRef.get().contentType());

        QueueBackends.NativeDriverQueueClient kafka = new QueueBackends.NativeDriverQueueClient(
            new QueueBackends.Config(
                QueueBackends.Kind.KAFKA,
                "kafka://localhost:9092/spider-tasks",
                "",
                "spider-tasks",
                Map.of(),
                "",
                ""
            )
        );
        AtomicReference<QueueBackends.KafkaPublishRequest> kafkaRef = new AtomicReference<>();
        kafka.publishKafkaJson(Map.of("job", "demo"), kafkaRef::set);
        assertEquals("spider-tasks", kafkaRef.get().topic());
        assertEquals("{\"job\":\"demo\"}", kafkaRef.get().value());
        assertEquals("localhost:9092", kafkaRef.get().properties().getProperty("bootstrap.servers"));
    }

    private static final class StubServer implements AutoCloseable {
        private final HttpServer server;

        private StubServer(AtomicReference<String> bodyRef) throws IOException {
            server = HttpServer.create(new InetSocketAddress(0), 0);
            server.createContext("/", exchange -> {
                try (InputStream input = exchange.getRequestBody()) {
                    bodyRef.set(new String(input.readAllBytes(), StandardCharsets.UTF_8));
                }
                exchange.sendResponseHeaders(200, 0);
                exchange.getResponseBody().close();
            });
            server.start();
        }

        private String url() {
            return "http://127.0.0.1:" + server.getAddress().getPort();
        }

        @Override
        public void close() {
            server.stop(0);
        }
    }
}
