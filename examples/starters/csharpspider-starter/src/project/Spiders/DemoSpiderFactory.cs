// scrapy: name=demo url=https://example.com
using CSharpSpider.Scrapy;

public static class DemoSpiderFactory
{
    public static Spider Create()
    {
        return new Spider(
            "demo",
            response => new object[]
            {
                new Item()
                    .Set("title", response.Selector().Title())
                    .Set("url", response.Url)
                    .Set("framework", "csharpspider")
            }
        ).AddStartUrl("https://example.com");
    }
}
