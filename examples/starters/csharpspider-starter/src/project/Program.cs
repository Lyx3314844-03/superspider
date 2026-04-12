using CSharpSpider.Scrapy;
using CSharpSpider.Scrapy.Project;

ProjectRuntime.RegisterSpider("demo", () => DemoSpiderFactory.Create());
ProjectRuntime.RegisterPlugin("project-plugin", () => new DefaultPlugin());
if (await ProjectRuntime.RunFromEnvironmentAsync()) return;

var spider = ProjectRuntime.ResolveSpider("");
var plugins = ProjectRuntime.ResolvePlugins();
var process = new CrawlerProcess(spider);
foreach (var plugin in plugins)
{
    process.AddPlugin(plugin);
}
var items = await process.RunAsync();
var exporter = new FeedExporter("json", Path.Combine("artifacts", "exports", "items.json"));
foreach (var item in items)
{
    exporter.ExportItem(item);
}
exporter.Close();
