package com.javaspider.core;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Logger;

/**
 * robots.txt 解析和遵守模块
 */
public class RobotsChecker {
    private static final Logger logger = Logger.getLogger(RobotsChecker.class.getName());
    
    private final String userAgent;
    private final long cacheTimeoutMs;
    private final Map<String, RobotsCacheEntry> cache = new ConcurrentHashMap<>();
    private volatile boolean respectRobots = true;
    
    private static class RobotsCacheEntry {
        final Map<String, List<String>> rules; // userAgent -> [disallowed paths]
        final double crawlDelay;
        final long timestamp;
        
        RobotsCacheEntry(Map<String, List<String>> rules, double crawlDelay) {
            this.rules = rules;
            this.crawlDelay = crawlDelay;
            this.timestamp = System.currentTimeMillis();
        }
    }
    
    public RobotsChecker() {
        this("*", 3600_000L);
    }
    
    public RobotsChecker(String userAgent, long cacheTimeoutMs) {
        this.userAgent = userAgent;
        this.cacheTimeoutMs = cacheTimeoutMs;
    }
    
    public void setRespectRobots(boolean respect) {
        this.respectRobots = respect;
    }
    
    /**
     * 检查 URL 是否允许爬取
     */
    public synchronized boolean isAllowed(String urlStr, String... userAgentOverride) {
        if (!respectRobots) return true;
        
        try {
            URL url = new URL(urlStr);
            String domain = url.getProtocol() + "://" + url.getHost();
            String path = url.getPath();
            String ua = userAgentOverride.length > 0 ? userAgentOverride[0] : userAgent;
            
            RobotsCacheEntry entry = getParser(domain);
            if (entry == null) return true; // 无法获取,默认允许
            
            List<String> disallowed = entry.rules.getOrDefault(ua, Collections.emptyList());
            // 也检查 *
            if (ua != null && !ua.equals("*")) {
                disallowed = new ArrayList<>(disallowed);
                disallowed.addAll(entry.rules.getOrDefault("*", Collections.emptyList()));
            }
            
            for (String disallowedPath : disallowed) {
                if (path.equals(disallowedPath) || path.startsWith(disallowedPath)) {
                    logger.fine("robots.txt disallowed: " + urlStr + " (UA: " + ua + ")");
                    return false;
                }
            }
            return true;
        } catch (Exception e) {
            logger.warning("robots.txt check failed for " + urlStr + ": " + e.getMessage());
            return true; // 检查失败,默认允许
        }
    }
    
    /**
     * 获取爬取延迟(秒)
     */
    public double getCrawlDelay(String urlStr) {
        try {
            URL url = new URL(urlStr);
            String domain = url.getProtocol() + "://" + url.getHost();
            RobotsCacheEntry entry = getParser(domain);
            return entry != null ? entry.crawlDelay : 0;
        } catch (Exception e) {
            return 0;
        }
    }
    
    private synchronized RobotsCacheEntry getParser(String domain) {
        RobotsCacheEntry entry = cache.get(domain);
        if (entry != null && (System.currentTimeMillis() - entry.timestamp) < cacheTimeoutMs) {
            return entry;
        }
        
        // 加载 robots.txt
        entry = loadRobotsTxt(domain);
        cache.put(domain, entry);
        return entry;
    }
    
    private RobotsCacheEntry loadRobotsTxt(String domain) {
        Map<String, List<String>> rules = new HashMap<>();
        double crawlDelay = 0;
        
        try {
            URL url = new URL(domain + "/robots.txt");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setConnectTimeout(5000);
            conn.setReadTimeout(10000);
            conn.setRequestMethod("GET");
            
            if (conn.getResponseCode() == 200) {
                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                String line;
                String currentUserAgent = null;
                List<String> currentDisallowed = new ArrayList<>();
                
                while ((line = reader.readLine()) != null) {
                    line = line.trim();
                    if (line.isEmpty() || line.startsWith("#")) continue;
                    
                    if (line.toLowerCase().startsWith("user-agent:")) {
                        // 保存之前的规则
                        if (currentUserAgent != null) {
                            rules.put(currentUserAgent, new ArrayList<>(currentDisallowed));
                        }
                        currentUserAgent = line.substring(11).trim().toLowerCase();
                        currentDisallowed.clear();
                    } else if (line.toLowerCase().startsWith("disallow:")) {
                        String path = line.substring(9).trim();
                        if (!path.isEmpty()) {
                            currentDisallowed.add(path);
                        }
                    } else if (line.toLowerCase().startsWith("crawl-delay:")) {
                        try {
                            crawlDelay = Double.parseDouble(line.substring(12).trim());
                        } catch (NumberFormatException e) {
                            // ignore
                        }
                    }
                }
                
                // 保存最后一个 user-agent 的规则
                if (currentUserAgent != null) {
                    rules.put(currentUserAgent, new ArrayList<>(currentDisallowed));
                }
                
                reader.close();
            }
            conn.disconnect();
            logger.info("Loaded robots.txt from " + domain);
        } catch (Exception e) {
            logger.warning("Failed to load robots.txt from " + domain + ": " + e.getMessage());
        }
        
        return new RobotsCacheEntry(rules, crawlDelay);
    }
    
    public void clearCache() {
        cache.clear();
    }
}
