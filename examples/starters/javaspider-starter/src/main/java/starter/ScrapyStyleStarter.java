package starter;

import com.javaspider.scrapy.CrawlerProcess;
import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.feed.FeedExporter;
import com.javaspider.scrapy.item.Item;

import java.util.List;

public final class ScrapyStyleStarter {
    private ScrapyStyleStarter() {
    }

    public static void main(String[] args) {
        Spider spider = new Spider() {
            {
                setName("starter");
                addStartUrl("https://example.com");
            }

            @Override
            public List<Object> parse(Response response) {
                return List.of(
                    new Item()
                        .set("title", response.selector().css("title").firstText())
                        .set("url", response.getUrl())
                        .set("framework", "javaspider")
                );
            }
        };

        List<Item> items = new CrawlerProcess(spider).crawl();
        try (FeedExporter exporter = FeedExporter.json("artifacts/exports/javaspider-starter-items.json")) {
            exporter.exportItems(items);
        }
        System.out.println("exported items: " + items.size());
    }
}
