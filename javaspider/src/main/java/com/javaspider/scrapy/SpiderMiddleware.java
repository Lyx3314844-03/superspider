package com.javaspider.scrapy;

import java.util.List;

public interface SpiderMiddleware {
    List<Object> processSpiderOutput(Spider.Response response, List<Object> result, Spider spider);
}
