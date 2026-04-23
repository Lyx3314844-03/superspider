package project.spiders.classkit;

import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.item.Item;
import com.javaspider.scrapy.project.ProjectRuntime;

import java.util.List;

public final class InfiniteScrollSpiderFactory {
    private InfiniteScrollSpiderFactory() {
    }

    public static Spider create() {
        return new Spider() {
            {
                setName("infinite-scroll");
                addStartUrl("https://example.com/discover");
                startMeta("runner", "browser");
            }

            @Override
            public List<Object> parse(Spider.Response response) {
                return List.of(new Item()
                    .set("kind", "infinite_scroll")
                    .set("title", response.selector().css("title").firstText())
                    .set("url", response.getUrl()));
            }
        };
    }

    public static void register() {
        ProjectRuntime.registerSpider("infinite-scroll", InfiniteScrollSpiderFactory::create);
    }
}

