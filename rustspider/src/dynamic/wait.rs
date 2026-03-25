//! 动态等待模块
//! 支持各种等待条件

use std::thread;
use std::time::{Duration, Instant};

/// 动态等待器
pub struct DynamicWait {
    timeout: Duration,
    polling: Duration,
}

impl DynamicWait {
    /// 创建动态等待器
    pub fn new(timeout_secs: u64, polling_ms: u64) -> Self {
        DynamicWait {
            timeout: Duration::from_secs(timeout_secs),
            polling: Duration::from_millis(polling_ms),
        }
    }

    /// 等待条件满足
    pub fn wait_for<F>(&self, mut condition: F) -> bool
    where
        F: FnMut() -> bool,
    {
        let start = Instant::now();

        while start.elapsed() < self.timeout {
            if condition() {
                return true;
            }
            thread::sleep(self.polling);
        }

        false
    }

    /// 等待元素出现
    pub fn wait_for_element<F>(&self, mut checker: F, selector: &str) -> bool
    where
        F: FnMut(&str) -> bool,
    {
        self.wait_for(|| checker(selector))
    }

    /// 等待文本出现
    pub fn wait_for_text<F>(&self, mut getter: F, text: &str) -> bool
    where
        F: FnMut() -> String,
    {
        self.wait_for(|| getter().contains(text))
    }

    /// 等待 URL 匹配
    pub fn wait_for_url<F>(&self, mut getter: F, pattern: &str) -> bool
    where
        F: FnMut() -> String,
    {
        self.wait_for(|| getter().contains(pattern))
    }

    /// 休眠
    pub fn sleep(ms: u64) {
        thread::sleep(Duration::from_millis(ms));
    }
}

/// 滚动加载器
pub struct ScrollLoader<FScroll, FHeight> {
    scroll_fn: FScroll,
    get_height_fn: FHeight,
}

impl<FScroll, FHeight> ScrollLoader<FScroll, FHeight>
where
    FScroll: FnMut(),
    FHeight: FnMut() -> i64,
{
    /// 创建滚动加载器
    pub fn new(scroll_fn: FScroll, get_height_fn: FHeight) -> Self {
        ScrollLoader {
            scroll_fn,
            get_height_fn,
        }
    }

    /// 滚动到底部
    pub fn scroll_to_bottom(&mut self, pause_ms: u64, max_scrolls: usize) -> usize {
        let mut scroll_count = 0;
        let mut last_height = (self.get_height_fn)();
        let mut stable_count = 0;

        while scroll_count < max_scrolls {
            // 滚动到底部
            (self.scroll_fn)();
            scroll_count += 1;

            // 等待加载
            DynamicWait::sleep(pause_ms);

            // 检查新高度
            let new_height = (self.get_height_fn)();

            if new_height == last_height {
                stable_count += 1;
                if stable_count >= 2 {
                    break;
                }
            } else {
                stable_count = 0;
                last_height = new_height;
            }
        }

        scroll_count
    }
}

/// 表单交互器
pub struct FormInteractor<FClick, FInput> {
    click_fn: FClick,
    input_fn: FInput,
}

impl<FClick, FInput> FormInteractor<FClick, FInput>
where
    FClick: FnMut(&str) -> Result<(), String>,
    FInput: FnMut(&str, &str) -> Result<(), String>,
{
    /// 创建表单交互器
    pub fn new(click_fn: FClick, input_fn: FInput) -> Self {
        FormInteractor { click_fn, input_fn }
    }

    /// 点击元素
    pub fn click(&mut self, selector: &str) -> Result<(), String> {
        (self.click_fn)(selector)
    }

    /// 输入文本
    pub fn input_text(&mut self, selector: &str, text: &str) -> Result<(), String> {
        (self.input_fn)(selector, text)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicI64, AtomicUsize, Ordering};
    use std::sync::Arc;

    #[test]
    fn test_wait_for() {
        let wait = DynamicWait::new(5, 100);
        let mut counter = 0;

        let result = wait.wait_for(|| {
            counter += 1;
            counter >= 3
        });

        assert!(result);
    }

    #[test]
    fn test_scroll_loader_with_distinct_closures() {
        let height = Arc::new(AtomicI64::new(1000));
        let scrolls = Arc::new(AtomicUsize::new(0));

        let scroll_height = Arc::clone(&height);
        let scroll_counter = Arc::clone(&scrolls);
        let read_height = Arc::clone(&height);

        let mut loader = ScrollLoader::new(
            move || {
                let current = scroll_counter.fetch_add(1, Ordering::SeqCst) + 1;
                if current < 3 {
                    scroll_height.fetch_add(500, Ordering::SeqCst);
                }
            },
            move || read_height.load(Ordering::SeqCst),
        );

        let total = loader.scroll_to_bottom(1, 10);
        assert!(total >= 3);
    }

    #[test]
    fn test_form_interactor_passes_text() {
        let mut clicked = String::new();
        let mut typed = String::new();

        let mut interactor = FormInteractor::new(
            |selector| {
                clicked = selector.to_string();
                Ok(())
            },
            |selector, text| {
                typed = format!("{}={}", selector, text);
                Ok(())
            },
        );

        interactor.click("#submit").unwrap();
        interactor.input_text("#search", "rustspider").unwrap();

        assert_eq!(clicked, "#submit");
        assert_eq!(typed, "#search=rustspider");
    }
}
