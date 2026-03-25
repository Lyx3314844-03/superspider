package com.javaspider.processor;

import com.javaspider.core.Page;

/**
 * 基础页面处理器
 */
public abstract class BasePageProcessor implements PageProcessor {
    @Override
    public abstract void process(Page page);
}
