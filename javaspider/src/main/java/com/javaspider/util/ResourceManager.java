package com.javaspider.util;

import com.javaspider.antibot.ProxyPool;
import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * 资源管理器
 * 
 * 功能:
 * 1. 统一管理所有可关闭资源
 * 2. 注册 JVM 关闭钩子
 * 3. 确保应用退出时资源正确释放
 * 
 * @author Lan
 * @version 1.0.0
 */
@Slf4j
public class ResourceManager implements AutoCloseable {

    private static final ResourceManager instance = new ResourceManager();
    
    private final List<AutoCloseable> resources = new ArrayList<>();
    private final AtomicBoolean shutdownHookRegistered = new AtomicBoolean(false);
    private final AtomicBoolean closing = new AtomicBoolean(false);

    // 包私有构造函数,允许测试访问
    ResourceManager() {
    }

    /**
     * 获取单例实例
     */
    public static ResourceManager getInstance() {
        return instance;
    }

    /**
     * 注册资源
     * 
     * @param resource 可关闭资源
     * @return 资源管理器实例（支持链式调用）
     */
    public synchronized ResourceManager register(AutoCloseable resource) {
        if (resource != null) {
            resources.add(resource);
            log.debug("注册资源：{}", resource.getClass().getSimpleName());
        }
        return this;
    }

    /**
     * 注册 ProxyPool 资源
     * 
     * @param proxyPool 代理池
     * @return 资源管理器实例
     */
    public ResourceManager registerProxyPool(ProxyPool proxyPool) {
        return register(proxyPool);
    }

    /**
     * 注册关闭钩子
     * 确保 JVM 退出时自动关闭所有资源
     */
    public void registerShutdownHook() {
        if (shutdownHookRegistered.compareAndSet(false, true)) {
            Runtime.getRuntime().addShutdownHook(new Thread(this::close, "ResourceManager-Shutdown"));
            log.info("已注册 JVM 关闭钩子");
        }
    }

    /**
     * 关闭所有资源
     */
    @Override
    public void close() {
        if (closing.compareAndSet(false, true)) {
            try {
                log.info("正在关闭 {} 个资源...", resources.size());
                
                // 倒序关闭资源
                for (int i = resources.size() - 1; i >= 0; i--) {
                    AutoCloseable resource = resources.get(i);
                    try {
                        log.debug("关闭资源：{} ({}/{})", 
                            resource.getClass().getSimpleName(), 
                            resources.size() - i, 
                            resources.size());
                        resource.close();
                    } catch (Exception e) {
                        log.error("关闭资源失败：{}", resource.getClass().getSimpleName(), e);
                    }
                }
                
                resources.clear();
                log.info("所有资源已关闭");
            } finally {
                closing.set(false);
            }
        }
    }

    /**
     * 获取已注册资源数量
     */
    public int getResourceCount() {
        return resources.size();
    }

    /**
     * 是否正在关闭
     */
    public boolean isClosing() {
        return closing.get();
    }

    /**
     * 移除资源
     * 
     * @param resource 要移除的资源
     */
    public synchronized void unregister(AutoCloseable resource) {
        resources.remove(resource);
        log.debug("移除资源：{}", resource.getClass().getSimpleName());
    }
}
