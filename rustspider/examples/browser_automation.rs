//! 浏览器自动化示例
//! 
//! 运行前请确保：
//! 1. 已安装 ChromeDriver: https://chromedriver.chromium.org/
//! 2. ChromeDriver 在 PATH 中或运行在 http://localhost:4444
//! 3. 启用 browser 特性：cargo run --example browser_automation --features browser

use rustspider::browser::{BrowserBuilder, BrowserConfig, BrowserManager};
use std::time::Duration;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🚀 浏览器自动化示例\n");

    // ========== 示例 1: 基本浏览 ==========
    println!("📖 示例 1: 基本浏览");
    basic_browsing().await?;

    // ========== 示例 2: 表单操作 ==========
    println!("\n📝 示例 2: 表单操作");
    form_operations().await?;

    // ========== 示例 3: 截图和 PDF ==========
    println!("\n📸 示例 3: 截图和 PDF");
    screenshot_demo().await?;

    // ========== 示例 4: 滚动加载 ==========
    println!("\n📜 示例 4: 滚动加载");
    scroll_loading().await?;

    // ========== 示例 5: Cookie 管理 ==========
    println!("\n🍪 示例 5: Cookie 管理");
    cookie_management().await?;

    // ========== 示例 6: 多标签页操作 ==========
    println!("\n🔖 示例 6: 多标签页操作");
    multi_tab().await?;

    println!("\n✅ 所有示例完成！");

    Ok(())
}

/// 示例 1: 基本浏览
async fn basic_browsing() -> Result<(), Box<dyn std::error::Error>> {
    // 创建浏览器（无头模式）
    let browser = BrowserBuilder::new()
        .headless(true)
        .timeout(Duration::from_secs(30))
        .build()
        .await?;

    // 导航到页面
    browser.navigate("https://www.example.com").await?;
    
    // 获取信息
    let title = browser.get_title().await?;
    let url = browser.get_url().await?;
    let html = browser.get_html().await?;

    println!("  标题：{}", title);
    println!("  URL: {}", url);
    println!("  HTML 长度：{} 字符", html.len());

    // 等待并关闭
    browser.wait_for_page_load(None).await?;
    browser.close().await?;

    Ok(())
}

/// 示例 2: 表单操作
async fn form_operations() -> Result<(), Box<dyn std::error::Error>> {
    let browser = BrowserBuilder::new()
        .headless(true)
        .build()
        .await?;

    // 导航到测试页面
    browser.navigate("https://www.w3schools.com/html/html_forms.asp").await?;
    browser.wait_for_page_load(None).await?;

    // 检查表单元素是否存在
    if browser.element_exists("input[type='text']").await? {
        println!("  ✓ 找到文本输入框");
        
        // 填写表单
        browser.fill("input[type='text']", "张三").await?;
        println!("  ✓ 填写姓名");

        // 获取输入框的值
        let value = browser.get_element_attribute("input[type='text']", "value").await?;
        println!("  输入框值：{}", value);
    }

    browser.close().await?;
    Ok(())
}

/// 示例 3: 截图和 PDF
async fn screenshot_demo() -> Result<(), Box<dyn std::error::Error>> {
    let browser = BrowserBuilder::new()
        .headless(true)
        .build()
        .await?;

    // 导航
    browser.navigate("https://www.rust-lang.org").await?;
    browser.wait_for_page_load(None).await?;

    // 全屏截图
    browser.screenshot_to_file("rust_lang_screenshot.png").await?;
    println!("  ✓ 截图保存：rust_lang_screenshot.png");

    // 元素截图
    if browser.element_exists("nav").await? {
        let nav_screenshot = browser.screenshot_element("nav").await?;
        std::fs::write("nav_screenshot.png", &nav_screenshot)?;
        println!("  ✓ 导航栏截图保存：nav_screenshot.png");
    }

    browser.close().await?;
    Ok(())
}

/// 示例 4: 滚动加载
async fn scroll_loading() -> Result<(), Box<dyn std::error::Error>> {
    let browser = BrowserBuilder::new()
        .headless(true)
        .build()
        .await?;

    // 导航到长页面
    browser.navigate("https://zh.wikipedia.org/wiki/Rust").await?;
    browser.wait_for_page_load(None).await?;

    // 获取初始高度
    let initial_height = browser.execute_script_with_result::<f64>(
        "return document.body.scrollHeight",
        vec![]
    ).await?;
    println!("  初始页面高度：{:.0}px", initial_height);

    // 滚动到底部
    browser.scroll_to_bottom().await?;
    println!("  ✓ 滚动到底部");

    // 等待加载
    tokio::time::sleep(Duration::from_secs(2)).await;

    // 获取新高度
    let new_height = browser.execute_script_with_result::<f64>(
        "return document.body.scrollHeight",
        vec![]
    ).await?;
    println!("  新页面高度：{:.0}px", new_height);

    // 滚动回顶部
    browser.scroll_to_top().await?;
    println!("  ✓ 滚动回顶部");

    browser.close().await?;
    Ok(())
}

/// 示例 5: Cookie 管理
async fn cookie_management() -> Result<(), Box<dyn std::error::Error>> {
    let browser = BrowserBuilder::new()
        .headless(true)
        .build()
        .await?;

    // 导航
    browser.navigate("https://www.example.com").await?;
    browser.wait_for_page_load(None).await?;

    // 获取所有 Cookie
    let cookies = browser.get_all_cookies().await?;
    println!("  初始 Cookie 数量：{}", cookies.len());

    // 设置 Cookie
    browser.set_cookie("test_cookie", "test_value", None).await?;
    println!("  ✓ 设置 Cookie: test_cookie=test_value");

    // 获取特定 Cookie
    if let Some(value) = browser.get_cookie("test_cookie").await? {
        println!("  获取 Cookie: test_cookie={}", value);
    }

    // 删除 Cookie
    browser.delete_cookie("test_cookie").await?;
    println!("  ✓ 删除 Cookie: test_cookie");

    // 验证删除
    let exists = browser.get_cookie("test_cookie").await?.is_some();
    println!("  Cookie 是否存在：{}", exists);

    browser.close().await?;
    Ok(())
}

/// 示例 6: 多标签页操作
async fn multi_tab() -> Result<(), Box<dyn std::error::Error>> {
    let browser = BrowserBuilder::new()
        .headless(true)
        .build()
        .await?;

    // 打开第一个页面
    browser.navigate("https://www.example.com").await?;
    println!("  ✓ 打开标签页 1: {}", browser.get_title().await?);

    // 创建新标签页
    browser.new_tab().await?;
    println!("  ✓ 创建新标签页");

    // 在新标签页打开页面
    browser.navigate("https://www.rust-lang.org").await?;
    println!("  ✓ 标签页 2: {}", browser.get_title().await?);

    // 获取所有标签页
    let handles = browser.get_window_handles().await?;
    println!("  标签页数量：{}", handles.len());

    // 切换回第一个标签页
    if let Some(first_handle) = handles.first() {
        browser.switch_to_window(first_handle).await?;
        println!("  ✓ 切换回标签页 1: {}", browser.get_title().await?);
    }

    // 关闭当前标签页
    browser.close_tab().await?;
    println!("  ✓ 关闭当前标签页");

    browser.close().await?;
    Ok(())
}

/// 示例 7: 绕过自动化检测（用于反爬网站）
async fn anti_detection_demo() -> Result<(), Box<dyn std::error::Error>> {
    let browser = BrowserBuilder::new()
        .headless(true)
        .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        .build()
        .await?;

    // 绕过检测
    browser.bypass_detection().await?;
    println!("  ✓ 已绕过自动化检测");

    // 验证
    let is_webdriver = browser.execute_script_with_result::<Option<bool>>(
        "return navigator.webdriver",
        vec![]
    ).await?;
    
    println!("  navigator.webdriver: {:?}", is_webdriver);

    browser.close().await?;
    Ok(())
}

/// 示例 8: 等待和条件判断
async fn wait_conditions_demo() -> Result<(), Box<dyn std::error::Error>> {
    let browser = BrowserBuilder::new()
        .headless(true)
        .timeout(Duration::from_secs(10))
        .build()
        .await?;

    browser.navigate("https://www.example.com").await?;

    // 等待页面加载完成
    browser.wait_for_page_load(None).await?;
    println!("  ✓ 页面加载完成");

    // 等待元素出现
    browser.wait_for_element("h1", None).await?;
    println!("  ✓ h1 元素出现");

    // 等待文本出现
    browser.wait_for_text("Example", None).await?;
    println!("  ✓ 文本 'Example' 出现");

    // 检查元素是否存在
    let exists = browser.element_exists("h1").await?;
    println!("  h1 元素存在：{}", exists);

    // 获取元素数量
    let count = browser.count_elements("p").await?;
    println!("  p 元素数量：{}", count);

    // 获取所有段落文本
    let texts = browser.get_all_texts("p").await?;
    for (i, text) in texts.iter().enumerate() {
        println!("  段落 {}: {}", i + 1, text.trim());
    }

    browser.close().await?;
    Ok(())
}
