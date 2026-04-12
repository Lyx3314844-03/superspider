package com.javaspider.session;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

public class SessionProfile {
    private final String sessionId;
    private final String accountId;
    private final String proxyGroup;
    private final String fingerprintPreset;
    private final Map<String, String> cookies;

    public SessionProfile(String sessionId, String accountId, String proxyGroup, String fingerprintPreset, Map<String, String> cookies) {
        this.sessionId = sessionId;
        this.accountId = accountId;
        this.proxyGroup = proxyGroup;
        this.fingerprintPreset = fingerprintPreset;
        this.cookies = cookies == null
            ? Collections.emptyMap()
            : Collections.unmodifiableMap(new LinkedHashMap<>(cookies));
    }

    public String getSessionId() {
        return sessionId;
    }

    public String getAccountId() {
        return accountId;
    }

    public String getProxyGroup() {
        return proxyGroup;
    }

    public String getFingerprintPreset() {
        return fingerprintPreset;
    }

    public Map<String, String> getCookies() {
        return cookies;
    }
}
