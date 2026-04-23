package project.spiders.classkit;

import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.item.Item;
import com.javaspider.scrapy.project.ProjectRuntime;

import java.util.List;

public final class ApiBootstrapSpiderFactory {
    private ApiBootstrapSpiderFactory() {
    }

    public static Spider create() {
        return new Spider() {
            {
                setName("api-bootstrap");
                addStartUrl("https://example.com/app/page");
            }

            @Override
            public List<Object> parse(Spider.Response response) {
                return List.of(new Item()
                    .set("kind", "api_bootstrap")
                    .set("title", response.selector().css("title").firstText())
                    .set("url", response.getUrl())
                    .set("bootstrap_excerpt", response.getBody()));
            }
        };
    }

    public static void register() {
        ProjectRuntime.registerSpider("api-bootstrap", ApiBootstrapSpiderFactory::create);
    }
}

