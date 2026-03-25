package com.javaspider.selector;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * RegexSelector - 正则表达式选择器
 * 
 * @author Lan
 * @version 2.0.0
 * @since 2026-03-20
 */
public class RegexSelector implements Selector {
    
    /**
     * 正则表达式
     */
    private final Pattern pattern;
    
    /**
     * 分组索引
     */
    private final int groupIndex;
    
    /**
     * 构造函数
     * @param regex 正则表达式
     */
    public RegexSelector(String regex) {
        this(regex, 0);
    }
    
    /**
     * 构造函数
     * @param regex 正则表达式
     * @param groupIndex 分组索引
     */
    public RegexSelector(String regex, int groupIndex) {
        this.pattern = Pattern.compile(regex, Pattern.DOTALL | Pattern.MULTILINE);
        this.groupIndex = groupIndex;
    }
    
    @Override
    public String select(String text) {
        if (text == null || text.isEmpty()) {
            return null;
        }
        
        Matcher matcher = pattern.matcher(text);
        if (matcher.find()) {
            return groupIndex == 0 ? matcher.group() : matcher.group(groupIndex);
        }
        
        return null;
    }
    
    @Override
    public List<String> selectAll(String text) {
        List<String> results = new ArrayList<>();
        
        if (text == null || text.isEmpty()) {
            return results;
        }
        
        Matcher matcher = pattern.matcher(text);
        while (matcher.find()) {
            String value = groupIndex == 0 ? matcher.group() : matcher.group(groupIndex);
            if (value != null && !value.isEmpty()) {
                results.add(value);
            }
        }
        
        return results;
    }
    
    /**
     * 创建 RegexSelector 实例
     * @param regex 正则表达式
     * @return RegexSelector 实例
     */
    public static RegexSelector of(String regex) {
        return new RegexSelector(regex);
    }
    
    /**
     * 创建 RegexSelector 实例 (带分组)
     * @param regex 正则表达式
     * @param group 分组索引
     * @return RegexSelector 实例
     */
    public static RegexSelector of(String regex, int group) {
        return new RegexSelector(regex, group);
    }
}
