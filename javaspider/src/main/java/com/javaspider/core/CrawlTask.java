package com.javaspider.core;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * 统一爬取任务格式
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CrawlTask {
    private String url;
    private int priority;
    private int depth;
    private String task_type;
    private String spider_name;
    private double created_at;
    private int retry_count;
    private Map<String, Object> metadata;
}
