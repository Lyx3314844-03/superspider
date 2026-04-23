package project.spiders.classkit;

import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.item.Item;
import com.javaspider.scrapy.project.ProjectRuntime;

import java.util.List;

public final class SocialFeedSpiderFactory {
    private SocialFeedSpiderFactory() {
    }

    public static Spider create() {
        return new Spider() {
            {
                setName("social-feed");
                addStartUrl("https://example.com/feed");
                startMeta("runner", "browser");
            }

            @Override
            public List<Object> parse(Spider.Response response) {
                return List.of(new Item()
                    .set("kind", "social_feed")
                    .set("title", response.selector().css("title").firstText())
                    .set("url", response.getUrl()));
            }
        };
    }

    public static void register() {
        ProjectRuntime.registerSpider("social-feed", SocialFeedSpiderFactory::create);
    }
}
