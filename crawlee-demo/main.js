import { PlaywrightCrawler, Dataset } from 'crawlee';

// 创建一个 PlaywrightCrawler 实例
// PlaywrightCrawler 结合了 Crawlee 的强大功能和 Playwright 的浏览器自动化能力
const crawler = new PlaywrightCrawler({
    // 限制并发请求数，以免被封禁
    maxConcurrency: 2,
    
    // 每次请求的处理函数
    async requestHandler({ page, request }) {
        const title = await page.title();
        console.log(`URL: ${request.loadedUrl} | 标题: ${title}`);
        
        // 提取页面数据
        await Dataset.pushData({
            url: request.loadedUrl,
            title,
            content: await page.content()
        });
    },
});

// 定义要抓取的 URL 列表
await crawler.run([
    'https://crawlee.dev',
    'https://crawlee.dev/docs/introduction',
]);

console.log('✅ 爬取完成！数据已保存。');
