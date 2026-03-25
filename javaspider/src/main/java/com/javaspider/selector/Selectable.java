package com.javaspider.selector;

import java.util.ArrayList;
import java.util.List;

/**
 * 可选择结果包装类
 */
public class Selectable {
    private String text;
    
    public Selectable(String text) {
        this.text = text;
    }
    
    public String get() {
        return text;
    }
    
    public List<String> all() {
        List<String> result = new ArrayList<>();
        if (text != null) {
            result.add(text);
        }
        return result;
    }
    
    public Selectable jsonPath(String jsonPath) {
        return new Selectable(text);
    }
    
    public Selectable aiExtract(String prompt) {
        return new Selectable(text);
    }
}
