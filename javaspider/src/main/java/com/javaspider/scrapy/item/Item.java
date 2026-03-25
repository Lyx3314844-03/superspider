package com.javaspider.scrapy.item;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

public class Item {
    private final LinkedHashMap<String, Object> data = new LinkedHashMap<>();

    public Item set(String key, Object value) {
        data.put(key, value);
        return this;
    }

    public Object get(String key) {
        return data.get(key);
    }

    public <T> T get(String key, T defaultValue) {
        Object value = data.get(key);
        if (value == null) {
            return defaultValue;
        }
        @SuppressWarnings("unchecked")
        T castValue = (T) value;
        return castValue;
    }

    public <T> T get(String key, Class<T> type) {
        Object value = data.get(key);
        if (value == null) {
            return null;
        }
        return type.cast(value);
    }

    public boolean hasField(String key) {
        return data.containsKey(key);
    }

    public Set<String> getFields() {
        return data.keySet();
    }

    public Object remove(String key) {
        return data.remove(key);
    }

    public void clear() {
        data.clear();
    }

    public boolean isEmpty() {
        return data.isEmpty();
    }

    public int size() {
        return data.size();
    }

    public void merge(Item other) {
        if (other != null) {
            data.putAll(other.data);
        }
    }

    public Map<String, Object> toMap() {
        return new LinkedHashMap<>(data);
    }

    public static Item fromMap(Map<String, Object> map) {
        Item item = new Item();
        if (map != null) {
            item.data.putAll(map);
        }
        return item;
    }

    @Override
    public String toString() {
        return data.toString();
    }
}
