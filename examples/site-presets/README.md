# Site Presets

These presets are domain-oriented starter `JobSpec` files for common Chinese marketplace and social-commerce families.

## Included Presets

- `jd-search-browser.json`
- `jd-detail-browser.json`
- `taobao-search-browser.json`
- `taobao-detail-browser.json`
- `tmall-search-browser.json`
- `pinduoduo-search-browser.json`
- `xiaohongshu-feed-browser.json`
- `douyin-shop-browser.json`

## Usage

- Replace the placeholder keyword or URL before running.
- Tune selectors, waits, and extract rules against the current page shape.
- Prefer embedded JSON and captured network payloads when the DOM is unstable.
- Treat login, verification, and challenge pages as separate session/bootstrap work, not as extraction rules.
