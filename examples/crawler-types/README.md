# Crawler Type Templates

These templates follow the shared normalized `JobSpec` shape used across the SuperSpider runtimes. They are intended as starting points for difficult site families, not one-click guarantees for every protected site.

## Included Templates

- `api-bootstrap-http.json`
  Use when the page ships useful JSON in script tags, hydration blobs, or schema.org blocks.
- `hydrated-spa-browser.json`
  Use for SPA pages where the useful state appears after client hydration.
- `infinite-scroll-browser.json`
  Use for list pages that reveal more items through scroll or load-more behavior.
- `ecommerce-search-browser.json`
  Use for catalog and search result pages with prices, SKU-like ids, and dynamic listing content.
- `login-session-browser.json`
  Use when you need to capture an authenticated browser session before extracting post-login content.

## Customization Notes

- Replace `example.com` URLs and `allowed_domains` before running.
- Review selectors, waits, and extract rules against the actual target page.
- For login/session flows, use your own authorized account/session assets and avoid scraping challenge pages.
- Prefer embedded JSON and stable network payloads before brittle DOM-only selectors.

## Coverage Goal

These templates improve coverage for:

- bootstrap JSON pages
- hydrated SPA pages
- infinite scroll lists
- e-commerce search and detail flows
- authenticated session pages

They do not guarantee access to every site, especially when a site requires login, actively blocks automation, or serves challenge pages.
