package distributed

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"os/exec"
	"strings"
	"time"
)

// QueueBackendKind identifies supported message queue backends.
type QueueBackendKind string

const (
	QueueBackendMemory   QueueBackendKind = "memory"
	QueueBackendFileJSON QueueBackendKind = "file-json"
	QueueBackendRedis    QueueBackendKind = "redis"
	QueueBackendRabbitMQ QueueBackendKind = "rabbitmq"
	QueueBackendKafka    QueueBackendKind = "kafka"
)

// QueueBackendConfig captures native and bridge queue backend settings.
type QueueBackendConfig struct {
	Kind       QueueBackendKind  `json:"kind"`
	Endpoint   string            `json:"endpoint"`
	RoutingKey string            `json:"routing_key,omitempty"`
	Topic      string            `json:"topic,omitempty"`
	Headers    map[string]string `json:"headers,omitempty"`
	Username   string            `json:"username,omitempty"`
	Password   string            `json:"password,omitempty"`
}

// DetectQueueBackendKind infers the backend type from an endpoint URI.
func DetectQueueBackendKind(endpoint string) (QueueBackendKind, bool) {
	lower := strings.ToLower(strings.TrimSpace(endpoint))
	switch {
	case strings.HasPrefix(lower, "memory://"):
		return QueueBackendMemory, true
	case strings.HasPrefix(lower, "file://"):
		return QueueBackendFileJSON, true
	case strings.HasPrefix(lower, "redis://"):
		return QueueBackendRedis, true
	case strings.HasPrefix(lower, "rabbitmq://"):
		return QueueBackendRabbitMQ, true
	case strings.HasPrefix(lower, "kafka://"):
		return QueueBackendKafka, true
	case strings.HasPrefix(lower, "rabbitmq+http://"),
		strings.HasPrefix(lower, "rabbitmq+https://"),
		(strings.HasPrefix(lower, "http://") || strings.HasPrefix(lower, "https://")) && strings.Contains(lower, "/api/exchanges/"):
		return QueueBackendRabbitMQ, true
	case strings.HasPrefix(lower, "kafka+http://"),
		strings.HasPrefix(lower, "kafka+https://"),
		(strings.HasPrefix(lower, "http://") || strings.HasPrefix(lower, "https://")) && strings.Contains(lower, "/topics/"):
		return QueueBackendKafka, true
	default:
		return "", false
	}
}

// NewQueueBackendConfig creates a queue backend config with sensible defaults.
func NewQueueBackendConfig(kind QueueBackendKind, endpoint string) QueueBackendConfig {
	return QueueBackendConfig{
		Kind:     kind,
		Endpoint: endpoint,
		Headers:  map[string]string{},
	}
}

// QueueBridgeClient publishes queue payloads through bridge HTTP endpoints.
type QueueBridgeClient struct {
	client *http.Client
	config QueueBackendConfig
}

// QueueCommandSpec describes a native CLI publish attempt.
type QueueCommandSpec struct {
	Program string
	Args    []string
	Stdin   string
}

// NativeQueueClient publishes to broker-native CLIs when available.
type NativeQueueClient struct {
	config QueueBackendConfig
}

// NewNativeQueueClient constructs a native queue client for RabbitMQ/Kafka URIs.
func NewNativeQueueClient(config QueueBackendConfig) *NativeQueueClient {
	return &NativeQueueClient{config: config}
}

// BuildPublishCommands returns broker-native CLI command candidates.
func (c *NativeQueueClient) BuildPublishCommands(payload any) ([]QueueCommandSpec, error) {
	switch c.config.Kind {
	case QueueBackendRabbitMQ:
		return c.buildRabbitMQCommands(payload)
	case QueueBackendKafka:
		return c.buildKafkaCommands(payload)
	default:
		return nil, fmt.Errorf("native queue client only supports RabbitMQ/Kafka")
	}
}

// PublishJSON executes the first available native CLI candidate.
func (c *NativeQueueClient) PublishJSON(payload any) error {
	specs, err := c.BuildPublishCommands(payload)
	if err != nil {
		return err
	}
	var lastErr error
	for _, spec := range specs {
		cmd := exec.Command(spec.Program, spec.Args...)
		if spec.Stdin != "" {
			cmd.Stdin = strings.NewReader(spec.Stdin)
		}
		if err := cmd.Run(); err == nil {
			return nil
		} else {
			lastErr = err
		}
	}
	if lastErr == nil {
		lastErr = fmt.Errorf("no native queue command available")
	}
	return lastErr
}

// NewQueueBridgeClient builds an HTTP bridge client for RabbitMQ/Kafka backends.
func NewQueueBridgeClient(config QueueBackendConfig) (*QueueBridgeClient, error) {
	if strings.TrimSpace(config.Endpoint) == "" {
		return nil, fmt.Errorf("queue backend endpoint is required")
	}
	if config.Headers == nil {
		config.Headers = map[string]string{}
	}
	return &QueueBridgeClient{
		client: &http.Client{Timeout: 30 * time.Second},
		config: config,
	}, nil
}

// PublishJSON sends a JSON payload to the configured bridge backend.
func (c *QueueBridgeClient) PublishJSON(payload any) error {
	switch c.config.Kind {
	case QueueBackendRabbitMQ:
		return c.publishRabbitMQ(payload)
	case QueueBackendKafka:
		return c.publishKafka(payload)
	case QueueBackendMemory, QueueBackendFileJSON, QueueBackendRedis:
		return fmt.Errorf("queue bridge client only handles RabbitMQ/Kafka bridge endpoints")
	default:
		return fmt.Errorf("unsupported queue backend kind: %s", c.config.Kind)
	}
}

func (c *QueueBridgeClient) publishRabbitMQ(payload any) error {
	body := map[string]any{
		"properties":       map[string]any{},
		"routing_key":      c.config.RoutingKey,
		"payload":          mustJSONString(payload),
		"payload_encoding": "string",
	}
	return c.postJSON(normalizeBridgeEndpoint(c.config.Endpoint, "rabbitmq+http://", "rabbitmq+https://"), body, "rabbitmq publish failed")
}

func (c *QueueBridgeClient) publishKafka(payload any) error {
	body := map[string]any{
		"records": []map[string]any{
			{"value": payload},
		},
	}
	return c.postJSON(normalizeBridgeEndpoint(c.config.Endpoint, "kafka+http://", "kafka+https://"), body, "kafka publish failed")
}

func (c *QueueBridgeClient) postJSON(endpoint string, body any, failurePrefix string) error {
	data, err := json.Marshal(body)
	if err != nil {
		return err
	}
	req, err := http.NewRequest(http.MethodPost, endpoint, bytes.NewReader(data))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	for key, value := range c.config.Headers {
		req.Header.Set(key, value)
	}
	if c.config.Username != "" || c.config.Password != "" {
		req.SetBasicAuth(c.config.Username, c.config.Password)
	}
	resp, err := c.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("%s: %s", failurePrefix, resp.Status)
	}
	return nil
}

func mustJSONString(payload any) string {
	data, err := json.Marshal(payload)
	if err != nil {
		return "{}"
	}
	return string(data)
}

func normalizeBridgeEndpoint(endpoint, httpPrefix, httpsPrefix string) string {
	if strings.HasPrefix(endpoint, httpPrefix) {
		return "http://" + strings.TrimPrefix(endpoint, httpPrefix)
	}
	if strings.HasPrefix(endpoint, httpsPrefix) {
		return "https://" + strings.TrimPrefix(endpoint, httpsPrefix)
	}
	return endpoint
}

// QueueBackendSupport describes native and bridged queue backends.
func QueueBackendSupport() map[string]any {
	return map[string]any{
		"native": []string{
			string(QueueBackendMemory),
			string(QueueBackendFileJSON),
			string(QueueBackendRedis),
			string(QueueBackendRabbitMQ),
			string(QueueBackendKafka),
		},
		"native_process": map[string]any{
			string(QueueBackendRabbitMQ): map[string]any{
				"mode":     "cli-adapter",
				"commands": []string{"amqp-publish", "rabbitmqadmin"},
			},
			string(QueueBackendKafka): map[string]any{
				"mode":     "cli-adapter",
				"commands": []string{"kcat", "kafka-console-producer"},
			},
		},
		"bridged": map[string]any{
			string(QueueBackendRabbitMQ): map[string]any{
				"mode":           "http-management-bridge",
				"adapter_engine": "rabbitmq-management-api",
			},
			string(QueueBackendKafka): map[string]any{
				"mode":           "rest-proxy-bridge",
				"adapter_engine": "kafka-rest-proxy",
			},
		},
	}
}

func (c *NativeQueueClient) buildRabbitMQCommands(payload any) ([]QueueCommandSpec, error) {
	parsed, err := url.Parse(c.config.Endpoint)
	if err != nil {
		return nil, err
	}
	host := parsed.Hostname()
	if host == "" {
		host = "localhost"
	}
	port := parsed.Port()
	if port == "" {
		port = "5672"
	}
	query := parsed.Query()
	segments := splitPath(parsed.Path)
	exchange := query.Get("exchange")
	if exchange == "" && len(segments) > 0 {
		exchange = segments[len(segments)-1]
	}
	if exchange == "" {
		exchange = "amq.default"
	}
	vhost := query.Get("vhost")
	if vhost == "" {
		vhost = "/"
	}
	routingKey := c.config.RoutingKey
	if routingKey == "" {
		routingKey = query.Get("routing_key")
	}
	body := mustJSONString(payload)
	amqpURL := fmt.Sprintf("amqp://%s:%s/%s", host, port, encodeVhost(vhost))
	return []QueueCommandSpec{
		{
			Program: "amqp-publish",
			Args: []string{
				"--url", amqpURL,
				"--exchange", exchange,
				"--routing-key", routingKey,
				"--body", body,
			},
		},
		{
			Program: "rabbitmqadmin",
			Args: []string{
				"--host", host,
				"--port", port,
				"--username", defaultString(c.config.Username, "guest"),
				"--password", defaultString(c.config.Password, "guest"),
				"--vhost", vhost,
				"publish",
				"exchange=" + exchange,
				"routing_key=" + routingKey,
				"payload=" + body,
			},
		},
	}, nil
}

func (c *NativeQueueClient) buildKafkaCommands(payload any) ([]QueueCommandSpec, error) {
	parsed, err := url.Parse(c.config.Endpoint)
	if err != nil {
		return nil, err
	}
	host := parsed.Hostname()
	if host == "" {
		host = "localhost"
	}
	port := parsed.Port()
	if port == "" {
		port = "9092"
	}
	topic := c.config.Topic
	if topic == "" {
		segments := splitPath(parsed.Path)
		if len(segments) > 0 {
			topic = segments[0]
		}
	}
	if topic == "" {
		topic = "spider-tasks"
	}
	hostPort := host + ":" + port
	body := mustJSONString(payload)
	return []QueueCommandSpec{
		{
			Program: "kcat",
			Args:    []string{"-b", hostPort, "-t", topic, "-P"},
			Stdin:   body,
		},
		{
			Program: "kafka-console-producer",
			Args:    []string{"--bootstrap-server", hostPort, "--topic", topic},
			Stdin:   body,
		},
	}, nil
}

func splitPath(path string) []string {
	parts := strings.Split(path, "/")
	segments := make([]string, 0, len(parts))
	for _, part := range parts {
		if trimmed := strings.TrimSpace(part); trimmed != "" {
			segments = append(segments, trimmed)
		}
	}
	return segments
}

func encodeVhost(vhost string) string {
	if vhost == "" || vhost == "/" {
		return "%2F"
	}
	return strings.ReplaceAll(vhost, "/", "%2F")
}

func defaultString(value, fallback string) string {
	if strings.TrimSpace(value) == "" {
		return fallback
	}
	return value
}
