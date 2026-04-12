use std::sync::Arc;

use rustspider::scrapy::{CrawlerProcess, FeedExporter, Item, Output, Spider};

fn main() -> Result<(), String> {
    let spider = Spider::new(
        "starter",
        Arc::new(|response| {
            vec![Output::Item(
                Item::new()
                    .set("title", response.css("title").get().unwrap_or_default())
                    .set("url", response.url.clone())
                    .set("framework", "rustspider"),
            )]
        }),
    )
    .add_start_url("https://example.com");

    let items = CrawlerProcess::new(spider).run()?;
    let mut exporter = FeedExporter::new("json", "artifacts/exports/rustspider-starter-items.json");
    for item in items {
        exporter.export_item(item);
    }
    let output = exporter.close()?;
    println!("exported {}", output.display());
    Ok(())
}
