package com.javaspider.contracts;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javaspider.core.Request;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

public final class RequestFingerprint {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private final String algorithm;
    private final String value;

    public RequestFingerprint(String algorithm, String value) {
        this.algorithm = algorithm;
        this.value = value;
    }

    public String getAlgorithm() {
        return algorithm;
    }

    public String getValue() {
        return value;
    }

    public static RequestFingerprint fromRequest(Request request) {
        try {
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("url", request.getUrl());
            payload.put("method", Objects.toString(request.getMethod(), "GET").toUpperCase());
            payload.put("headers", new LinkedHashMap<>(request.getHeaders()));
            payload.put("body", request.getBody() == null ? "" : new String(request.getBody(), StandardCharsets.UTF_8));
            payload.put("meta", new LinkedHashMap<>(request.getMeta()));
            payload.put("priority", request.getPriority());

            byte[] digest = MessageDigest.getInstance("SHA-256").digest(
                OBJECT_MAPPER.writeValueAsBytes(payload)
            );
            StringBuilder builder = new StringBuilder();
            for (byte value : digest) {
                builder.append(String.format("%02x", value));
            }
            return new RequestFingerprint("sha256", builder.toString());
        } catch (Exception exception) {
            throw new RuntimeException("failed to fingerprint request", exception);
        }
    }
}
