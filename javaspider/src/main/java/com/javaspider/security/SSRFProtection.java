package com.javaspider.security;

import com.javaspider.antibot.UrlValidator;

import java.util.ArrayList;
import java.util.List;

/**
 * 显式 SSRF 防护入口，供下载器、事件回放、控制面统一复用。
 */
public final class SSRFProtection {
    private SSRFProtection() {
    }

    public static boolean isSafeUrl(String url) {
        return UrlValidator.isValidUrl(url);
    }

    public static String validate(String url) {
        return UrlValidator.validateAndNormalize(url);
    }

    public static List<String> filterSafeUrls(List<String> urls) {
        List<String> safeUrls = new ArrayList<>();
        for (String url : urls) {
            if (isSafeUrl(url)) {
                safeUrls.add(url);
            }
        }
        return safeUrls;
    }

    public static boolean validateRedirectChain(String initialUrl, List<String> redirects) {
        if (!isSafeUrl(initialUrl)) {
            return false;
        }
        for (String redirect : redirects) {
            if (!isSafeUrl(redirect)) {
                return false;
            }
        }
        return true;
    }
}
