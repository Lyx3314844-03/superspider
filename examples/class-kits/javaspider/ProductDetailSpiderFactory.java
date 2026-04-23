package project.spiders.classkit;

import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.item.Item;
import com.javaspider.scrapy.project.ProjectRuntime;

import java.util.List;

public final class ProductDetailSpiderFactory {
    private ProductDetailSpiderFactory() {
    }

    public static Spider create() {
        return new Spider() {
            {
                setName("product-detail");
                addStartUrl("https://example.com/item/123");
            }

            @Override
            public List<Object> parse(Spider.Response response) {
                return List.of(new Item()
                    .set("kind", "detail")
                    .set("title", response.selector().css("title").firstText())
                    .set("url", response.getUrl())
                    .set("html_excerpt", response.getBody()));
            }
        };
    }

    public static void register() {
        ProjectRuntime.registerSpider("product-detail", ProductDetailSpiderFactory::create);
    }
}

