package project.spiders.classkit;

import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.item.Item;
import com.javaspider.scrapy.project.ProjectRuntime;

import java.util.List;

public final class LoginSessionSpiderFactory {
    private LoginSessionSpiderFactory() {
    }

    public static Spider create() {
        return new Spider() {
            {
                setName("login-session");
                addStartUrl("https://example.com/login");
                startMeta("runner", "browser");
            }

            @Override
            public List<Object> parse(Spider.Response response) {
                return List.of(new Item()
                    .set("kind", "login_session")
                    .set("title", response.selector().css("title").firstText())
                    .set("url", response.getUrl()));
            }
        };
    }

    public static void register() {
        ProjectRuntime.registerSpider("login-session", LoginSessionSpiderFactory::create);
    }
}

