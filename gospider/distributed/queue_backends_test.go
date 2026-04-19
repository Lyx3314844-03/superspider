package distributed

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestDetectQueueBackendKindSupportsBridgeEndpoints(t *testing.T) {
	rabbitNative, ok := DetectQueueBackendKind("rabbitmq://localhost:5672/amq.default?routing_key=spider.jobs")
	if !ok || rabbitNative != QueueBackendRabbitMQ {
		t.Fatalf("expected rabbitmq native detection, got %q ok=%v", rabbitNative, ok)
	}

	kafkaNative, ok := DetectQueueBackendKind("kafka://localhost:9092/spider-tasks")
	if !ok || kafkaNative != QueueBackendKafka {
		t.Fatalf("expected kafka native detection, got %q ok=%v", kafkaNative, ok)
	}

	rabbitKind, ok := DetectQueueBackendKind("rabbitmq+http://localhost:15672/api/exchanges/%2F/amq.default/publish")
	if !ok || rabbitKind != QueueBackendRabbitMQ {
		t.Fatalf("expected rabbitmq bridge detection, got %q ok=%v", rabbitKind, ok)
	}

	kafkaKind, ok := DetectQueueBackendKind("kafka+http://localhost:8082/topics/spider-tasks")
	if !ok || kafkaKind != QueueBackendKafka {
		t.Fatalf("expected kafka bridge detection, got %q ok=%v", kafkaKind, ok)
	}
}

func TestQueueBridgeClientPublishesRabbitMQPayload(t *testing.T) {
	var requestPath string
	var payload map[string]any
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestPath = r.URL.EscapedPath()
		body, err := io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed to read request body: %v", err)
		}
		if err := json.Unmarshal(body, &payload); err != nil {
			t.Fatalf("failed to decode request body: %v", err)
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{}`))
	}))
	defer server.Close()

	config := NewQueueBackendConfig(QueueBackendRabbitMQ, "rabbitmq+"+server.URL+"/api/exchanges/%2F/amq.default/publish")
	config.RoutingKey = "spider.jobs"
	client, err := NewQueueBridgeClient(config)
	if err != nil {
		t.Fatalf("expected bridge client to build: %v", err)
	}
	if err := client.PublishJSON(map[string]any{"job": "demo"}); err != nil {
		t.Fatalf("expected rabbitmq publish to succeed: %v", err)
	}

	if requestPath != "/api/exchanges/%2F/amq.default/publish" {
		t.Fatalf("unexpected request path: %s", requestPath)
	}
	if payload["routing_key"] != "spider.jobs" {
		t.Fatalf("unexpected routing key payload: %#v", payload)
	}
	if payload["payload_encoding"] != "string" {
		t.Fatalf("unexpected payload encoding: %#v", payload)
	}
}

func TestQueueBridgeClientPublishesKafkaPayload(t *testing.T) {
	var requestPath string
	var payload map[string]any
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestPath = r.URL.EscapedPath()
		body, err := io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed to read request body: %v", err)
		}
		if err := json.Unmarshal(body, &payload); err != nil {
			t.Fatalf("failed to decode request body: %v", err)
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{}`))
	}))
	defer server.Close()

	config := NewQueueBackendConfig(QueueBackendKafka, "kafka+"+server.URL+"/topics/spider-tasks")
	client, err := NewQueueBridgeClient(config)
	if err != nil {
		t.Fatalf("expected bridge client to build: %v", err)
	}
	if err := client.PublishJSON(map[string]any{"job": "demo"}); err != nil {
		t.Fatalf("expected kafka publish to succeed: %v", err)
	}

	if requestPath != "/topics/spider-tasks" {
		t.Fatalf("unexpected request path: %s", requestPath)
	}
	records, ok := payload["records"].([]any)
	if !ok || len(records) != 1 {
		t.Fatalf("unexpected kafka records payload: %#v", payload)
	}
	support := QueueBackendSupport()
	nativeProcess, ok := support["native_process"].(map[string]any)
	if !ok {
		t.Fatalf("expected native_process support map: %#v", support)
	}
	if _, ok := nativeProcess[string(QueueBackendRabbitMQ)]; !ok {
		t.Fatalf("expected native rabbitmq support payload: %#v", support)
	}
	if _, ok := nativeProcess[string(QueueBackendKafka)]; !ok {
		t.Fatalf("expected native kafka support payload: %#v", support)
	}
	bridged, ok := support["bridged"].(map[string]any)
	if !ok {
		t.Fatalf("expected bridged support map: %#v", support)
	}
	rabbit, ok := bridged[string(QueueBackendRabbitMQ)].(map[string]any)
	if !ok || rabbit["adapter_engine"] != "rabbitmq-management-api" {
		t.Fatalf("unexpected rabbitmq support payload: %#v", support)
	}
	kafka, ok := bridged[string(QueueBackendKafka)].(map[string]any)
	if !ok || kafka["adapter_engine"] != "kafka-rest-proxy" {
		t.Fatalf("unexpected kafka support payload: %#v", support)
	}
}

func TestNativeQueueClientBuildsRabbitMQAndKafkaCommands(t *testing.T) {
	rabbit := NewNativeQueueClient(QueueBackendConfig{
		Kind:       QueueBackendRabbitMQ,
		Endpoint:   "rabbitmq://localhost:5672/amq.default?routing_key=spider.jobs",
		RoutingKey: "spider.jobs",
		Username:   "guest",
		Password:   "guest",
	})
	rabbitCommands, err := rabbit.BuildPublishCommands(map[string]any{"job": "demo"})
	if err != nil {
		t.Fatalf("expected native rabbitmq commands: %v", err)
	}
	if rabbitCommands[0].Program != "amqp-publish" {
		t.Fatalf("unexpected rabbitmq native program: %#v", rabbitCommands[0])
	}

	kafka := NewNativeQueueClient(QueueBackendConfig{
		Kind:     QueueBackendKafka,
		Endpoint: "kafka://localhost:9092/spider-tasks",
		Topic:    "spider-tasks",
	})
	kafkaCommands, err := kafka.BuildPublishCommands(map[string]any{"job": "demo"})
	if err != nil {
		t.Fatalf("expected native kafka commands: %v", err)
	}
	if kafkaCommands[0].Program != "kcat" || kafkaCommands[0].Stdin != "{\"job\":\"demo\"}" {
		t.Fatalf("unexpected kafka native command: %#v", kafkaCommands[0])
	}
}
