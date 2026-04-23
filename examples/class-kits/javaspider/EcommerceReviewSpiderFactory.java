package project.spiders.classkit;

import com.javaspider.scrapy.Spider;
import com.javaspider.scrapy.item.Item;
import com.javaspider.scrapy.project.ProjectRuntime;

import java.util.List;

public final class EcommerceReviewSpiderFactory {
    private EcommerceReviewSpiderFactory() {
    }

    public static Spider create() {
        EcommerceSiteProfiles.Profile profile = EcommerceSiteProfiles.profileFor(EcommerceSiteProfiles.DEFAULT_SITE_FAMILY);
        return new Spider() {
            {
                setName("ecommerce-review");
                addStartUrl(profile.reviewUrl);
                startMeta("site_family", profile.family);
                startMeta("runner", profile.runner);
            }

            @Override
            public List<Object> parse(Spider.Response response) {
                String family = EcommerceSiteProfiles.siteFamilyFrom(response);
                EcommerceSiteProfiles.Profile current = EcommerceSiteProfiles.profileFor(family);

                return List.of(new Item()
                    .set("kind", "ecommerce_review")
                    .set("site_family", family)
                    .set("url", response.getUrl())
                    .set("item_id", EcommerceSiteProfiles.firstMatch(response.getBody(), current.itemIdPatterns))
                    .set("rating", EcommerceSiteProfiles.firstMatch(response.getBody(), current.ratingPatterns))
                    .set("review_count", EcommerceSiteProfiles.firstMatch(response.getBody(), current.reviewCountPatterns))
                    .set("review_id_candidates", EcommerceSiteProfiles.collectMatches(response.getBody(), List.of("(?:commentId|reviewId|id)[\"'=:\\s]+([A-Za-z0-9_-]+)"), 10))
                    .set("excerpt", EcommerceSiteProfiles.textExcerpt(response.getBody(), 800))
                    .set("note", "Template for public review pages or review APIs. Prefer stable JSON payloads over brittle DOM selectors."));
            }
        };
    }

    public static void register() {
        ProjectRuntime.registerSpider("ecommerce-review", EcommerceReviewSpiderFactory::create);
    }
}
