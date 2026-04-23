package project.spiders.classkit;

import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.item.Item;
import com.javaspider.scrapy.project.ProjectRuntime;

import java.util.List;

public final class EcommerceCatalogSpiderFactory {
    private EcommerceCatalogSpiderFactory() {
    }

    public static Spider create() {
        EcommerceSiteProfiles.Profile profile = EcommerceSiteProfiles.profileFor(EcommerceSiteProfiles.DEFAULT_SITE_FAMILY);
        return new Spider() {
            {
                setName("ecommerce-catalog");
                addStartUrl(profile.catalogUrl);
                startMeta("site_family", profile.family);
                startMeta("runner", profile.runner);
            }

            @Override
            public List<Object> parse(Spider.Response response) {
                String family = EcommerceSiteProfiles.siteFamilyFrom(response);
                EcommerceSiteProfiles.Profile current = EcommerceSiteProfiles.profileFor(family);
                List<String> links = response.selector().css("a").attrs("href");

                return List.of(new Item()
                    .set("kind", "ecommerce_catalog")
                    .set("site_family", family)
                    .set("runner", current.runner)
                    .set("title", EcommerceSiteProfiles.bestTitle(response))
                    .set("url", response.getUrl())
                    .set("product_link_candidates", EcommerceSiteProfiles.collectProductLinks(response.getUrl(), links, current, 20))
                    .set("next_page", EcommerceSiteProfiles.firstLinkWithKeywords(response.getUrl(), links, current.nextLinkKeywords))
                    .set("sku_candidates", EcommerceSiteProfiles.collectMatches(response.getBody(), current.itemIdPatterns, 10))
                    .set("price_excerpt", EcommerceSiteProfiles.firstMatch(response.getBody(), current.pricePatterns))
                    .set("note", "Template for public category/search pages. Tune the site profile before production crawling."));
            }
        };
    }

    public static void register() {
        ProjectRuntime.registerSpider("ecommerce-catalog", EcommerceCatalogSpiderFactory::create);
    }
}
