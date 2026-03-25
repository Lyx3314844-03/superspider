package com.javaspider.antibot;

import java.net.InetAddress;
import java.net.URL;
import java.util.Arrays;
import java.util.List;

/**
 * URL 安全验证工具
 * 防止 SSRF（服务端请求伪造）攻击
 * 
 * @see <a href="https://owasp.org/www-community/attacks/Server_Side_Request_Forgery">OWASP SSRF</a>
 */
public class UrlValidator {
    
    // 允许的域名白名单
    private static final List<String> ALLOWED_DOMAINS = Arrays.asList(
        "2captcha.com",
        "api.anti-captcha.com",
        "anti-captcha.com",
        "localhost",
        "127.0.0.1"
    );
    
    // 禁止的协议
    private static final List<String> BLOCKED_PROTOCOLS = Arrays.asList(
        "file", "ftp", "gopher", "dict", "ldap", "netdoc"
    );
    
    /**
     * 验证 URL 是否安全
     * @param urlString URL 字符串
     * @return 是否安全
     */
    public static boolean isValidUrl(String urlString) {
        if (urlString == null || urlString.isEmpty()) {
            return false;
        }
        
        try {
            URL url = new URL(urlString);
            String protocol = url.getProtocol();
            String host = url.getHost();
            
            // 检查协议是否被允许
            if (!isAllowedProtocol(protocol)) {
                return false;
            }
            
            // 检查域名白名单
            if (!isAllowedDomain(host)) {
                return false;
            }
            
            // 检查是否为内网地址
            if (isInternalHost(host)) {
                return false;
            }
            
            return true;
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * 检查协议是否允许
     */
    private static boolean isAllowedProtocol(String protocol) {
        if (protocol == null) {
            return false;
        }
        
        String lowerProtocol = protocol.toLowerCase();
        
        // 只允许 HTTP/HTTPS
        if (!"http".equals(lowerProtocol) && !"https".equals(lowerProtocol)) {
            return false;
        }
        
        // 检查是否在黑名单中
        return !BLOCKED_PROTOCOLS.contains(lowerProtocol);
    }
    
    /**
     * 检查域名是否在白名单中
     */
    private static boolean isAllowedDomain(String host) {
        if (host == null || host.isEmpty()) {
            return false;
        }
        
        String lowerHost = host.toLowerCase();
        
        for (String allowed : ALLOWED_DOMAINS) {
            if (lowerHost.equals(allowed) || lowerHost.endsWith("." + allowed)) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * 检查是否为内网地址
     */
    private static boolean isInternalHost(String host) {
        if (host == null || host.isEmpty()) {
            return true;
        }
        
        try {
            InetAddress[] addresses = InetAddress.getAllByName(host);
            for (InetAddress addr : addresses) {
                // 检查是否为私有 IP 地址
                if (isPrivateIp(addr)) {
                    return true;
                }
            }
            return false;
        } catch (Exception e) {
            // DNS 解析失败，保守处理为内网
            return true;
        }
    }
    
    /**
     * 检查 IP 地址是否为私有地址
     */
    private static boolean isPrivateIp(InetAddress address) {
        // 本地回环地址
        if (address.isLoopbackAddress()) {
            return true;
        }
        
        // 任意本地地址
        if (address.isAnyLocalAddress()) {
            return true;
        }
        
        // 链路本地地址
        if (address.isLinkLocalAddress()) {
            return true;
        }
        
        // 站点本地地址（私有地址）
        if (address.isSiteLocalAddress()) {
            return true;
        }
        
        // IPv4 私有地址段检查
        byte[] addrBytes = address.getAddress();
        if (addrBytes.length == 4) {
            // 10.0.0.0/8
            if (addrBytes[0] == 10) {
                return true;
            }
            // 172.16.0.0/12
            if (addrBytes[0] == (byte) 172 && (addrBytes[1] >= 16 && addrBytes[1] <= 31)) {
                return true;
            }
            // 192.168.0.0/16
            if (addrBytes[0] == (byte) 192 && addrBytes[1] == (byte) 168) {
                return true;
            }
            // 127.0.0.0/8
            if (addrBytes[0] == 127) {
                return true;
            }
            // 0.0.0.0
            if (addrBytes[0] == 0) {
                return true;
            }
        }
        
        // IPv6 唯一本地地址 (fc00::/7)
        if (addrBytes.length == 16) {
            if ((addrBytes[0] & (byte) 0xfe) == (byte) 0xfc) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * 验证并规范化 URL
     * @param urlString URL 字符串
     * @return 规范化的 URL
     * @throws SecurityException 如果 URL 不安全
     */
    public static String validateAndNormalize(String urlString) throws SecurityException {
        if (!isValidUrl(urlString)) {
            throw new SecurityException("Invalid or unsafe URL: " + urlString);
        }
        
        try {
            URL url = new URL(urlString);
            return url.toString();
        } catch (Exception e) {
            throw new SecurityException("Invalid URL format: " + urlString);
        }
    }
}
