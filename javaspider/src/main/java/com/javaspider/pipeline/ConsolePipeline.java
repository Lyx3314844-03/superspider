package com.javaspider.pipeline;

import com.javaspider.core.ResultItems;
import com.javaspider.core.Spider;
import com.javaspider.util.SpiderExceptionHandler;

/**
 * 控制台管道
 */
public class ConsolePipeline implements Pipeline {

    @Override
    public void process(ResultItems resultItems, Spider spider) {
        try {
            System.out.println("========== Spider Result ==========");
            System.out.println("Data:");

            if (resultItems != null) {
                for (String key : resultItems.getAll().keySet()) {
                    Object value = resultItems.get(key);
                    System.out.println("  " + key + ": " + (value != null ? value : "null"));
                }
            } else {
                System.out.println("  No data");
            }

            System.out.println("===================================\n");
        } catch (Exception e) {
            SpiderExceptionHandler.handle(e, "ConsolePipeline");
        }
    }

    @Override
    public void close() {
        // 无需关闭
    }
}
