// Omega-Spider Cluster - Rust Worker 专家版
use anyhow::{anyhow, Result};
use futures::future::join_all;
use rand::Rng;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;
use tokio::time::sleep;

#[derive(Debug, Serialize, Deserialize, Clone)]
struct Task {
    id: i32,
    url: String,
    priority: i32,
    depth: i32,
}

pub struct DistributedWorker {
    id: String,
    master_url: String,
    client: Client,
    concurrency: usize,
}

impl DistributedWorker {
    pub fn new(master_url: &str, concurrency: usize) -> Self {
        let mut rng = rand::thread_rng();
        Self {
            id: format!("rust-worker-{}", rng.gen::<u16>()),
            master_url: master_url.to_string(),
            client: Client::builder()
                .timeout(Duration::from_secs(20))
                .build()
                .unwrap(),
            concurrency,
        }
    }

    pub async fn run(&self) {
        println!("❖ Rust Expert Worker [{}] 启动 ❖", self.id);

        // 1. 启动异步心跳
        let id = self.id.clone();
        let master = self.master_url.clone();
        let hb_client = self.client.clone();
        tokio::spawn(async move {
            loop {
                let payload =
                    serde_json::json!({ "id": id, "lang": "rust", "stats": {"active": true} });
                let _ = hb_client
                    .post(format!("{}/worker/heartbeat", master))
                    .json(&payload)
                    .send()
                    .await;
                sleep(Duration::from_secs(30)).await;
            }
        });

        loop {
            let mut tasks = Vec::new();
            for _ in 0..self.concurrency {
                if let Ok(Some(task)) = self.pull_task().await {
                    tasks.push(task);
                }
            }

            if tasks.is_empty() {
                sleep(Duration::from_secs(5)).await;
                continue;
            }

            let mut handles = Vec::new();
            for task in tasks {
                let client = self.client.clone();
                let master = self.master_url.clone();
                handles.push(tokio::spawn(async move {
                    // 2. 使用重试机制执行任务
                    let res = Self::process_with_retry(&client, &master, task, 3).await;
                    if let Err(e) = res {
                        eprintln!("Task failed after retries: {}", e);
                    }
                }));
            }
            join_all(handles).await;
        }
    }

    async fn process_with_retry(
        client: &Client,
        master: &str,
        task: Task,
        max_retries: usize,
    ) -> Result<()> {
        let mut last_err = anyhow!("Unknown error");
        for i in 0..max_retries {
            match Self::process_single_task(client, master, task.clone()).await {
                Ok(_) => return Ok(()),
                Err(e) => {
                    println!("重试 {}/{} 由于: {}", i + 1, max_retries, e);
                    last_err = e;
                    sleep(Duration::from_secs(2u64.pow(i as u32))).await; // 指数退避
                }
            }
        }
        Err(last_err)
    }

    async fn pull_task(&self) -> Result<Option<Task>> {
        let resp = self
            .client
            .get(format!("{}/task/get", self.master_url))
            .send()
            .await?;
        if resp.status() == 404 {
            return Ok(None);
        }
        Ok(Some(resp.json().await?))
    }

    async fn process_single_task(client: &Client, master: &str, task: Task) -> Result<()> {
        let resp = client.get(&task.url).send().await?;
        let len = resp.bytes().await?.len();
        let payload = serde_json::json!({
            "url": task.url,
            "status": "completed",
            "data": { "worker_lang": "rust", "content_length": len }
        });
        client
            .post(format!("{}/task/submit", master))
            .json(&payload)
            .send()
            .await?;
        Ok(())
    }
}
