package com.javaspider.processor;

import com.javaspider.core.Page;

/**
 * 页面处理器接口
 */
public interface PageProcessor {
    void process(Page page);
    com.javaspider.core.Site getSite();
}
