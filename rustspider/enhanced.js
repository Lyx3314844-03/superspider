#!/usr/bin/env node
/**
 * RustSpider 增强版
 * 
 * 添加：
 * - 视频下载（集成 yt-dlp）
 * - API 扫描（集成目录扫描器）
 * - Web UI（Express 仪表盘）
 * - 分布式（Redis 消息队列）
 * - 数据管道（流式处理）
 */

import { spawn } from 'child_process';
import express from 'express';
import Redis from 'ioredis';
import * as fs from 'fs';
import * as path from 'path';

// ============================================================================
// 1. 视频下载增强
// ============================================================================

class VideoDownloader {
    constructor(outputDir = './videos') {
        this.outputDir = outputDir;
        if (!fs.existsSync(outputDir)) {
            fs.mkdirSync(outputDir, { recursive: true });
        }
    }
    
    /**
     * 下载视频（使用 yt-dlp）
     */
    async download(url, options = {}) {
        const {
            quality = 'best',
            format = 'mp4',
            audioOnly = false
        } = options;
        
        return new Promise((resolve, reject) => {
            const args = [
                url,
                '-o', path.join(this.outputDir, '%(title)s.%(ext)s'),
                '--no-playlist'
            ];
            
            if (audioOnly) {
                args.push('-x', '--audio-format', 'mp3');
            } else {
                args.push('-f', quality, '--merge-output-format', format);
            }
            
            const child = spawn('yt-dlp', args);
            
            let stdout = '';
            let stderr = '';
            
            child.stdout.on('data', (data) => stdout += data.toString());
            child.stderr.on('data', (data) => stderr += data.toString());
            
            child.on('close', (code) => {
                if (code === 0) {
                    resolve({
                        success: true,
                        output: stdout,
                        dir: this.outputDir
                    });
                } else {
                    reject(new Error(stderr || '下载失败'));
                }
            });
        });
    }
    
    /**
     * 批量下载
     */
    async downloadBatch(urls, options = {}) {
        const results = [];
        for (const url of urls) {
            try {
                const result = await this.download(url, options);
                results.push({ url, success: true, ...result });
            } catch (error) {
                results.push({ url, success: false, error: error.message });
            }
        }
        return results;
    }
    
    /**
     * 获取视频信息
     */
    async getInfo(url) {
        return new Promise((resolve, reject) => {
            const child = spawn('yt-dlp', [
                url,
                '--dump-json',
                '--no-download'
            ]);
            
            let stdout = '';
            child.stdout.on('data', (data) => stdout += data.toString());
            
            child.on('close', (code) => {
                if (code === 0) {
                    try {
                        resolve(JSON.parse(stdout));
                    } catch (e) {
                        reject(new Error('解析失败'));
                    }
                } else {
                    reject(new Error('获取信息失败'));
                }
            });
        });
    }
}

// ============================================================================
// 2. API 扫描增强
// ============================================================================

class APIScanner {
    constructor() {
        this.commonEndpoints = [
            '/api', '/api/v1', '/api/v2',
            '/graphql', '/graphql/v1',
            '/rest', '/rest/v1',
            '/swagger', '/swagger.json', '/swagger-ui',
            '/api-docs', '/openapi.json',
            '/health', '/healthz', '/ready',
            '/metrics', '/status', '/info'
        ];
        
        this.methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'];
    }
    
    /**
     * 扫描 API 端点
     */
    async scan(baseUrl, options = {}) {
        const {
            depth = 2,
            timeout = 5000,
            methods = ['GET']
        } = options;
        
        const results = [];
        
        // 扫描常见端点
        for (const endpoint of this.commonEndpoints) {
            const url = baseUrl + endpoint;
            try {
                const result = await this.testEndpoint(url, methods, timeout);
                if (result.found) {
                    results.push(result);
                }
            } catch (error) {
                // 忽略错误
            }
        }
        
        // 从页面提取 API 链接
        const links = await this.extractAPILinks(baseUrl, depth);
        for (const link of links) {
            if (!results.find(r => r.url === link)) {
                try {
                    const result = await this.testEndpoint(link, methods, timeout);
                    if (result.found) {
                        results.push(result);
                    }
                } catch (error) {
                    // 忽略
                }
            }
        }
        
        return {
            baseUrl,
            endpoints: results,
            total: results.length,
            timestamp: new Date().toISOString()
        };
    }
    
    /**
     * 测试端点
     */
    async testEndpoint(url, methods, timeout) {
        const result = {
            url,
            found: false,
            methods: [],
            responseTime: 0
        };
        
        for (const method of methods) {
            const start = Date.now();
            try {
                const response = await fetch(url, {
                    method,
                    timeout,
                    headers: {
                        'Accept': 'application/json'
                    }
                });
                
                const elapsed = Date.now() - start;
                
                if (response.ok || response.status === 401 || response.status === 403) {
                    result.found = true;
                    result.methods.push({
                        method,
                        status: response.status,
                        responseTime: elapsed
                    });
                }
            } catch (error) {
                // 忽略
            }
        }
        
        return result;
    }
    
    /**
     * 从页面提取 API 链接
     */
    async extractAPILinks(baseUrl, depth) {
        // 使用 spider 爬取页面
        return new Promise((resolve, reject) => {
            const child = spawn('spider.exe', [
                'crawl',
                '--url', baseUrl,
                '--depth', depth.toString(),
                '--export', 'json'
            ]);
            
            let stdout = '';
            child.stdout.on('data', (data) => stdout += data.toString());
            
            child.on('close', (code) => {
                if (code === 0) {
                    try {
                        const data = JSON.parse(stdout);
                        const links = data.urls || [];
                        // 过滤 API 链接
                        const apiLinks = links.filter(url => 
                            url.includes('/api') ||
                            url.includes('/graphql') ||
                            url.includes('/rest')
                        );
                        resolve(apiLinks);
                    } catch (e) {
                        resolve([]);
                    }
                } else {
                    resolve([]);
                }
            });
        });
    }
    
    /**
     * 生成 OpenAPI 规范
     */
    generateOpenAPI(results) {
        const openapi = {
            openapi: '3.0.0',
            info: {
                title: 'Scanned API',
                version: '1.0.0',
                description: 'Auto-generated from API scan'
            },
            servers: [{ url: results.baseUrl }],
            paths: {}
        };
        
        for (const endpoint of results.endpoints) {
            const path = endpoint.url.replace(results.baseUrl, '');
            openapi.paths[path] = {};
            
            for (const method of endpoint.methods) {
                openapi.paths[path][method.method.toLowerCase()] = {
                    summary: `Auto-discovered ${method.method} endpoint`,
                    responses: {
                        [method.status]: {
                            description: `Response ${method.status}`
                        }
                    }
                };
            }
        }
        
        return openapi;
    }
}

// ============================================================================
// 3. Web UI 增强
// ============================================================================

class WebUI {
    constructor(port = 3000) {
        this.app = express();
        this.port = port;
        this.tasks = new Map();
        this.setupMiddleware();
        this.setupRoutes();
        this.setupWebSocket();
    }
    
    setupMiddleware() {
        this.app.use(express.json());
        this.app.use(express.static('public'));
        this.app.use((req, res, next) => {
            res.header('Access-Control-Allow-Origin', '*');
            next();
        });
    }
    
    setupRoutes() {
        // 仪表盘
        this.app.get('/', (req, res) => {
            res.sendFile('dashboard.html', { root: 'public' });
        });
        
        // 开始爬取
        this.app.post('/api/crawl', async (req, res) => {
            const { url, depth, threads, javascript } = req.body;
            const taskId = `crawl_${Date.now()}`;
            
            this.tasks.set(taskId, {
                type: 'crawl',
                status: 'running',
                progress: 0,
                started: Date.now()
            });
            
            // 后台执行
            this.runCrawl(taskId, url, depth, threads, javascript);
            
            res.json({ success: true, taskId });
        });
        
        // 视频下载
        this.app.post('/api/download', async (req, res) => {
            const { url, quality } = req.body;
            const taskId = `download_${Date.now()}`;
            
            this.tasks.set(taskId, {
                type: 'download',
                status: 'running',
                progress: 0
            });
            
            this.runDownload(taskId, url, quality);
            
            res.json({ success: true, taskId });
        });
        
        // API 扫描
        this.app.post('/api/scan', async (req, res) => {
            const { url, depth } = req.body;
            const taskId = `scan_${Date.now()}`;
            
            this.tasks.set(taskId, {
                type: 'scan',
                status: 'running',
                progress: 0
            });
            
            this.runScan(taskId, url, depth);
            
            res.json({ success: true, taskId });
        });
        
        // 获取进度
        this.app.get('/api/progress/:taskId', (req, res) => {
            const task = this.tasks.get(req.params.taskId);
            if (!task) {
                res.status(404).json({ error: 'Task not found' });
            } else {
                res.json(task);
            }
        });
        
        // 获取结果
        this.app.get('/api/results/:taskId', (req, res) => {
            const task = this.tasks.get(req.params.taskId);
            if (!task) {
                res.status(404).json({ error: 'Task not found' });
            } else if (task.status !== 'completed') {
                res.json({ success: false, error: 'Task not completed' });
            } else {
                res.json({ success: true, data: task.results });
            }
        });
        
        // 任务列表
        this.app.get('/api/tasks', (req, res) => {
            const tasks = Array.from(this.tasks.values());
            res.json({ tasks });
        });
    }
    
    setupWebSocket() {
        const { WebSocketServer } = require('ws');
        const wss = new WebSocketServer({ port: this.port + 1 });
        
        wss.on('connection', (ws) => {
            console.log('WebSocket 客户端连接');
            
            // 定期推送进度更新
            const interval = setInterval(() => {
                for (const [id, task] of this.tasks.entries()) {
                    if (task.status === 'running') {
                        ws.send(JSON.stringify({
                            type: 'progress',
                            taskId: id,
                            progress: task.progress,
                            status: task.status
                        }));
                    }
                }
            }, 1000);
            
            ws.on('close', () => {
                clearInterval(interval);
            });
        });
        
        console.log(`WebSocket 运行在 ws://localhost:${this.port + 1}`);
    }
    
    async runCrawl(taskId, url, depth, threads, javascript) {
        const task = this.tasks.get(taskId);
        
        return new Promise((resolve, reject) => {
            const args = javascript
                ? ['crawl', '--url', url, '--depth', depth.toString(), '--javascript']
                : ['crawl', '--url', url, '--depth', depth.toString(), '--workers', threads.toString()];
            
            const child = spawn('spider.exe', args);
            
            let stdout = '';
            let urlsFound = 0;
            
            child.stdout.on('data', (data) => {
                stdout += data.toString();
                // 解析进度
                const match = data.toString().match(/Found (\d+) URLs/);
                if (match) {
                    urlsFound = parseInt(match[1]);
                    task.progress = Math.min(urlsFound / 100 * 100, 100);
                }
            });
            
            child.on('close', (code) => {
                task.status = code === 0 ? 'completed' : 'failed';
                task.results = { output: stdout, urlsFound };
                task.completed = Date.now();
                resolve(task);
            });
        });
    }
    
    async runDownload(taskId, url, quality) {
        const task = this.tasks.get(taskId);
        const downloader = new VideoDownloader();
        
        try {
            const result = await downloader.download(url, { quality });
            task.status = 'completed';
            task.results = result;
            task.progress = 100;
        } catch (error) {
            task.status = 'failed';
            task.error = error.message;
        }
        
        task.completed = Date.now();
    }
    
    async runScan(taskId, url, depth) {
        const task = this.tasks.get(taskId);
        const scanner = new APIScanner();
        
        try {
            const result = await scanner.scan(url, { depth });
            task.status = 'completed';
            task.results = result;
            task.progress = 100;
        } catch (error) {
            task.status = 'failed';
            task.error = error.message;
        }
        
        task.completed = Date.now();
    }
    
    start() {
        this.app.listen(this.port, () => {
            console.log(`Web UI 运行在 http://localhost:${this.port}`);
            console.log(`WebSocket 运行在 ws://localhost:${this.port + 1}`);
        });
    }
}

// ============================================================================
// 4. 分布式增强
// ============================================================================

class DistributedCrawler {
    constructor(redisUrl = 'redis://localhost:6379') {
        this.redis = new Redis(redisUrl);
        this.queueName = 'rustspider_queue';
        this.resultQueue = 'rustspider_results';
        this.workerId = `worker_${process.pid}`;
    }
    
    /**
     * 添加任务
     */
    async addTask(task) {
        await this.redis.lpush(this.queueName, JSON.stringify({
            ...task,
            createdAt: Date.now(),
            priority: task.priority || 0
        }));
        return true;
    }
    
    /**
     * 获取任务（带锁）
     */
    async getTask() {
        const result = await this.redis.brpop(this.queueName, 0);
        if (result) {
            const task = JSON.parse(result[1]);
            // 标记为处理中
            await this.redis.setex(
                `task:${task.id}:lock`,
                300, // 5 分钟超时
                this.workerId
            );
            return task;
        }
        return null;
    }
    
    /**
     * 保存结果
     */
    async saveResult(result) {
        await this.redis.lpush(this.resultQueue, JSON.stringify({
            ...result,
            completedAt: Date.now()
        }));
    }
    
    /**
     * 获取统计
     */
    async getStats() {
        const [queueLen, resultLen, activeWorkers] = await Promise.all([
            this.redis.llen(this.queueName),
            this.redis.llen(this.resultQueue),
            this.redis.keys('task:*:lock').then(keys => keys.length)
        ]);
        
        return {
            pending: queueLen,
            completed: resultLen,
            activeWorkers
        };
    }
    
    /**
     * 启动 Worker
     */
    async startWorker(handler) {
        console.log(`Worker ${this.workerId} 启动...`);
        
        while (true) {
            const task = await this.getTask();
            if (task) {
                console.log(`处理任务：${task.id} - ${task.url}`);
                try {
                    const result = await handler(task);
                    await this.saveResult({ ...result, success: true });
                } catch (error) {
                    await this.saveResult({ 
                        taskId: task.id, 
                        success: false, 
                        error: error.message 
                    });
                }
            }
        }
    }
}

// ============================================================================
// 5. 数据管道增强
// ============================================================================

class DataPipeline {
    constructor() {
        this.stages = [];
    }
    
    /**
     * 添加处理阶段
     */
    add(stage) {
        this.stages.push(stage);
        return this;
    }
    
    /**
     * 处理数据
     */
    async process(data) {
        let result = data;
        for (const stage of this.stages) {
            result = await stage(result);
        }
        return result;
    }
    
    /**
     * 批量处理
     */
    async processBatch(items, concurrency = 10) {
        const results = [];
        const batches = [];
        
        // 分批
        for (let i = 0; i < items.length; i += concurrency) {
            batches.push(items.slice(i, i + concurrency));
        }
        
        // 并发处理
        for (const batch of batches) {
            const batchResults = await Promise.all(
                batch.map(item => this.process(item))
            );
            results.push(...batchResults);
        }
        
        return results;
    }
}

// 预定义处理阶段
const Stages = {
    // HTML 清理
    cleanHTML: async (data) => {
        if (data.html) {
            data.html = data.html
                .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
                .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
        }
        return data;
    },
    
    // 提取文本
    extractText: async (data) => {
        const cheerio = require('cheerio');
        if (data.html) {
            const $ = cheerio.load(data.html);
            data.text = $('body').text().trim();
        }
        return data;
    },
    
    // 提取链接
    extractLinks: async (data) => {
        const cheerio = require('cheerio');
        if (data.html) {
            const $ = cheerio.load(data.html);
            data.links = $('a').map((_, el) => $(el).attr('href')).get();
        }
        return data;
    },
    
    // 提取图片
    extractImages: async (data) => {
        const cheerio = require('cheerio');
        if (data.html) {
            const $ = cheerio.load(data.html);
            data.images = $('img').map((_, el) => $(el).attr('src')).get();
        }
        return data;
    },
    
    // 提取标题
    extractTitle: async (data) => {
        const cheerio = require('cheerio');
        if (data.html) {
            const $ = cheerio.load(data.html);
            data.title = $('title').text().trim();
        }
        return data;
    },
    
    // 保存文件
    saveFile: async (data) => {
        const filename = path.join('output', `${Date.now()}.json`);
        fs.writeFileSync(filename, JSON.stringify(data, null, 2));
        data.savedFile = filename;
        return data;
    },
    
    // 发送到 Webhook
    sendWebhook: async (data) => {
        const webhookUrl = process.env.WEBHOOK_URL;
        if (webhookUrl) {
            await fetch(webhookUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        }
        return data;
    }
};

// ============================================================================
// CLI 入口
// ============================================================================

async function main() {
    const args = process.argv.slice(2);
    const command = args[0];
    
    switch (command) {
        case 'download':
            // 视频下载
            const downloader = new VideoDownloader();
            const result = await downloader.download(args[1], {
                quality: args[2] || 'best'
            });
            console.log('下载完成:', result);
            break;
            
        case 'scan':
            // API 扫描
            const scanner = new APIScanner();
            const scanResult = await scanner.scan(args[1], {
                depth: parseInt(args[2]) || 2
            });
            console.log(`发现 ${scanResult.total} 个 API 端点`);
            console.log(JSON.stringify(scanResult, null, 2));
            break;
            
        case 'webui':
            // 启动 Web UI
            const ui = new WebUI(parseInt(args[1]) || 3000);
            ui.start();
            break;
            
        case 'worker':
            // 启动分布式 worker
            const crawler = new DistributedCrawler();
            await crawler.startWorker(async (task) => {
                console.log('处理:', task.url);
                // 执行爬取
                return { url: task.url, success: true };
            });
            break;
            
        case 'pipeline':
            // 数据管道测试
            const pipeline = new DataPipeline();
            pipeline
                .add(Stages.cleanHTML)
                .add(Stages.extractTitle)
                .add(Stages.extractText)
                .add(Stages.extractLinks)
                .add(Stages.saveFile);
            
            const testData = { html: '<html><head><title>Test</title></head><body>Hello</body></html>' };
            const result = await pipeline.process(testData);
            console.log('管道处理完成:', result);
            break;
            
        default:
            console.log(`
RustSpider 增强版

用法:
  node enhanced.js download <URL> [画质]
  node enhanced.js scan <URL> [深度]
  node enhanced.js webui [端口]
  node enhanced.js worker
  node enhanced.js pipeline

功能:
  - 视频下载（支持多个平台）
  - API 端点扫描
  - Web 监控界面
  - 分布式爬取
  - 数据管道处理
            `);
    }
}

// 导出
export {
    VideoDownloader,
    APIScanner,
    WebUI,
    DistributedCrawler,
    DataPipeline,
    Stages
};

// 运行
if (process.argv[1]?.endsWith('enhanced.js')) {
    main().catch(console.error);
}
