/**
 * Crawlee 示例代码
 * Node.js 全功能爬虫库，支持静态与动态网页
 * 安装: npm install crawlee
 */
import { CheerioCrawler } from 'crawlee';

const crawler = new CheerioCrawler({
    async requestHandler({ $, request }) {
        const title = $('title').text();
        console.log(`标题: ${title}`);
        console.log(`URL: ${request.url}`);
    },
});

await crawler.run(['https://example.com']);
