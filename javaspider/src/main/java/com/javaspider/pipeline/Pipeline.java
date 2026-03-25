package com.javaspider.pipeline;

import com.javaspider.core.ResultItems;
import com.javaspider.core.Spider;

/**
 * 数据管道接口
 */
public interface Pipeline {
    void process(ResultItems resultItems, Spider spider);
    void close();
}
