#!/usr/bin/env node
/**
 * JavaSpider 增强版
 * 
 * 添加：
 * - 站点地图生成
 * - 视频下载（集成 downloader）
 * - API 扫描
 * - Web UI（Spring Boot）
 */

import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SPIDER_DIR = path.join(__dirname);

// ============================================================================
// 1. 站点地图增强
// ============================================================================

class SitemapGenerator {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.urls = [];
    }
    
    /**
     * 爬取生成站点地图
     */
    async crawlForSitemap(startUrl, depth = 3) {
        return new Promise((resolve, reject) => {
            const args = [
                '-jar', 'target/javaspider.jar',
                'crawl',
                '-u', startUrl,
                '-d', depth.toString(),
                '--export', 'json'
            ];
            
            const child = spawn('java', args, {
                cwd: SPIDER_DIR
            });
            
            let stdout = '';
            child.stdout.on('data', (data) => stdout += data.toString());
            
            child.on('close', (code) => {
                if (code === 0) {
                    try {
                        const data = JSON.parse(stdout);
                        this.urls = data.urls || [];
                        resolve(this.urls);
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
     * 生成 XML 站点地图
     */
    generateXML(outputFile = 'sitemap.xml') {
        let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n';
        
        for (const url of this.urls) {
            xml += '  <url>\n';
            xml += `    <loc>${url}</loc>\n`;
            xml += '    <changefreq>weekly</changefreq>\n';
            xml += '    <priority>0.5</priority>\n';
            xml += '  </url>\n';
        }
        
        xml += '</urlset>';
        
        fs.writeFileSync(outputFile, xml, 'utf-8');
        console.log(`站点地图已保存到：${outputFile}`);
        return outputFile;
    }
    
    /**
     * 生成 JSON 站点地图
     */
    generateJSON(outputFile = 'sitemap.json') {
        const data = {
            base_url: this.baseUrl,
            total_urls: this.urls.length,
            urls: this.urls,
            generated_at: new Date().toISOString()
        };
        
        fs.writeFileSync(outputFile, JSON.stringify(data, null, 2), 'utf-8');
        console.log(`站点地图已保存到：${outputFile}`);
        return outputFile;
    }
}

// ============================================================================
// 2. 视频下载增强
// ============================================================================

class VideoDownloader {
    constructor(outputDir = './videos') {
        this.outputDir = outputDir;
        if (!fs.existsSync(outputDir)) {
            fs.mkdirSync(outputDir, { recursive: true });
        }
    }
    
    /**
     * 下载视频
     */
    async download(url, options = {}) {
        const {
            quality = 'best',
            format = 'mp4',
            audioOnly = false
        } = options;
        
        return new Promise((resolve, reject) => {
            // 使用 Java 下载器或调用外部工具
            const args = [
                '-jar', 'target/downloader.jar',
                url,
                '-o', this.outputDir,
                '-q', quality
            ];
            
            if (audioOnly) {
                args.push('-x');
            }
            
            const child = spawn('java', args, {
                cwd: SPIDER_DIR
            });
            
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
            const child = spawn('java', [
                '-jar', 'target/downloader.jar',
                url,
                '--info'
            ], {
                cwd: SPIDER_DIR
            });
            
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
// 3. API 扫描增强
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
            const result = await this.testEndpoint(url, methods, timeout);
            if (result.found) {
                results.push(result);
            }
        }
        
        // 从页面提取 API 链接
        const links = await this.extractAPILinks(baseUrl, depth);
        for (const link of links) {
            if (!results.find(r => r.url === link)) {
                const result = await this.testEndpoint(link, methods, timeout);
                if (result.found) {
                    results.push(result);
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
        return new Promise((resolve, reject) => {
            const args = [
                '-jar', 'target/javaspider.jar',
                'crawl',
                '-u', baseUrl,
                '-d', depth.toString(),
                '--export', 'json'
            ];
            
            const child = spawn('java', args, {
                cwd: SPIDER_DIR
            });
            
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
// 4. Web UI 增强
// ============================================================================

class WebUI {
    constructor(port = 8080) {
        this.port = port;
        this.tasks = new Map();
    }
    
    /**
     * 启动 Web UI
     */
    start() {
        console.log(`启动 JavaSpider Web UI...`);
        console.log(`访问：http://localhost:${this.port}`);
        
        const args = [
            '-jar', 'target/webui.jar',
            '--server.port', this.port.toString()
        ];
        
        const child = spawn('java', args, {
            cwd: SPIDER_DIR
        });
        
        child.stdout.on('data', (data) => {
            console.log(data.toString());
        });
        
        child.stderr.on('data', (data) => {
            console.error(data.toString());
        });
    }
}

// ============================================================================
// 5. 数据管道增强
// ============================================================================

class DataPipeline {
    constructor() {
        this.processors = [];
    }
    
    /**
     * 添加处理器
     */
    add(processor) {
        this.processors.push(processor);
        return this;
    }
    
    /**
     * 处理数据
     */
    async process(data) {
        let result = data;
        for (const processor of this.processors) {
            result = await processor(result);
        }
        return result;
    }
    
    /**
     * 批量处理
     */
    async processBatch(items, concurrency = 10) {
        const results = [];
        const batches = [];
        
        for (let i = 0; i < items.length; i += concurrency) {
            batches.push(items.slice(i, i + concurrency));
        }
        
        for (const batch of batches) {
            const batchResults = await Promise.all(
                batch.map(item => this.process(item))
            );
            results.push(...batchResults);
        }
        
        return results;
    }
}

// 预定义处理器
const Processors = {
    cleanHTML: async (data) => {
        if (data.html) {
            data.html = data.html
                .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
                .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
        }
        return data;
    },
    
    extractText: async (data) => {
        const cheerio = require('cheerio');
        if (data.html) {
            const $ = cheerio.load(data.html);
            data.text = $('body').text().trim();
        }
        return data;
    },
    
    extractLinks: async (data) => {
        const cheerio = require('cheerio');
        if (data.html) {
            const $ = cheerio.load(data.html);
            data.links = $('a').map((_, el) => $(el).attr('href')).get();
        }
        return data;
    },
    
    extractImages: async (data) => {
        const cheerio = require('cheerio');
        if (data.html) {
            const $ = cheerio.load(data.html);
            data.images = $('img').map((_, el) => $(el).attr('src')).get();
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
        case 'sitemap':
            // 生成站点地图
            const url = args[1] || 'https://example.com';
            const depth = parseInt(args[2]) || 3;
            
            const generator = new SitemapGenerator(url);
            const urls = await generator.crawlForSitemap(url, depth);
            generator.generateXML();
            generator.generateJSON();
            
            console.log(`发现 ${urls.length} 个 URL`);
            break;
            
        case 'download':
            // 视频下载
            const downloadUrl = args[1] || '';
            const quality = args[2] || 'best';
            
            const downloader = new VideoDownloader();
            const result = await downloader.download(downloadUrl, { quality });
            console.log('下载完成:', result);
            break;
            
        case 'scan':
            // API 扫描
            const scanUrl = args[1] || '';
            const scanDepth = parseInt(args[2]) || 2;
            
            const scanner = new APIScanner();
            const scanResult = await scanner.scan(scanUrl, { depth: scanDepth });
            console.log(`发现 ${scanResult.total} 个 API 端点`);
            console.log(JSON.stringify(scanResult, null, 2));
            break;
            
        case 'webui':
            // 启动 Web UI
            const port = parseInt(args[1]) || 8080;
            const webui = new WebUI(port);
            webui.start();
            break;
            
        case 'pipeline':
            // 数据管道测试
            const pipeline = new DataPipeline();
            pipeline
                .add(Processors.cleanHTML)
                .add(Processors.extractText)
                .add(Processors.extractLinks)
                .add(Processors.saveFile);
            
            const testData = { html: '<html><head><title>Test</title></head><body>Hello</body></html>' };
            const result = await pipeline.process(testData);
            console.log('管道处理完成:', result);
            break;
            
        default:
            console.log(`
JavaSpider 增强版

用法:
  node enhanced.js sitemap <URL> [深度]
  node enhanced.js download <URL> [画质]
  node enhanced.js scan <URL> [深度]
  node enhanced.js webui [端口]
  node enhanced.js pipeline

功能:
  - 站点地图生成（XML/JSON）
  - 视频下载（多平台支持）
  - API 端点扫描
  - Web 监控界面
  - 数据管道处理
            `);
    }
}

// 导出
export {
    SitemapGenerator,
    VideoDownloader,
    APIScanner,
    WebUI,
    DataPipeline,
    Processors
};

// 运行
if (process.argv[1]?.endsWith('enhanced.js')) {
    main().catch(console.error);
}
