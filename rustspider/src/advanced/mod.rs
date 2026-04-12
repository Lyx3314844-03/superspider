#![allow(dead_code)]

//! 终极增强模块
pub mod ultimate;

pub use ultimate::{
    create_ultimate_spider, CrawlResult, CrawlTask, UltimateConfig, UltimateSpider,
};
