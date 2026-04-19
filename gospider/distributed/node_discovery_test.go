package distributed

import (
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

func TestDiscoverNodesFromEnvParsesCommaSeparatedAddresses(t *testing.T) {
	t.Setenv("GOSPIDER_CLUSTER_PEERS", "node-a:9000, node-b:9001")

	nodes := DiscoverNodesFromEnv("GOSPIDER_CLUSTER_PEERS")
	if len(nodes) != 2 {
		t.Fatalf("unexpected node count: %d", len(nodes))
	}
	if nodes[0].Address != "node-a:9000" || nodes[1].Address != "node-b:9001" {
		t.Fatalf("unexpected nodes: %#v", nodes)
	}
}

func TestDiscoverNodesFromFileIgnoresCommentsAndBlankLines(t *testing.T) {
	path := filepath.Join(t.TempDir(), "nodes.txt")
	if err := os.WriteFile(path, []byte("# comment\nnode-a:9000\n\nnode-b:9001\n"), 0o644); err != nil {
		t.Fatalf("failed to write fixture: %v", err)
	}

	nodes, err := DiscoverNodesFromFile(path)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(nodes) != 2 {
		t.Fatalf("unexpected node count: %d", len(nodes))
	}
}

func TestDiscoverNodesFromConsulAndEtcd(t *testing.T) {
	consul := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`[{"Address":"10.0.0.2","ServicePort":9000},{"Address":"10.0.0.3","ServicePort":9001}]`))
	}))
	defer consul.Close()

	consulNodes, err := DiscoverNodesFromConsul(consul.URL)
	if err != nil {
		t.Fatalf("expected consul discovery to succeed: %v", err)
	}
	if len(consulNodes) != 2 || consulNodes[0].Source != "consul" {
		t.Fatalf("unexpected consul nodes: %#v", consulNodes)
	}

	etcd := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"node":{"nodes":[{"value":"10.0.0.4:9100"},{"value":"10.0.0.5:9101"}]}}`))
	}))
	defer etcd.Close()

	etcdNodes, err := DiscoverNodesFromEtcd(etcd.URL)
	if err != nil {
		t.Fatalf("expected etcd discovery to succeed: %v", err)
	}
	if len(etcdNodes) != 2 || etcdNodes[0].Source != "etcd" {
		t.Fatalf("unexpected etcd nodes: %#v", etcdNodes)
	}
}
