import { PlaywrightCrawler, Dataset } from 'crawlee';
import { exec } from 'child_process';
import { promisify } from 'util';
import { writeFileSync } from 'fs';

const execAsync = promisify(exec);

// 你的 Node.js 逆向服务地址
const REVERSE_SERVICE_URL = 'http://localhost:3000';
const TARGET_URL = 'https://www.youtube.com/watch?v=pDe00E3Gvh8';

console.log('🚀 启动 YouTube 终极爬虫...');
console.log('🎯 目标: 拦截加密 API + 转发逆向分析 + 下载视频');

const crawler = new PlaywrightCrawler({
    maxConcurrency: 1, // YouTube 必须单线程防封
    
    async requestHandler({ page, request }) {
        console.log('\n🕸️ 开始拦截网络流...');

        // 1. 设置网络拦截器：监听请求 (Outgoing Requests)
        page.on('request', async (interceptedRequest) => {
            try {
                const url = interceptedRequest.url();
                
                // 过滤：寻找 YouTube 的核心 API 请求
                if (url.includes('youtubei/v1/')) {
                    const apiName = url.split('?')[0].split('/').pop();
                    
                    // 拦截 POST 数据 (Payload)
                    const postData = interceptedRequest.postData();
                    
                    if (postData) {
                        console.log(`📤 拦截到 ${apiName} 请求的加密 Payload!`);
                        
                        // 2. 将 Payload 转发给逆向服务
                        await sendPayloadToReverseService(apiName, postData);
                    }
                }
            } catch (error) {
                // ignore
            }
        });

        // 3. 设置响应拦截器 (Incoming Responses)
        page.on('response', async (response) => {
            try {
                const url = response.url();
                if (url.includes('youtubei/v1/player') && response.status() === 200) {
                    console.log('📥 拦截到 Player API 响应 (含视频流数据)');
                    const json = await response.json();
                    // 这里可以进一步解析 signatureCipher 等
                }
            } catch (e) {}
        });

        // 4. 访问页面
        console.log('🚀 正在访问 YouTube 页面...');
        await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded' });

        // 等待网络请求完成
        await page.waitForLoadState('networkidle');
        await new Promise(r => setTimeout(r, 2000));
        
        console.log('\n🏁 拦截阶段结束...');

        // 5. 下载视频 (使用 yt-dlp)
        console.log('📥 正在调用 yt-dlp 下载...');
        try {
            // 检查是否已存在
            const cmd = `yt-dlp -f "bestaudio" --restrict-filenames -o "downloaded_video.%(ext)s" "${TARGET_URL}"`;
            const { stdout, stderr } = await execAsync(cmd);
            if (stdout.includes('has already been downloaded')) {
                 console.log('✅ 视频已存在，无需重复下载。');
            } else {
                 console.log('✅ 视频下载完成！');
            }
        } catch (error) {
            console.warn('⚠️ yt-dlp 失败', error.message);
        }
    },
});

/**
 * 将捕获的 Payload 发送给 Node.js 逆向服务进行分析
 */
async function sendPayloadToReverseService(apiName, postData) {
    console.log(`📡 发送 ${apiName} 数据到逆向服务...`);
    
    try {
        // 使用 fetch 发送数据
        // 这里我们发送给 /api/crypto/analyze，看看逆向服务能否识别出什么
        const response = await fetch(`${REVERSE_SERVICE_URL}/api/crypto/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: postData.substring(0, 1000) }) // 截取前 1000 字符
        });

        if (response.ok) {
            const result = await response.json();
            // 打印逆向服务的分析结果
            if (result.cryptoTypes && result.cryptoTypes.length > 0) {
                console.log('🔐 逆向服务发现加密模式:', result.cryptoTypes.map(t => t.name).join(', '));
            } else {
                console.log('📄 逆向服务分析完成 (未发现明显加密特征)');
            }
        }
    } catch (err) {
        console.error('❌ 连接逆向服务失败:', err.message);
    }
}

/**
 * 下载文件流
 */
async function downloadVideo(url, filename) {
    try {
        const response = await fetch(url);
        const buffer = await response.arrayBuffer();
        writeFileSync(filename, Buffer.from(buffer));
        console.log(`💾 文件已保存: ${filename}`);
    } catch (err) {
        console.error('❌ 下载失败:', err.message);
    }
}

await crawler.run([TARGET_URL]);
console.log('\n🎉 任务结束！');
