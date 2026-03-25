package com.javaspider.selector;

import java.util.List;

/**
 * Selector - 选择器接口
 * 
 * @author Lan
 * @version 2.0.0
 * @since 2026-03-20
 */
public interface Selector {
    
    /**
     * 选择单个结果
     * @param text 文本
     * @return 结果
     */
    String select(String text);
    
    /**
     * 选择多个结果
     * @param text 文本
     * @return 结果列表
     */
    List<String> selectAll(String text);
}
