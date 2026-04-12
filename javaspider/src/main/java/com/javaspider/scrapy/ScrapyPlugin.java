package com.javaspider.scrapy;

import com.javaspider.scrapy.item.Item;

import java.util.Map;
import java.util.List;

public interface ScrapyPlugin {
    default void configure(Map<String, Object> config) {
    }

    default void prepareSpider(Spider spider) {
    }

    default List<Spider.ItemPipeline> providePipelines() {
        return List.of();
    }

    default List<SpiderMiddleware> provideSpiderMiddlewares() {
        return List.of();
    }

    default List<DownloaderMiddleware> provideDownloaderMiddlewares() {
        return List.of();
    }

    default void onSpiderOpened(Spider spider) {
    }

    default void onSpiderClosed(Spider spider) {
    }

    default Item processItem(Item item, Spider spider) {
        return item;
    }
}
