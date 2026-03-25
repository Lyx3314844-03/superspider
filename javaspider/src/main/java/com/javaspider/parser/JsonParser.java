package com.javaspider.parser;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.stream.JsonReader;

import java.io.StringReader;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * JSON 解析器
 * 支持 JSONPath 风格的查询
 */
public class JsonParser {
    private final String json;
    private final JsonElement root;
    private final Gson gson;

    public JsonParser(String json) {
        this.json = json;
        this.gson = new Gson();
        try {
            this.root = com.google.gson.JsonParser.parseString(json);
        } catch (Exception e) {
            throw new IllegalArgumentException("Invalid JSON", e);
        }
    }

    public JsonParser(JsonElement root) {
        this.root = root;
        this.json = root.toString();
        this.gson = new Gson();
    }

    /**
     * 解析 JSON 字符串（静态方法）
     */
    public static JsonElement parseJson(String json) {
        return com.google.gson.JsonParser.parseString(json);
    }

    /**
     * 获取 JSONPath 对应的值
     */
    public Object get(String jsonPath) {
        if (jsonPath == null || jsonPath.isEmpty()) {
            return root;
        }

        // 移除开头的 $
        if (jsonPath.startsWith("$")) {
            jsonPath = jsonPath.substring(1);
        }

        // 分割路径
        String[] parts = splitPath(jsonPath);
        JsonElement current = root;

        for (String part : parts) {
            if (current == null) {
                return null;
            }

            if (part.isEmpty()) {
                continue;
            }

            // 数组索引
            if (part.startsWith("[") && part.endsWith("]")) {
                String indexStr = part.substring(1, part.length() - 1);
                if (current.isJsonArray()) {
                    JsonArray array = current.getAsJsonArray();
                    if (indexStr.equals("*")) {
                        // 返回所有元素
                        List<Object> results = new ArrayList<>();
                        for (JsonElement element : array) {
                            results.add(jsonElementToObject(element));
                        }
                        return results;
                    } else {
                        try {
                            int index = Integer.parseInt(indexStr);
                            if (index >= 0 && index < array.size()) {
                                current = array.get(index);
                            } else {
                                return null;
                            }
                        } catch (NumberFormatException e) {
                            return null;
                        }
                    }
                } else {
                    return null;
                }
            }
            // 对象属性
            else if (current.isJsonObject()) {
                JsonObject object = current.getAsJsonObject();
                current = object.get(part);
            } else {
                return null;
            }
        }

        return jsonElementToObject(current);
    }

    /**
     * 获取字符串值
     */
    public String getAsString(String jsonPath) {
        Object value = get(jsonPath);
        return value != null ? value.toString() : null;
    }

    /**
     * 获取整数值
     */
    public Integer getAsInt(String jsonPath) {
        Object value = get(jsonPath);
        if (value instanceof Number) {
            return ((Number) value).intValue();
        }
        if (value instanceof String) {
            try {
                return Integer.parseInt((String) value);
            } catch (NumberFormatException e) {
                return null;
            }
        }
        return null;
    }

    /**
     * 获取长整数值
     */
    public Long getAsLong(String jsonPath) {
        Object value = get(jsonPath);
        if (value instanceof Number) {
            return ((Number) value).longValue();
        }
        if (value instanceof String) {
            try {
                return Long.parseLong((String) value);
            } catch (NumberFormatException e) {
                return null;
            }
        }
        return null;
    }

    /**
     * 获取浮点数值
     */
    public Double getAsDouble(String jsonPath) {
        Object value = get(jsonPath);
        if (value instanceof Number) {
            return ((Number) value).doubleValue();
        }
        if (value instanceof String) {
            try {
                return Double.parseDouble((String) value);
            } catch (NumberFormatException e) {
                return null;
            }
        }
        return null;
    }

    /**
     * 获取布尔值
     */
    public Boolean getAsBoolean(String jsonPath) {
        Object value = get(jsonPath);
        if (value instanceof Boolean) {
            return (Boolean) value;
        }
        if (value instanceof String) {
            return Boolean.parseBoolean((String) value);
        }
        return null;
    }

    /**
     * 获取对象
     */
    @SuppressWarnings("unchecked")
    public <T> T getAsObject(String jsonPath) {
        Object value = get(jsonPath);
        if (value instanceof Map) {
            return (T) value;
        }
        return null;
    }

    /**
     * 获取数组
     */
    @SuppressWarnings("unchecked")
    public <T> List<T> getAsList(String jsonPath) {
        Object value = get(jsonPath);
        if (value instanceof List) {
            return (List<T>) value;
        }
        return null;
    }

    /**
     * 获取所有键
     */
    public List<String> keys() {
        if (root.isJsonObject()) {
            JsonObject object = root.getAsJsonObject();
            return new ArrayList<>(object.keySet());
        }
        return new ArrayList<>();
    }

    /**
     * 检查是否包含指定键
     */
    public boolean has(String key) {
        if (root.isJsonObject()) {
            JsonObject object = root.getAsJsonObject();
            return object.has(key);
        }
        return false;
    }

    /**
     * 检查是否为数组
     */
    public boolean isArray() {
        return root.isJsonArray();
    }

    /**
     * 检查是否为对象
     */
    public boolean isObject() {
        return root.isJsonObject();
    }

    /**
     * 获取数组长度
     */
    public int size() {
        if (root.isJsonArray()) {
            return root.getAsJsonArray().size();
        }
        return 0;
    }

    /**
     * 转换为 Map
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> toMap() {
        return gson.fromJson(json, Map.class);
    }

    /**
     * 转换为 List
     */
    @SuppressWarnings("unchecked")
    public List<Object> toList() {
        return gson.fromJson(json, List.class);
    }

    /**
     * 转换为指定类型的对象
     */
    public <T> T toObject(Class<T> clazz) {
        return gson.fromJson(json, clazz);
    }

    /**
     * 获取原始 JSON 字符串
     */
    public String getJson() {
        return json;
    }

    /**
     * 获取根元素
     */
    public JsonElement getRoot() {
        return root;
    }

    /**
     * 分割 JSONPath
     */
    private String[] splitPath(String jsonPath) {
        List<String> parts = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean inBracket = false;

        for (int i = 0; i < jsonPath.length(); i++) {
            char c = jsonPath.charAt(i);

            if (c == '.') {
                if (current.length() > 0) {
                    parts.add(current.toString());
                    current.setLength(0);
                }
            } else if (c == '[') {
                if (current.length() > 0) {
                    parts.add(current.toString());
                    current.setLength(0);
                }
                inBracket = true;
                current.append(c);
            } else if (c == ']') {
                current.append(c);
                parts.add(current.toString());
                current.setLength(0);
                inBracket = false;
            } else {
                current.append(c);
            }
        }

        if (current.length() > 0) {
            parts.add(current.toString());
        }

        return parts.toArray(new String[0]);
    }

    /**
     * JsonElement 转 Object
     */
    private Object jsonElementToObject(JsonElement element) {
        if (element == null || element.isJsonNull()) {
            return null;
        } else if (element.isJsonPrimitive()) {
            if (element.getAsJsonPrimitive().isBoolean()) {
                return element.getAsBoolean();
            } else if (element.getAsJsonPrimitive().isNumber()) {
                Number number = element.getAsNumber();
                if (number instanceof Double || number instanceof Float) {
                    return number.doubleValue();
                } else {
                    return number.longValue();
                }
            } else {
                return element.getAsString();
            }
        } else if (element.isJsonObject()) {
            return gson.fromJson(element, Map.class);
        } else if (element.isJsonArray()) {
            List<Object> list = new ArrayList<>();
            for (JsonElement e : element.getAsJsonArray()) {
                list.add(jsonElementToObject(e));
            }
            return list;
        }
        return null;
    }

    /**
     * 从对象创建 JsonParser
     */
    public static JsonParser fromObject(Object object) {
        Gson gson = new Gson();
        String json = gson.toJson(object);
        return new JsonParser(json);
    }

    /**
     * 从 Map 创建 JsonParser
     */
    public static JsonParser fromMap(Map<?, ?> map) {
        Gson gson = new Gson();
        String json = gson.toJson(map);
        return new JsonParser(json);
    }

    /**
     * 从 List 创建 JsonParser
     */
    public static JsonParser fromList(List<?> list) {
        Gson gson = new Gson();
        String json = gson.toJson(list);
        return new JsonParser(json);
    }
}
