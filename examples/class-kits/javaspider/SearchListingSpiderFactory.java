package project.spiders.classkit;

import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.item.Item;
import com.javaspider.scrapy.project.ProjectRuntime;

import java.util.List;

public final class SearchListingSpiderFactory {
    private SearchListingSpiderFactory() {
    }

    public static Spider create() {
        return new Spider() {
            {
                setName("search-listing");
                addStartUrl("https://example.com/search?q=demo");
                startMeta("runner", "browser");
            }

            @Override
            public List<Object> parse(Spider.Response response) {
                return List.of(new Item()
                    .set("kind", "listing")
                    .set("title", response.selector().css("title").firstText())
                    .set("url", response.getUrl()));
            }
        };
    }

    public static void register() {
        ProjectRuntime.registerSpider("search-listing", SearchListingSpiderFactory::create);
    }
}

