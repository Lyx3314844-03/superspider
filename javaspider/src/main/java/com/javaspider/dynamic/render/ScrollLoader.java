package com.javaspider.dynamic.render;

import com.javaspider.browser.BrowserManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;

/**
 * 滚动加载器
 * 支持无限滚动页面爬取
 * 
 * 特性:
 * - 自动滚动到底部
 * - 等待内容加载
 * - 检测滚动结束
 * - 增量内容提取
 */
public class ScrollLoader {
    private static final Logger logger = LoggerFactory.getLogger(ScrollLoader.class);
    
    // 默认配置
    private static final int DEFAULT_SCROLL_PAUSE = 1000; // 1 秒
    private static final int DEFAULT_MAX_SCROLLS = 50;
    private static final int DEFAULT_STABLE_THRESHOLD = 2; // 连续 2 次高度不变
    
    private final BrowserManager browser;
    private final JavaScriptExecutor jsExecutor;
    
    private final int scrollPause;
    private final int maxScrolls;
    private final int stableThreshold;
    
    private long lastHeight = 0;
    private int stableCount = 0;
    private final List<Long> scrollHistory = new ArrayList<>();
    
    /**
     * 构造函数
     */
    public ScrollLoader(BrowserManager browser) {
        this(browser, DEFAULT_SCROLL_PAUSE, DEFAULT_MAX_SCROLLS, DEFAULT_STABLE_THRESHOLD);
    }
    
    /**
     * 构造函数
     */
    public ScrollLoader(BrowserManager browser, int scrollPause, int maxScrolls, int stableThreshold) {
        this.browser = browser;
        this.jsExecutor = new JavaScriptExecutor(browser);
        this.scrollPause = scrollPause;
        this.maxScrolls = maxScrolls;
        this.stableThreshold = stableThreshold;
    }
    
    /**
     * 滚动到页面底部（无限滚动）
     * 
     * @return 滚动次数
     */
    public int scrollToBottom() {
        return scrollToBottom(scrollPause, maxScrolls, stableThreshold);
    }
    
    /**
     * 滚动到页面底部
     * 
     * @param scrollPause 滚动间隔 (ms)
     * @param maxScrolls 最大滚动次数
     * @param stableThreshold 稳定阈值（连续多少次高度不变）
     * @return 滚动次数
     */
    public int scrollToBottom(int scrollPause, int maxScrolls, int stableThreshold) {
        logger.info("Starting infinite scroll: pause={}ms, maxScrolls={}, stableThreshold={}",
                scrollPause, maxScrolls, stableThreshold);
        
        int scrollCount = 0;
        lastHeight = getPageHeight();
        stableCount = 0;
        scrollHistory.clear();
        
        while (scrollCount < maxScrolls) {
            // 滚动到底部
            jsExecutor.scrollToBottom();
            scrollCount++;
            
            logger.debug("Scroll {}/{} - Height: {}px", scrollCount, maxScrolls, lastHeight);
            scrollHistory.add(lastHeight);
            
            // 等待内容加载
            try {
                Thread.sleep(scrollPause);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
            
            // 检查新高度
            long newHeight = getPageHeight();
            
            if (newHeight == lastHeight) {
                stableCount++;
                logger.debug("Height unchanged (stable {}/{})", stableCount, stableThreshold);
                
                if (stableCount >= stableThreshold) {
                    logger.info("Scroll ended: page stable after {} scrolls", scrollCount);
                    break;
                }
            } else {
                stableCount = 0;
                lastHeight = newHeight;
            }
        }
        
        logger.info("Scroll completed: {} scrolls, final height: {}px", scrollCount, lastHeight);
        return scrollCount;
    }
    
    /**
     * 滚动到指定位置
     */
    public void scrollTo(int y) {
        String script = "window.scrollTo(0, " + y + ")";
        jsExecutor.execute(script);
        logger.debug("Scrolled to y={}", y);
    }
    
    /**
     * 滚动到元素
     */
    public void scrollToElement(String selector) {
        jsExecutor.scrollToElement(selector);
        logger.debug("Scrolled to element: {}", selector);
    }
    
    /**
     * 逐步滚动（模拟人工）
     */
    public void scrollStepByStep(int stepSize, int stepPause) {
        long currentScroll = 0;
        long maxScroll = getMaxScrollHeight();
        
        logger.info("Step scrolling: stepSize={}, maxScroll={}", stepSize, maxScroll);
        
        while (currentScroll < maxScroll) {
            currentScroll += stepSize;
            scrollTo((int) Math.min(currentScroll, maxScroll));
            
            try {
                Thread.sleep(stepPause);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
    }
    
    /**
     * 获取页面总高度
     */
    public long getPageHeight() {
        Object result = jsExecutor.execute(
            "return Math.max(" +
            "  document.body.scrollHeight, " +
            "  document.body.offsetHeight, " +
            "  document.documentElement.scrollHeight, " +
            "  document.documentElement.offsetHeight" +
            ")");
        
        return result != null ? ((Number) result).longValue() : 0;
    }
    
    /**
     * 获取可视区域高度
     */
    public long getViewportHeight() {
        Object result = jsExecutor.execute(
            "return window.innerHeight || document.documentElement.clientHeight");
        
        return result != null ? ((Number) result).longValue() : 0;
    }
    
    /**
     * 获取当前滚动位置
     */
    public long getCurrentScroll() {
        Object result = jsExecutor.execute(
            "return window.pageYOffset || document.documentElement.scrollTop");
        
        return result != null ? ((Number) result).longValue() : 0;
    }
    
    /**
     * 获取最大可滚动高度
     */
    public long getMaxScrollHeight() {
        return getPageHeight() - getViewportHeight();
    }
    
    /**
     * 检查是否已滚动到底部
     */
    public boolean isAtBottom() {
        long currentScroll = getCurrentScroll();
        long viewportHeight = getViewportHeight();
        long pageHeight = getPageHeight();
        
        // 允许 1px 误差
        return currentScroll + viewportHeight >= pageHeight - 1;
    }
    
    /**
     * 检查是否已滚动到顶部
     */
    public boolean isAtTop() {
        return getCurrentScroll() <= 1;
    }
    
    /**
     * 获取滚动进度（百分比）
     */
    public double getScrollProgress() {
        long maxScroll = getMaxScrollHeight();
        if (maxScroll <= 0) {
            return 100.0;
        }
        
        long current = getCurrentScroll();
        return (double) current / maxScroll * 100.0;
    }
    
    /**
     * 获取滚动历史
     */
    public List<Long> getScrollHistory() {
        return new ArrayList<>(scrollHistory);
    }
    
    /**
     * 获取滚动统计信息
     */
    public ScrollStats getStats() {
        return new ScrollStats(
            scrollHistory.size(),
            lastHeight,
            stableCount,
            getScrollProgress()
        );
    }
    
    /**
     * 重置状态
     */
    public void reset() {
        lastHeight = 0;
        stableCount = 0;
        scrollHistory.clear();
        scrollTo(0);
    }
    
    /**
     * 滚动统计信息
     */
    public static class ScrollStats {
        public final int scrollCount;
        public final long totalHeight;
        public final int stableCount;
        public final double progress;
        
        public ScrollStats(int scrollCount, long totalHeight, int stableCount, double progress) {
            this.scrollCount = scrollCount;
            this.totalHeight = totalHeight;
            this.stableCount = stableCount;
            this.progress = progress;
        }
        
        @Override
        public String toString() {
            return String.format("ScrollStats{scrolls=%d, height=%dpx, stable=%d, progress=%.1f%%}",
                    scrollCount, totalHeight, stableCount, progress);
        }
    }
}
