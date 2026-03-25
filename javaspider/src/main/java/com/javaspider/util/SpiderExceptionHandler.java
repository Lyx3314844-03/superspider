package com.javaspider.util;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.PrintWriter;
import java.io.StringWriter;

/**
 * 蜘蛛异常处理器
 */
public class SpiderExceptionHandler {
    
    private static final Logger logger = LoggerFactory.getLogger(SpiderExceptionHandler.class);
    
    /**
     * 处理异常
     */
    public static void handle(Exception e, String context) {
        logger.error("Error in {}: {}", context, e.getMessage(), e);
    }
    
    /**
     * 处理异常并返回友好消息
     */
    public static String handleAndGetMessage(Exception e, String context) {
        String message = String.format("Error in %s: %s", context, e.getMessage());
        logger.error(message, e);
        return message;
    }
    
    /**
     * 获取完整的堆栈跟踪
     */
    public static String getStackTrace(Throwable throwable) {
        StringWriter sw = new StringWriter();
        PrintWriter pw = new PrintWriter(sw);
        throwable.printStackTrace(pw);
        return sw.toString();
    }
    
    /**
     * 安全执行，捕获异常
     */
    public interface SafeRunnable {
        void run() throws Exception;
    }
    
    public static void safeRun(SafeRunnable runnable, String context) {
        try {
            runnable.run();
        } catch (Exception e) {
            handle(e, context);
        }
    }
    
    /**
     * 安全执行，带重试
     */
    public static void safeRunWithRetry(SafeRunnable runnable, String context, int maxRetries) {
        int attempts = 0;
        while (attempts < maxRetries) {
            try {
                runnable.run();
                return;
            } catch (Exception e) {
                attempts++;
                if (attempts >= maxRetries) {
                    handle(e, context + " (after " + maxRetries + " attempts)");
                } else {
                    logger.warn("Attempt {} failed: {}", attempts, e.getMessage());
                    try {
                        Thread.sleep(1000 * attempts);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                    }
                }
            }
        }
    }
}
