use rustspider::DistributedWorker;
use std::env;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let master_url = env::args()
        .nth(1)
        .unwrap_or_else(|| "http://localhost:5000".to_string());

    let worker = DistributedWorker::new(&master_url, 4);
    worker.run().await;
    Ok(())
}
