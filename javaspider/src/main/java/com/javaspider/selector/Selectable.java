package com.javaspider.selector;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * 可选择结果包装类
 */
public class Selectable {
    private final String text;
    private final List<String> values;
    
    public Selectable(String text) {
        this(text == null ? Collections.emptyList() : List.of(text));
    }

    public Selectable(List<String> values) {
        this.values = values == null ? Collections.emptyList() : new ArrayList<>(values);
        this.text = this.values.isEmpty() ? null : this.values.get(0);
    }
    
    public String get() {
        return text;
    }
    
    public List<String> all() {
        return new ArrayList<>(values);
    }
    
    public Selectable jsonPath(String jsonPath) {
        return new Selectable(values);
    }
    
    public Selectable aiExtract(String prompt) {
        return new Selectable(values);
    }
}
