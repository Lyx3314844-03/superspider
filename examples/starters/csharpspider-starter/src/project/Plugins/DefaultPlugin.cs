using CSharpSpider.Scrapy;

public sealed class DefaultPlugin : IScrapyPlugin
{
    public string Name => "project-plugin";

    public Item ProcessItem(Item item, Spider spider)
    {
        return item.Set("plugin", "project-plugin");
    }
}
