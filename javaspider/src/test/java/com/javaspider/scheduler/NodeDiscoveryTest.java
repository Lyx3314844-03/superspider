package com.javaspider.scheduler;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

class NodeDiscoveryTest {

    @Test
    void discoversFromEnvAndFile() throws Exception {
        List<NodeDiscovery.DiscoveredNode> env = NodeDiscovery.discoverFromEnv("JAVASPIDER_CLUSTER_PEERS_MISSING");
        assertEquals(0, env.size());

        Path file = Files.createTempFile("java-nodes", ".txt");
        Files.writeString(file, "# comment\nnode-a:9000\n\nnode-b:9001\n", StandardCharsets.UTF_8);
        List<NodeDiscovery.DiscoveredNode> nodes = NodeDiscovery.discoverFromFile(file);
        assertEquals(2, nodes.size());
        assertEquals("file", nodes.get(0).source());
    }

    @Test
    void discoversFromConsulAndEtcd() throws Exception {
        try (StubServer consul = new StubServer("[{\"Address\":\"10.0.0.2\",\"ServicePort\":9000}]");
             StubServer etcd = new StubServer("{\"node\":{\"nodes\":[{\"value\":\"10.0.0.4:9100\"}]}}")) {
            List<NodeDiscovery.DiscoveredNode> consulNodes = NodeDiscovery.discoverFromConsul(consul.url());
            assertEquals(1, consulNodes.size());
            assertEquals("consul", consulNodes.get(0).source());

            List<NodeDiscovery.DiscoveredNode> etcdNodes = NodeDiscovery.discoverFromEtcd(etcd.url());
            assertEquals(1, etcdNodes.size());
            assertEquals("etcd", etcdNodes.get(0).source());
        }
    }

    private static final class StubServer implements AutoCloseable {
        private final HttpServer server;

        private StubServer(String body) throws IOException {
            server = HttpServer.create(new InetSocketAddress(0), 0);
            server.createContext("/", exchange -> {
                byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
                exchange.sendResponseHeaders(200, bytes.length);
                exchange.getResponseBody().write(bytes);
                exchange.close();
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
