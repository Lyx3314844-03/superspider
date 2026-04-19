package com.javaspider.distributed;

import org.junit.jupiter.api.Test;

import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;

class NodeDiscoveryTest {

    @Test
    void parsesCommaSeparatedAddressLists() {
        List<NodeDiscovery.DiscoveredNode> nodes =
            NodeDiscovery.parseAddressList("node-a:9000, node-b:9001", "env");

        assertEquals(2, nodes.size());
        assertEquals("node-a:9000", nodes.get(0).address());
        assertEquals("env", nodes.get(0).source());
    }

    @Test
    void discoversNodesFromFileIgnoringComments() throws Exception {
        Path file = Files.createTempFile("java-nodes", ".txt");
        Files.writeString(file, "# comment\nnode-a:9000\n\nnode-b:9001\n");

        List<NodeDiscovery.DiscoveredNode> nodes = NodeDiscovery.discoverFromFile(file);

        assertEquals(2, nodes.size());
        assertEquals("file", nodes.get(1).source());
    }

    @Test
    void parsesDnsSrvRecordsIntoAddressesAndMetadata() {
        List<NodeDiscovery.DiscoveredNode> nodes = NodeDiscovery.discoverFromDnsSrvRecords(List.of(
            "10 5 8080 crawler-a.internal.",
            "20 10 9090 crawler-b.internal."
        ));

        assertEquals(2, nodes.size());
        assertEquals("crawler-a.internal:8080", nodes.get(0).address());
        assertEquals("10", nodes.get(0).meta().get("priority"));
        assertEquals("5", nodes.get(0).meta().get("weight"));
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
