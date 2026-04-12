import { PlaywrightCrawler, Dataset } from 'crawlee';

const url = 'https://www.youtube.com/watch?v=pDe00E3Gvh8&list=RDpDe00E3Gvh8&start_radio=1';

console.log('🚀 启动 YouTube 爬虫...');
console.log(`🎯 目标: ${url}`);

const crawler = new PlaywrightCrawler({
    // YouTube 反爬较严，建议降低并发，1 是最稳妥的
    maxConcurrency: 1, 
    // 最大重试次数
    maxRequestRetries: 2,
    // 请求处理函数
    async requestHandler({ page, request }) {
        console.log(`\n🌐 正在加载页面: ${request.url}`);

        try {
            // 等待页面核心数据加载完成
            // 我们可以通过判断 window.ytInitialPlayerResponse 是否存在来确认数据已加载
            await page.waitForFunction(() => !!window.ytInitialPlayerResponse, { timeout: 15000 });

            // 从全局变量中提取 JSON 数据（这是最稳的方式，比解析 DOM 元素更不容易失效）
            const data = await page.evaluate(() => {
                const playerData = window.ytInitialPlayerResponse;
                const videoDetails = playerData?.videoDetails || {};
                const microformat = playerData?.microformat?.playerMicroformatRenderer || {};

                return {
                    title: videoDetails.title,
                    videoId: videoDetails.videoId,
                    channelName: videoDetails.author,
                    channelId: videoDetails.channelId,
                    views: videoDetails.viewCount,
                    lengthSeconds: videoDetails.lengthSeconds,
                    description: videoDetails.shortDescription?.substring(0, 100) + '...',
                    isLive: videoDetails.isLiveContent,
                    publishDate: microformat.publishDate,
                    category: microformat.category,
                    keywords: videoDetails.keywords || [],
                    crawledAt: new Date().toISOString()
                };
            });

            // 打印提取的数据
            console.log('✅ 数据提取成功:');
            console.log(`📺 标题: ${data.title}`);
            console.log(`👤 频道: ${data.channelName}`);
            console.log(`👁️  观看次数: ${Number(data.views).toLocaleString()}`);
            console.log(`⏱️  时长: ${Math.floor(data.lengthSeconds / 60)} 分钟`);
            console.log(`📅 发布时间: ${data.publishDate}`);

            // 将数据保存到数据集（默认会保存为 JSON/CSV 文件）
            await Dataset.pushData(data);

        } catch (error) {
            console.error('❌ 提取数据失败:', error.message);
            // 如果是验证码拦截，Crawlee 会自动重试
        }
    },
    // 失败处理
    failedRequestHandler({ request }) {
        console.error(`❌ 请求彻底失败了: ${request.url}`);
    },
});

// 开始运行
try {
    await crawler.run([url]);
    console.log('\n🎉 爬取任务完成！');
    console.log('📂 数据已保存到 ./storage/datasets/default/ 目录下');
} catch (err) {
    console.error('💥 爬虫运行异常:', err);
}
