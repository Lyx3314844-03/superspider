package distributed

import (
	"encoding/json"
	"bufio"
	"fmt"
	"net/http"
	"net"
	"os"
	"strconv"
	"strings"
)

type DiscoveredNode struct {
	Address string            `json:"address"`
	Source  string            `json:"source"`
	Meta    map[string]string `json:"meta,omitempty"`
}

func DiscoverNodesFromEnv(envVar string) []DiscoveredNode {
	raw := strings.TrimSpace(os.Getenv(envVar))
	if raw == "" {
		return nil
	}
	parts := strings.Split(raw, ",")
	nodes := make([]DiscoveredNode, 0, len(parts))
	for _, part := range parts {
		address := strings.TrimSpace(part)
		if address == "" {
			continue
		}
		nodes = append(nodes, DiscoveredNode{Address: address, Source: "env"})
	}
	return nodes
}

func DiscoverNodesFromFile(path string) ([]DiscoveredNode, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var nodes []DiscoveredNode
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		nodes = append(nodes, DiscoveredNode{Address: line, Source: "file"})
	}
	return nodes, scanner.Err()
}

func DiscoverNodesFromDNSSRV(service, proto, name string) ([]DiscoveredNode, error) {
	_, records, err := net.LookupSRV(service, proto, name)
	if err != nil {
		return nil, err
	}
	nodes := make([]DiscoveredNode, 0, len(records))
	for _, record := range records {
		target := strings.TrimSuffix(record.Target, ".")
		nodes = append(nodes, DiscoveredNode{
			Address: net.JoinHostPort(target, itoa(int(record.Port))),
			Source:  "dns-srv",
			Meta: map[string]string{
				"priority": itoa(int(record.Priority)),
				"weight":   itoa(int(record.Weight)),
			},
		})
	}
	return nodes, nil
}

func DiscoverNodesFromConsul(endpoint string) ([]DiscoveredNode, error) {
	resp, err := http.Get(strings.TrimRight(endpoint, "/"))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("consul discovery failed: %s", resp.Status)
	}
	var payload []map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return nil, err
	}
	nodes := make([]DiscoveredNode, 0, len(payload))
	for _, item := range payload {
		address := strings.TrimSpace(fmt.Sprint(item["Address"]))
		port := strings.TrimSpace(fmt.Sprint(item["ServicePort"]))
		if address == "" || port == "" || port == "<nil>" {
			continue
		}
		nodes = append(nodes, DiscoveredNode{
			Address: net.JoinHostPort(address, port),
			Source:  "consul",
		})
	}
	return nodes, nil
}

func DiscoverNodesFromEtcd(endpoint string) ([]DiscoveredNode, error) {
	resp, err := http.Get(strings.TrimRight(endpoint, "/"))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("etcd discovery failed: %s", resp.Status)
	}
	var payload map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return nil, err
	}
	node, _ := payload["node"].(map[string]interface{})
	rawNodes, _ := node["nodes"].([]interface{})
	discovered := make([]DiscoveredNode, 0, len(rawNodes))
	for _, raw := range rawNodes {
		child, _ := raw.(map[string]interface{})
		value := strings.TrimSpace(fmt.Sprint(child["value"]))
		if value == "" || value == "<nil>" {
			continue
		}
		discovered = append(discovered, DiscoveredNode{Address: value, Source: "etcd"})
	}
	return discovered, nil
}

func itoa(value int) string { return strconv.Itoa(value) }
