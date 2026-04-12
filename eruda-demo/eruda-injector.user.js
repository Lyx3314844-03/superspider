// ==UserScript==
// @name         Eruda 注入神器 (爬虫逆向专用)
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  在任意网页右下角注入 Eruda 控制台，支持快捷键 F12 唤起
// @author       Spider Team
// @match        *://*/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // 配置 CDN 地址 (可以使用本地路径或 CDN)
    const ERUDA_URL = 'https://cdn.jsdelivr.net/npm/eruda';

    // 检查是否已经加载
    if (window.eruda) {
        console.log('Eruda 已存在');
        return;
    }

    // 动态加载 Eruda
    const script = document.createElement('script');
    script.src = ERUDA_URL;
    script.onload = function() {
        if (window.eruda) {
            // 初始化
            window.eruda.init();
            
            // 可以配置需要加载的插件，例如 Network, Elements, Console
            // window.eruda.add(new erudaNetwork());
            
            // 默认隐藏，等待 F12 唤醒
            window.eruda.hide();
            
            // 添加一个浮动按钮方便点击
            const btn = document.createElement('div');
            btn.innerHTML = '🐛 Eruda';
            btn.style.cssText = `
                position: fixed; bottom: 20px; right: 20px;
                background: #000; color: #fff; padding: 10px;
                border-radius: 50%; width: 40px; height: 40px;
                line-height: 40px; text-align: center; cursor: pointer;
                z-index: 999999; font-size: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            `;
            btn.onclick = function() {
                if (window.eruda._isShow) {
                    window.eruda.hide();
                } else {
                    window.eruda.show();
                }
            };
            document.body.appendChild(btn);
        }
    };
    document.head.appendChild(script);

    // 监听 F12 快捷键
    document.addEventListener('keydown', function(e) {
        if (e.key === 'F12' && window.eruda) {
            e.preventDefault(); // 阻止浏览器默认 DevTools
            if (window.eruda._isShow) {
                window.eruda.hide();
            } else {
                window.eruda.show();
            }
        }
    });

    console.log('%c Eruda Injector Loaded! ', 'background: #222; color: #bada55; font-size: 16px');
})();
