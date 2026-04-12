package com.javaspider;

import java.util.*;
import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;

/**
 * JavaSpider 安全增强模块 - 请求加密、IP 白名单、访问令牌
 */
public class Security {
    
    // IP 白名单
    private static final Set<String> ipWhitelist = new HashSet<>();
    
    // 访问令牌
    private static final Map<String, Long> accessTokens = new HashMap<>();
    private static final long TOKEN_EXPIRY = 3600000; // 1小时
    
    // 加密密钥
    private static String encryptionKey = "default_key";
    
    // 初始化白名单
    static {
        // 可以从配置文件加载
        ipWhitelist.add("127.0.0.1");
        ipWhitelist.add("localhost");
    }
    
    /**
     * 检查 IP 是否在白名单中
     */
    public static boolean isIPAllowed(String ip) {
        return ipWhitelist.contains(ip) || ipWhitelist.contains("*");
    }
    
    /**
     * 添加 IP 到白名单
     */
    public static void addToWhitelist(String ip) {
        ipWhitelist.add(ip);
        System.out.println("✅ IP 已添加到白名单: " + ip);
    }
    
    /**
     * 从白名单移除 IP
     */
    public static void removeFromWhitelist(String ip) {
        ipWhitelist.remove(ip);
        System.out.println("✅ IP 已从白名单移除: " + ip);
    }
    
    /**
     * 生成访问令牌
     */
    public static String generateToken(String userId) {
        String token = UUID.randomUUID().toString();
        accessTokens.put(token, System.currentTimeMillis() + TOKEN_EXPIRY);
        return token;
    }
    
    /**
     * 验证访问令牌
     */
    public static boolean validateToken(String token) {
        Long expiry = accessTokens.get(token);
        if (expiry == null) {
            return false;
        }
        
        if (System.currentTimeMillis() > expiry) {
            accessTokens.remove(token);
            return false;
        }
        
        return true;
    }
    
    /**
     * 撤销访问令牌
     */
    public static void revokeToken(String token) {
        accessTokens.remove(token);
        System.out.println("✅ 令牌已撤销");
    }
    
    /**
     * MD5 加密
     */
    public static String md5(String input) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] hash = md.digest(input.getBytes(StandardCharsets.UTF_8));
            StringBuilder hexString = new StringBuilder();
            for (byte b : hash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) hexString.append('0');
                hexString.append(hex);
            }
            return hexString.toString();
        } catch (Exception e) {
            return "";
        }
    }
    
    /**
     * SHA-256 加密
     */
    public static String sha256(String input) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(input.getBytes(StandardCharsets.UTF_8));
            StringBuilder hexString = new StringBuilder();
            for (byte b : hash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) hexString.append('0');
                hexString.append(hex);
            }
            return hexString.toString();
        } catch (Exception e) {
            return "";
        }
    }
    
    /**
     * 设置加密密钥
     */
    public static void setEncryptionKey(String key) {
        encryptionKey = key;
    }
    
    /**
     * 简单的 XOR 加密
     */
    public static String encrypt(String data) {
        StringBuilder result = new StringBuilder();
        for (int i = 0; i < data.length(); i++) {
            result.append((char) (data.charAt(i) ^ encryptionKey.charAt(i % encryptionKey.length())));
        }
        return Base64.getEncoder().encodeToString(result.toString().getBytes());
    }
    
    /**
     * XOR 解密
     */
    public static String decrypt(String encryptedData) {
        try {
            byte[] decoded = Base64.getDecoder().decode(encryptedData);
            String data = new String(decoded);
            StringBuilder result = new StringBuilder();
            for (int i = 0; i < data.length(); i++) {
                result.append((char) (data.charAt(i) ^ encryptionKey.charAt(i % encryptionKey.length())));
            }
            return result.toString();
        } catch (Exception e) {
            return "解密失败";
        }
    }
    
    /**
     * 显示安全菜单
     */
    public static void showSecurityMenu() {
        System.out.println("\n🔒 安全增强功能:");
        System.out.println("  security whitelist add <ip>     - 添加 IP 到白名单");
        System.out.println("  security whitelist remove <ip>  - 从白名单移除 IP");
        System.out.println("  security token generate <user> - 生成访问令牌");
        System.out.println("  security token validate <token> - 验证令牌");
        System.out.println("  security encrypt <text>        - 加密文本");
        System.out.println("  security decrypt <text>        - 解密文本");
    }
}
