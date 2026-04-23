package project.spiders.classkit;

public final class ClassKitSpiders {
    private ClassKitSpiders() {
    }

    public static void register() {
        ApiBootstrapSpiderFactory.register();
        EcommerceCatalogSpiderFactory.register();
        EcommerceDetailSpiderFactory.register();
        EcommerceReviewSpiderFactory.register();
        InfiniteScrollSpiderFactory.register();
        LoginSessionSpiderFactory.register();
        ProductDetailSpiderFactory.register();
        SearchListingSpiderFactory.register();
        SocialFeedSpiderFactory.register();
    }
}
