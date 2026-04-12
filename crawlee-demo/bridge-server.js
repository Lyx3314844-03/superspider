import express from 'express';
import { PlaywrightCrawler, Dataset } from 'crawlee';

const app = express();
app.use(express.json());

// 启动 Crawlee 爬虫实例
const runCrawleeJob = async (config) => {
    const results = [];

    const crawler = new PlaywrightCrawler({
        maxConcurrency: config.maxConcurrency || 2,
        maxRequestRetries: config.maxRetries || 3,
        // 可以在这里集成代理池配置
        
        async requestHandler({ page, request }) {
            // 如果配置了自定义 JS 执行，可以在这里运行
            if (config.onPageScript) {
                await page.evaluate(config.onPageScript);
            }

            // 提取数据逻辑
            const data = await page.evaluate(() => {
                return {
                    url: window.location.href,
                    title: document.title,
                    html: document.body.innerHTML.substring(0, 1000) + '...'
                };
            });

            results.push(data);
        },
    });

    // 执行抓取
    await crawler.run(config.urls);
    return results;
};

// 暴露 API
app.post('/api/crawl', async (req, res) => {
    try {
        const config = req.body;
        console.log('🚀 接收到 Crawlee 桥接请求:', config.urls);
        
        const results = await runCrawleeJob(config);
        
        res.json({ success: true, data: results });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

const PORT = 3100;
app.listen(PORT, () => {
    console.log(`🔗 Crawlee Bridge Service running on port ${PORT}`);
});
