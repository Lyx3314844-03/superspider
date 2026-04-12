package com.javaspider.ai;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * 将 AI 返回值按 JSON Schema 的核心类型约束做最小归一化。
 */
public final class SchemaNormalizer {
    private SchemaNormalizer() {
    }

    public static Map<String, Object> normalizeObject(
        Map<String, Object> schema,
        Map<String, Object> primary,
        Map<String, Object> fallback
    ) {
        Map<String, Object> normalized = new LinkedHashMap<>();
        Object propertiesNode = schema.get("properties");
        if (!(propertiesNode instanceof Map<?, ?> rawProperties)) {
            if (primary != null && !primary.isEmpty()) {
                normalized.putAll(primary);
            } else if (fallback != null && !fallback.isEmpty()) {
                normalized.putAll(fallback);
            }
            return normalized;
        }

        List<String> required = stringList(schema.get("required"));
        Map<String, Object> primaryValues = primary == null ? Map.of() : primary;
        Map<String, Object> fallbackValues = fallback == null ? Map.of() : fallback;

        for (Map.Entry<?, ?> entry : rawProperties.entrySet()) {
            if (!(entry.getKey() instanceof String key)) {
                continue;
            }

            Map<String, Object> propertySchema = mapValue(entry.getValue());
            Object value = normalizeValue(
                propertySchema,
                primaryValues.get(key),
                fallbackValues.get(key)
            );

            if (value != null || required.contains(key) || propertySchema.containsKey("default")) {
                normalized.put(key, value);
            }
        }

        for (Map.Entry<String, Object> entry : primaryValues.entrySet()) {
            normalized.putIfAbsent(entry.getKey(), entry.getValue());
        }
        return normalized;
    }

    public static Object normalizeValue(Map<String, Object> schema, Object primary, Object fallback) {
        if (schema == null || schema.isEmpty()) {
            return firstPresent(primary, fallback, null);
        }

        Object defaultValue = schema.get("default");
        String type = stringValue(schema.get("type"));
        if (type.isBlank()) {
            return firstPresent(primary, fallback, defaultValue);
        }

        return switch (type) {
            case "object" -> normalizeNestedObject(schema, primary, fallback, defaultValue);
            case "array" -> normalizeArray(schema, primary, fallback, defaultValue);
            case "string" -> normalizeString(primary, fallback, defaultValue);
            case "number" -> normalizeNumber(primary, fallback, defaultValue, false);
            case "integer" -> normalizeNumber(primary, fallback, defaultValue, true);
            case "boolean" -> normalizeBoolean(primary, fallback, defaultValue);
            default -> firstPresent(primary, fallback, defaultValue);
        };
    }

    private static Object normalizeNestedObject(
        Map<String, Object> schema,
        Object primary,
        Object fallback,
        Object defaultValue
    ) {
        Map<String, Object> primaryMap = mapValue(primary);
        Map<String, Object> fallbackMap = mapValue(fallback);
        Map<String, Object> defaultMap = mapValue(defaultValue);

        if (primaryMap.isEmpty() && fallbackMap.isEmpty() && defaultMap.isEmpty()) {
            return null;
        }

        Map<String, Object> mergedFallback = new LinkedHashMap<>(defaultMap);
        mergedFallback.putAll(fallbackMap);
        return normalizeObject(schema, primaryMap, mergedFallback);
    }

    private static Object normalizeArray(
        Map<String, Object> schema,
        Object primary,
        Object fallback,
        Object defaultValue
    ) {
        List<Object> source = listValue(primary);
        if (source == null) {
            source = listValue(fallback);
        }
        if (source == null) {
            source = listValue(defaultValue);
        }
        if (source == null) {
            return null;
        }

        Map<String, Object> itemSchema = mapValue(schema.get("items"));
        List<Object> normalized = new ArrayList<>();
        for (Object item : source) {
            Object value = itemSchema.isEmpty() ? item : normalizeValue(itemSchema, item, null);
            if (value != null) {
                normalized.add(value);
            }
        }
        return normalized;
    }

    private static String normalizeString(Object primary, Object fallback, Object defaultValue) {
        for (Object candidate : ordered(primary, fallback, defaultValue)) {
            if (candidate == null) {
                continue;
            }
            if (candidate instanceof String text) {
                return text;
            }
            if (candidate instanceof Number || candidate instanceof Boolean) {
                return String.valueOf(candidate);
            }
            if (candidate instanceof List<?> list && !list.isEmpty()) {
                String nested = normalizeString(list.get(0), null, null);
                if (nested != null) {
                    return nested;
                }
            }
        }
        return null;
    }

    private static Object normalizeNumber(Object primary, Object fallback, Object defaultValue, boolean integerOnly) {
        for (Object candidate : ordered(primary, fallback, defaultValue)) {
            Number value = numberValue(candidate, integerOnly);
            if (value != null) {
                return integerOnly ? value.longValue() : value.doubleValue();
            }
        }
        return null;
    }

    private static Number numberValue(Object candidate, boolean integerOnly) {
        if (candidate == null) {
            return null;
        }
        if (candidate instanceof Number number) {
            return integerOnly ? number.longValue() : number.doubleValue();
        }
        if (candidate instanceof String text) {
            try {
                return integerOnly ? Long.parseLong(text.trim()) : Double.parseDouble(text.trim());
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        if (candidate instanceof List<?> list && !list.isEmpty()) {
            return numberValue(list.get(0), integerOnly);
        }
        return null;
    }

    private static Boolean normalizeBoolean(Object primary, Object fallback, Object defaultValue) {
        for (Object candidate : ordered(primary, fallback, defaultValue)) {
            Boolean value = booleanValue(candidate);
            if (value != null) {
                return value;
            }
        }
        return null;
    }

    private static Boolean booleanValue(Object candidate) {
        if (candidate == null) {
            return null;
        }
        if (candidate instanceof Boolean value) {
            return value;
        }
        if (candidate instanceof Number number) {
            return number.intValue() != 0;
        }
        if (candidate instanceof String text) {
            String normalized = text.trim().toLowerCase(Locale.ROOT);
            if (List.of("true", "1", "yes", "y").contains(normalized)) {
                return true;
            }
            if (List.of("false", "0", "no", "n").contains(normalized)) {
                return false;
            }
            return null;
        }
        if (candidate instanceof List<?> list && !list.isEmpty()) {
            return booleanValue(list.get(0));
        }
        return null;
    }

    private static List<Object> listValue(Object candidate) {
        if (candidate == null) {
            return null;
        }
        if (candidate instanceof List<?> list) {
            return new ArrayList<>(list);
        }
        if (candidate instanceof String || candidate instanceof Number || candidate instanceof Boolean) {
            return new ArrayList<>(List.of(candidate));
        }
        return null;
    }

    private static Map<String, Object> mapValue(Object candidate) {
        if (!(candidate instanceof Map<?, ?> rawMap)) {
            return Map.of();
        }

        Map<String, Object> normalized = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : rawMap.entrySet()) {
            if (entry.getKey() instanceof String key) {
                normalized.put(key, entry.getValue());
            }
        }
        return normalized;
    }

    private static List<String> stringList(Object value) {
        if (!(value instanceof List<?> list)) {
            return List.of();
        }

        List<String> normalized = new ArrayList<>();
        for (Object item : list) {
            if (item instanceof String text && !text.isBlank()) {
                normalized.add(text);
            }
        }
        return normalized;
    }

    private static String stringValue(Object value) {
        return value instanceof String text ? text : "";
    }

    private static Object firstPresent(Object primary, Object fallback, Object defaultValue) {
        if (primary != null) {
            return primary;
        }
        if (fallback != null) {
            return fallback;
        }
        return defaultValue;
    }

    private static List<Object> ordered(Object primary, Object fallback, Object defaultValue) {
        List<Object> values = new ArrayList<>(3);
        values.add(primary);
        values.add(fallback);
        values.add(defaultValue);
        return values;
    }
}
