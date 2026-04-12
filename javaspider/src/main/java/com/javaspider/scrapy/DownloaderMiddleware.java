package com.javaspider.scrapy;

public interface DownloaderMiddleware {
    Spider.Request processRequest(Spider.Request request, Spider spider);

    Spider.Response processResponse(Spider.Response response, Spider spider);
}
