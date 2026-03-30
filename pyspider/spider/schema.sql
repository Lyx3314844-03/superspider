-- Omega-Spider Cluster 数据库架构定义
-- 用于存储爬取任务及其进度

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- pending (待处理), running (执行中), completed (已完成), failed (失败)
    priority INTEGER DEFAULT 0,              -- 任务优先级
    depth INTEGER DEFAULT 0,                 -- 爬取深度
    data TEXT,                               -- JSON 格式的抓取结果数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以加快基于状态的查询速度
CREATE INDEX IF NOT EXISTS idx_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_priority ON tasks(priority DESC);
