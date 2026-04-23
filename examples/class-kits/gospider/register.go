package classkit

import projectruntime "gospider/scrapy/project"

func RegisterCatalog() {
	projectruntime.RegisterSpider("search-listing", NewSearchListingSpider)
	projectruntime.RegisterSpider("product-detail", NewProductDetailSpider)
	projectruntime.RegisterSpider("api-bootstrap", NewAPIBootstrapSpider)
	projectruntime.RegisterSpider("infinite-scroll", NewInfiniteScrollSpider)
	projectruntime.RegisterSpider("login-session", NewLoginSessionSpider)
	projectruntime.RegisterSpider("social-feed", NewSocialFeedSpider)
	projectruntime.RegisterSpider("ecommerce-catalog", NewEcommerceCatalogSpider)
	projectruntime.RegisterSpider("ecommerce-detail", NewEcommerceDetailSpider)
	projectruntime.RegisterSpider("ecommerce-review", NewEcommerceReviewSpider)
}
