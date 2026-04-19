use rustspider::{
    queue_backend_support, NativeQueueClient, QueueBackendConfig, QueueBackendKind,
    QueueBridgeClient,
};
use serde_json::json;
use std::io::{Read, Write};
use std::net::TcpListener;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

struct MockServer {
    addr: String,
    shutdown: Arc<AtomicBool>,
    handle: Option<thread::JoinHandle<()>>,
}

impl Drop for MockServer {
    fn drop(&mut self) {
        self.shutdown.store(true, Ordering::SeqCst);
        let _ = std::net::TcpStream::connect(&self.addr);
        if let Some(handle) = self.handle.take() {
            let _ = handle.join();
        }
    }
}

fn start_mock_server(last_request: Arc<Mutex<String>>) -> MockServer {
    let listener = TcpListener::bind("127.0.0.1:0").expect("listener should bind");
    listener
        .set_nonblocking(true)
        .expect("listener should be non-blocking");
    let addr = listener.local_addr().expect("addr");
    let shutdown = Arc::new(AtomicBool::new(false));
    let shutdown_flag = shutdown.clone();

    let handle = thread::spawn(move || {
        while !shutdown_flag.load(Ordering::SeqCst) {
            match listener.accept() {
                Ok((mut stream, _)) => {
                    let mut buffer = [0_u8; 8192];
                    let size = stream.read(&mut buffer).unwrap_or(0);
                    let request = String::from_utf8_lossy(&buffer[..size]).to_string();
                    *last_request.lock().expect("request lock") = request;
                    let response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}";
                    let _ = stream.write_all(response.as_bytes());
                    let _ = stream.flush();
                }
                Err(err) if err.kind() == std::io::ErrorKind::WouldBlock => {
                    thread::sleep(Duration::from_millis(20));
                }
                Err(_) => break,
            }
        }
    });

    MockServer {
        addr: addr.to_string(),
        shutdown,
        handle: Some(handle),
    }
}

#[test]
fn queue_backend_detection_supports_rabbitmq_and_kafka_bridge_urls() {
    assert_eq!(
        QueueBackendConfig::detect("rabbitmq://localhost:5672/amq.default?routing_key=spider.jobs"),
        Some(QueueBackendKind::RabbitMq)
    );
    assert_eq!(
        QueueBackendConfig::detect("kafka://localhost:9092/spider-tasks"),
        Some(QueueBackendKind::Kafka)
    );
    assert_eq!(
        QueueBackendConfig::detect(
            "rabbitmq+http://localhost:15672/api/exchanges/%2F/amq.default/publish"
        ),
        Some(QueueBackendKind::RabbitMq)
    );
    assert_eq!(
        QueueBackendConfig::detect("kafka+http://localhost:8082/topics/spider-tasks"),
        Some(QueueBackendKind::Kafka)
    );
}

#[test]
fn rabbitmq_bridge_client_posts_management_publish_payload() {
    let last_request = Arc::new(Mutex::new(String::new()));
    let server = start_mock_server(last_request.clone());
    let endpoint = format!(
        "rabbitmq+http://{}/api/exchanges/%2F/amq.default/publish",
        server.addr
    );
    let mut config = QueueBackendConfig::new(QueueBackendKind::RabbitMq, endpoint);
    config.routing_key = Some("spider.jobs".to_string());

    let client = QueueBridgeClient::new(config).expect("bridge client should build");
    client
        .publish_json(&json!({"job": "demo"}))
        .expect("rabbitmq bridge publish should succeed");

    let request = last_request.lock().expect("request lock").clone();
    assert!(request.contains("POST /api/exchanges/%2F/amq.default/publish"));
    assert!(request.contains("\"routing_key\":\"spider.jobs\""));
    assert!(request.contains("\"payload_encoding\":\"string\""));
}

#[test]
fn kafka_bridge_client_posts_rest_proxy_payload() {
    let last_request = Arc::new(Mutex::new(String::new()));
    let server = start_mock_server(last_request.clone());
    let endpoint = format!("kafka+http://{}/topics/spider-tasks", server.addr);
    let config = QueueBackendConfig::new(QueueBackendKind::Kafka, endpoint);

    let client = QueueBridgeClient::new(config).expect("bridge client should build");
    client
        .publish_json(&json!({"job": "demo"}))
        .expect("kafka bridge publish should succeed");

    let request = last_request.lock().expect("request lock").clone();
    assert!(request.contains("POST /topics/spider-tasks"));
    assert!(request.contains("\"records\":[{\"value\":{\"job\":\"demo\"}}]"));

    let support = queue_backend_support();
    assert_eq!(
        support["native_process"]["rabbitmq"]["commands"][0],
        "amqp-publish"
    );
    assert_eq!(support["native_process"]["kafka"]["commands"][0], "kcat");
    assert_eq!(
        support["bridged"]["rabbitmq"]["adapter_engine"],
        "rabbitmq-management-api"
    );
    assert_eq!(
        support["bridged"]["kafka"]["adapter_engine"],
        "kafka-rest-proxy"
    );
}

#[test]
fn native_queue_client_builds_cli_commands() {
    let mut rabbit = QueueBackendConfig::new(
        QueueBackendKind::RabbitMq,
        "rabbitmq://localhost:5672/amq.default?routing_key=spider.jobs",
    );
    rabbit.routing_key = Some("spider.jobs".to_string());
    let rabbit_specs = NativeQueueClient::new(rabbit)
        .build_publish_commands(&json!({"job": "demo"}))
        .expect("native rabbitmq commands");
    assert_eq!(rabbit_specs[0].program, "amqp-publish");
    assert!(rabbit_specs[0]
        .args
        .iter()
        .any(|arg| arg == "--routing-key"));

    let mut kafka = QueueBackendConfig::new(
        QueueBackendKind::Kafka,
        "kafka://localhost:9092/spider-tasks",
    );
    kafka.topic = Some("spider-tasks".to_string());
    let kafka_specs = NativeQueueClient::new(kafka)
        .build_publish_commands(&json!({"job": "demo"}))
        .expect("native kafka commands");
    assert_eq!(kafka_specs[0].program, "kcat");
    assert_eq!(kafka_specs[0].stdin.as_deref(), Some("{\"job\":\"demo\"}"));
}
