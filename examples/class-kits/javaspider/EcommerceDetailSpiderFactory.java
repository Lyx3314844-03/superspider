package project.spiders.classkit;

import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.item.Item;
import com.javaspider.scrapy.project.ProjectRuntime;

import java.util.List;

public final class EcommerceDetailSpiderFactory {
    private EcommerceDetailSpiderFactory() {
    }

    public static Spider create() {
        EcommerceSiteProfiles.Profile profile = EcommerceSiteProfiles.profileFor(EcommerceSiteProfiles.DEFAULT_SITE_FAMILY);
        return new Spider() {
            {
                setName("ecommerce-detail");
                addStartUrl(profile.detailUrl);
                startMeta("site_family", profile.family);
                startMeta("runner", profile.runner);
            }

            @Override
            public List<Object> parse(Spider.Response response) {
                String family = EcommerceSiteProfiles.siteFamilyFrom(response);
                EcommerceSiteProfiles.Profile current = EcommerceSiteProfiles.profileFor(family);
                List<String> links = response.selector().css("a").attrs("href");

                return List.of(new Item()
                    .set("kind", "ecommerce_detail")
                    .set("site_family", family)
                    .set("title", EcommerceSiteProfiles.bestTitle(response))
                    .set("url", response.getUrl())
                    .set("item_id", EcommerceSiteProfiles.firstMatch(response.getBody(), current.itemIdPatterns))
                    .set("price", EcommerceSiteProfiles.firstMatch(response.getBody(), current.pricePatterns))
                    .set("shop", EcommerceSiteProfiles.firstMatch(response.getBody(), current.shopPatterns))
                    .set("review_count", EcommerceSiteProfiles.firstMatch(response.getBody(), current.reviewCountPatterns))
                    .set("image_candidates", EcommerceSiteProfiles.collectImageLinks(response.getUrl(), response.selector().css("img").attrs("src"), 10))
                    .set("review_url", EcommerceSiteProfiles.firstLinkWithKeywords(response.getUrl(), links, current.reviewLinkKeywords))
                    .set("html_excerpt", EcommerceSiteProfiles.textExcerpt(response.getBody(), 800))
                    .set("note", "Template for public product detail pages. Extend with site-specific JSON/bootstrap extraction when available."));
            }
        };
    }

    public static void register() {
        ProjectRuntime.registerSpider("ecommerce-detail", EcommerceDetailSpiderFactory::create);
    }
}
