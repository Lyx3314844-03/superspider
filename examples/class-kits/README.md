# Spider Class Kits

These class kits provide reusable spider class templates for all four runtimes.

## Included Spider Classes

- `SearchListingSpider`
- `ProductDetailSpider`
- `ApiBootstrapSpider`
- `InfiniteScrollSpider`
- `LoginSessionSpider`
- `SocialFeedSpider`
- `EcommerceCatalogSpider`
- `EcommerceDetailSpider`
- `EcommerceReviewSpider`
- `EcommerceCrawler`
- browser capture companions for the runtimes that support rendered-page export

## Runtimes

- `examples/class-kits/pyspider/`
- `examples/class-kits/gospider/`
- `examples/class-kits/rustspider/`
- `examples/class-kits/javaspider/`

## Goal

The kits are not production-ready site implementations. They are reusable class skeletons that you can copy into a project and then adapt for:

- search/list pages
- detail pages
- bootstrap JSON pages
- infinite scroll pages
- authenticated session pages
- social/feed pages
- public e-commerce catalog pages
- public product detail pages
- public review/API pages
- unified ecommerce wrapper classes that can delegate to browser capture companions when a runtime supports them

## Recommended Use

1. Start from `profile-site` and the site preset output.
2. Pick the closest spider class template from the kit.
3. Use the new e-commerce profiles when you need product/list/detail/review coverage across multiple marketplaces.
4. Move it into your project and tune selectors, requests, and browser/session settings.

## Constraint

These kits are public-data templates. They do not guarantee crawling of every marketplace and they are not a drop-in solution for login-gated pages, private user data, orders, or challenge-page bypass.
