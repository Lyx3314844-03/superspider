use rustspider::{HTTPDownloader, Request};
use std::io::{Read, Write};
use std::net::TcpListener;

#[test]
fn http_downloader_attaches_access_friction_report() {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind");
    let addr = listener.local_addr().expect("addr");

    std::thread::spawn(move || {
        if let Ok((mut stream, _)) = listener.accept() {
            let mut buffer = [0u8; 1024];
            let _ = stream.read(&mut buffer);
            let body = "checking your browser";
            let response = format!(
                "HTTP/1.1 429 Too Many Requests\r\nRetry-After: 45\r\nCF-Ray: demo\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                body.len(),
                body
            );
            let _ = stream.write_all(response.as_bytes());
        }
    });

    let response = HTTPDownloader::new().download(&Request::new(format!("http://{addr}")));
    let report = response
        .access_friction
        .expect("expected access friction report");

    assert_eq!(report.level, "high");
    assert!(report.blocked);
    assert_eq!(report.retry_after_seconds, Some(45));
    assert!(report.should_upgrade_to_browser);
}
