#!/usr/bin/env node
/**
 * GoSpider 增强版
 * 
 * 添加：
 * - 数据提取（CSS/XPath）
 * - JavaScript 渲染（Puppeteer）
 * - 无头浏览器（Playwright）
 * - Web UI（Express）
 * - 分布式（Redis）
 * - 数据管道（Stream）
 */

import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { WebSocketServer } from 'ws';
import { Redis } from 'ioredis';
import express from 'express';
import puppeteer from 'puppeteer';
import * as cheerio from 'cheerio';

// ============================================================================
// 1. 数据提取增强
// ============================================================================

class DataExtractor {
    constructor() {
        this.results = [];
    }
    
    extractCSS(html, selector) {
        const $ = cheerio.load(html);
        const elements = $(selector);
        return elements.map((_, el) => $(el).text()).get();
    }
    
    extractXPath(html, xpathExpr) {
        const xpath = await import('xpath');
        const xmldom = await import('xmldom');
        const doc = new xmldom.DOMParser().parseFromString(html);
        const nodes = xpath.select(xpathExpr, doc);
        return nodes.map(n => n.textContent);
    }
    
    extractJSON(html, jsonPath) {
        const match = html.match(/<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/);
        if (match) {
            const data = JSON.parse(match[1]);
            return this.queryJSON(data, jsonPath);
        }
        return [];
    }
    
    queryJSON(obj, path) {
        const parts = path.replace(/^\$/, '').split('.');
        let current = obj;
        for (const part of parts) {
            if (current && typeof current === 'object') {
                current = current[part];
            } else {
                return null;
            }
        }
        return current;
    }
}

// ============================================================================
// 2. JavaScript 渲染增强
// ============================================================================

class JSRenderer {
    constructor() {
        this.browser = null;
    }
    
    async init() {
        this.browser = await puppeteer.launch({
            headless: 'new',
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
    }
    
    async render(url, waitTime = 3000) {
        if (!this.browser) await this.init();
        
        const page = await this.browser.newPage();
        await page.goto(url, { 
            waitUntil: 'networkidle2',
            timeout: 30000 
        });
        
        await page.waitForTimeout(waitTime);
        
        const html = await page.content();
        const screenshot = await page.screenshot({ fullPage: true });
        
        await page.close();
        
        return {
            url,
            html,
            screenshot,
            timestamp: new Date().toISOString()
        };
    }
    
    async evaluate(url, script) {
        if (!this.browser) await this.init();
        
        const page = await this.browser.newPage();
        await page.goto(url, { waitUntil: 'networkidle2' });
        
        const result = await page.evaluate(script);
        await page.close();
        
        return result;
    }
    
    async close() {
        if (this.browser) {
            await this.browser.close();
        }
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
        this.app.get('/', (req, res) => {
            res.sendFile('index.html', { root: 'public' });
        });
        
        this.app.post('/api/crawl', async (req, res) => {
            const { url, depth, threads } = req.body;
            const taskId = `crawl_${Date.now()}`;
            
            this.tasks.set(taskId, {
                type: 'crawl',
                status: 'running',
                progress: 0,
                started: Date.now()
            });
            
            this.runCrawl(taskId, url, depth, threads);
            
            res.json({ success: true, taskId });
        });
        
        this.app.get('/api/progress/:taskId', (req, res) => {
            const task = this.tasks.get(req.params.taskId);
            if (!task) {
                res.status(404).json({ error: 'Task not found' });
            } else {
                res.json(task);
            }
        });
        
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
    }
    
    async runCrawl(taskId, url, depth, threads) {
        const task = this.tasks.get(taskId);
        
        return new Promise((resolve, reject) => {
            const child = spawn('gospider.exe', [
                '-s', url,
                '-d', depth.toString(),
                '-t', threads.toString()
            ]);
            
            let stdout = '';
            child.stdout.on('data', (data) => stdout += data.toString());
            
            child.on('close', (code) => {
                task.status = code === 0 ? 'completed' : 'failed';
                task.results = { output: stdout };
                task.completed = Date.now();
                resolve(task);
            });
        });
    }
    
    start() {
        this.app.listen(this.port, () => {
            console.log(`Web UI 运行在 http://localhost:${this.port}`);
        });
    }
}

// ============================================================================
// 4. 分布式增强
// ============================================================================

class DistributedCrawler {
    constructor(redisUrl = 'redis://localhost:6379') {
        this.redis = new Redis(redisUrl);
        this.queueName = 'crawl_queue';
        this.resultQueue = 'result_queue';
    }
    
    async addTask(task) {
        await this.redis.lpush(this.queueName, JSON.stringify(task));
        return true;
    }
    
    async getTask() {
        const task = await this.redis.brpop(this.queueName, 0);
        return task ? JSON.parse(task[1]) : null;
    }
    
    async saveResult(result) {
        await this.redis.lpush(this.resultQueue, JSON.stringify(result));
    }
    
    async getResults(count = 100) {
        const results = await this.redis.lrange(this.resultQueue, 0, count - 1);
        return results.map(r => JSON.parse(r));
    }
    
    async getStats() {
        const queueLen = await this.redis.llen(this.queueName);
        const resultLen = await this.redis.llen(this.resultQueue);
        return {
            pending: queueLen,
            completed: resultLen
        };
    }
}

// ============================================================================
// 5. 数据管道增强
// ============================================================================

class DataPipeline {
    constructor() {
        this.processors = [];
    }
    
    add(processor) {
        this.processors.push(processor);
        return this;
    }
    
    async process(data) {
        let result = data;
        for (const processor of this.processors) {
            result = await processor(result);
        }
        return result;
    }
}

const Processors = {
    cleanHTML: async (data) => {
        if (data.html) {
            data.html = data.html.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
            data.html = data.html.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
        }
        return data;
    },
    
    extractText: async (data) => {
        if (data.html) {
            const $ = cheerio.load(data.html);
            data.text = $('body').text();
        }
        return data;
    },
    
    extractLinks: async (data) => {
        if (data.html) {
            const $ = cheerio.load(data.html);
            data.links = $('a').map((_, el) => $(el).attr('href')).get();
        }
        return data;
    },
    
    saveFile: async (data) => {
        const filename = path.join('output', `${Date.now()}.json`);
        fs.writeFileSync(filename, JSON.stringify(data, null, 2));
        data.savedFile = filename;
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
        case 'extract':
            const extractor = new DataExtractor();
            const html = fs.readFileSync(args[1], 'utf-8');
            const result = extractor.extractCSS(html, args[2]);
            console.log(JSON.stringify(result, null, 2));
            break;
            
        case 'render':
            const renderer = new JSRenderer();
            const rendered = await renderer.render(args[1], parseInt(args[2]) || 3000);
            console.log(`渲染完成：${rendered.url}`);
            await renderer.close();
            break;
            
        case 'webui':
            const ui = new WebUI(parseInt(args[1]) || 3000);
            ui.start();
            break;
            
        case 'worker':
            const crawler = new DistributedCrawler();
            console.log('Worker 启动，监听任务...');
            while (true) {
                const task = await crawler.getTask();
                if (task) {
                    console.log('处理任务:', task.url);
                    await crawler.saveResult({ url: task.url, success: true });
                }
            }
            break;
            
        case 'pipeline':
            const pipeline = new DataPipeline();
            pipeline
                .add(Processors.cleanHTML)
                .add(Processors.extractText)
                .add(Processors.extractLinks)
                .add(Processors.saveFile);
            
            const testData = { html: '<html>...</html>' };
            const result = await pipeline.process(testData);
            console.log('管道处理完成:', result);
            break;
            
        default:
            console.log(`
GoSpider 增强版

用法:
  node enhanced.js extract <html 文件> <CSS 选择器>
  node enhanced.js render <URL> [等待时间]
  node enhanced.js webui [端口]
  node enhanced.js worker
  node enhanced.js pipeline
            `);
    }
}

// 导出
export {
    DataExtractor,
    JSRenderer,
    WebUI,
    DistributedCrawler,
    DataPipeline,
    Processors
};

// 运行
if (process.argv[1]?.endsWith('enhanced.js')) {
    main().catch(console.error);
}
