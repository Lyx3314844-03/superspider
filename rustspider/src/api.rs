//! API 模块（简化版）

use crate::monitor::SpiderMonitor;

/// API 状态
#[derive(Clone)]
pub struct ApiState;

impl ApiState {
    pub fn new() -> Self {
        Self
    }

    pub fn register_monitor(&self, _name: &str, _monitor: SpiderMonitor) {
        // 简化实现
    }
}

impl Default for ApiState {
    fn default() -> Self {
        Self::new()
    }
}
