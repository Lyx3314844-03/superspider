// RustSpider 数据导出模块 - 支持 JSON、CSV、Markdown 导出

use serde::Serialize;
use std::fs::{self, File};
use std::io::Write;

#[derive(Debug, Clone, Serialize)]
pub struct ExportData {
    pub title: String,
    pub url: String,
    pub snippet: String,
    pub source: String,
    pub time: String,
}

pub struct Exporter {
    output_dir: String,
}

impl Exporter {
    pub fn new(output_dir: &str) -> Self {
        fs::create_dir_all(output_dir).ok();
        Self {
            output_dir: output_dir.to_string(),
        }
    }

    pub fn export_json(&self, data: &[ExportData], filename: &str) -> Result<String, String> {
        let mut filename = filename.to_string();
        if !filename.ends_with(".json") {
            filename.push_str(".json");
        }
        let filepath = format!("{}/{}", self.output_dir, filename);

        let json = serde_json::to_string_pretty(&serde_json::json!({
            "schema_version": 1,
            "runtime": "rust",
            "exported_at": chrono::Local::now().to_rfc3339(),
            "item_count": data.len(),
            "items": data,
        }))
        .map_err(|e| e.to_string())?;

        fs::write(&filepath, json).map_err(|e| e.to_string())?;

        println!("✅ 已导出 JSON: {}", filepath);
        Ok(filepath)
    }

    pub fn export_csv(&self, data: &[ExportData], filename: &str) -> Result<String, String> {
        let mut filename = filename.to_string();
        if !filename.ends_with(".csv") {
            filename.push_str(".csv");
        }
        let filepath = format!("{}/{}", self.output_dir, filename);

        let mut file = File::create(&filepath).map_err(|e| e.to_string())?;

        writeln!(file, "Title,URL,Snippet,Source,Time").map_err(|e| e.to_string())?;

        for item in data {
            writeln!(
                file,
                "\"{}\",\"{}\",\"{}\",\"{}\",\"{}\"",
                item.title, item.url, item.snippet, item.source, item.time
            )
            .map_err(|e| e.to_string())?;
        }

        println!("✅ 已导出 CSV: {}", filepath);
        Ok(filepath)
    }

    pub fn export_markdown(&self, data: &[ExportData], filename: &str) -> Result<String, String> {
        let mut filename = filename.to_string();
        if !filename.ends_with(".md") {
            filename.push_str(".md");
        }
        let filepath = format!("{}/{}", self.output_dir, filename);

        let mut content = String::from("# 爬取结果\n\n");
        content.push_str(&format!("**数据条数**: {}\n\n", data.len()));
        content.push_str("| Title | URL | Source |\n");
        content.push_str("|-------|-----|--------|\n");

        for item in data {
            content.push_str(&format!(
                "| {} | [Link]({}) | {} |\n",
                item.title, item.url, item.source
            ));
        }

        fs::write(&filepath, content).map_err(|e| e.to_string())?;

        println!("✅ 已导出 Markdown: {}", filepath);
        Ok(filepath)
    }
}

// 任务调度模块
#[derive(Debug, Clone)]
pub struct SpiderTask {
    pub id: String,
    pub name: String,
    pub url: String,
    pub engine: String,
    pub interval: u64, // 秒
    pub enabled: bool,
    pub run_count: u32,
}

pub struct Scheduler {
    tasks: Vec<SpiderTask>,
}

impl Scheduler {
    pub fn new() -> Self {
        Self { tasks: Vec::new() }
    }

    pub fn add_task(&mut self, task: SpiderTask) {
        self.tasks.push(task);
    }

    pub fn list_tasks(&self) -> &Vec<SpiderTask> {
        &self.tasks
    }

    pub fn remove_task(&mut self, id: &str) {
        self.tasks.retain(|t| t.id != id);
    }
}

impl Default for Scheduler {
    fn default() -> Self {
        Self::new()
    }
}

// 性能监控模块
#[derive(Debug)]
pub struct Monitor {
    total_requests: u64,
    success_requests: u64,
    failed_requests: u64,
    start_time: std::time::Instant,
}

impl Monitor {
    pub fn new() -> Self {
        Self {
            total_requests: 0,
            success_requests: 0,
            failed_requests: 0,
            start_time: std::time::Instant::now(),
        }
    }

    pub fn record_request(&mut self, success: bool) {
        self.total_requests += 1;
        if success {
            self.success_requests += 1;
        } else {
            self.failed_requests += 1;
        }
    }

    pub fn get_success_rate(&self) -> f64 {
        if self.total_requests == 0 {
            return 0.0;
        }
        (self.success_requests as f64 / self.total_requests as f64) * 100.0
    }

    pub fn show_stats(&self) {
        let elapsed = self.start_time.elapsed().as_secs();
        let success_rate = self.get_success_rate();
        let reqs_per_sec = if elapsed > 0 {
            self.total_requests as f64 / elapsed as f64
        } else {
            0.0
        };

        println!("\n📈 性能监控:");
        println!("  运行时间: {} 秒", elapsed);
        println!("  总请求数: {}", self.total_requests);
        println!("  成功请求: {}", self.success_requests);
        println!("  失败请求: {}", self.failed_requests);
        println!("  成功率: {:.2}%", success_rate);
        println!("  爬取速度: {:.2} 请求/秒", reqs_per_sec);
    }
}

impl Default for Monitor {
    fn default() -> Self {
        Self::new()
    }
}
