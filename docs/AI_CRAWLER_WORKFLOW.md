# AI Crawler Workflow

This is the shortest end-to-end path for the new AI crawler authoring flow.

## New Project

```bash
<runtime> scrapy init --path my-ai-project
cd my-ai-project
<runtime> scrapy scaffold-ai --project . --url https://example.com --name product_ai
```

Generated assets:

- `ai-schema.json`
- `ai-blueprint.json`
- `ai-extract-prompt.txt`
- `ai-auth.json`
- `ai-plan.json`
- AI spider source template

## Existing Project

```bash
<runtime> scrapy sync-ai --project . --spider existing_spider
```

This backfills AI assets into an existing scrapy-style project.

## Auth Flow

When the target needs authentication:

1. Edit `ai-auth.json`
2. Fill headers/cookies or session file paths
3. Optionally define `actions`
4. Capture a browser session
5. Validate the captured session

```bash
<runtime> scrapy auth-capture --project . --url https://example.com --session auth
<runtime> scrapy auth-validate --project . --url https://example.com
```

## Run

```bash
<runtime> scrapy run --project . --spider product_ai
```

## Auth Action DSL

Supported action types:

- `if`
- `goto`
- `wait`
- `click`
- `type`
- `otp`
- `mfa_totp`
- `submit`
- `wait_network_idle`
- `captcha_solve`
- `captcha_wait`
- `select`
- `hover`
- `scroll`
- `eval`
- `assert`
- `save_as`
- `listen_network`
- `reverse_profile`
- `reverse_analyze_crypto`
- `screenshot`

Example:

```json
{
  "actions": [
    { "type": "goto", "url": "https://example.com/login" },
    { "type": "type", "selector": "#username", "value": "demo" },
    { "type": "type", "selector": "#password", "value": "secret" },
    {
      "type": "if",
      "when": { "selector_exists": "#otp" },
      "then": [
        { "type": "mfa_totp", "selector": "#otp", "totp_env": "SPIDER_AUTH_TOTP_SECRET" }
      ]
    },
    {
      "type": "if",
      "when": { "selector_exists": ".cf-turnstile,[data-sitekey]" },
      "then": [
        {
          "type": "captcha_solve",
          "challenge": "turnstile",
          "selector": ".cf-turnstile,[data-sitekey]",
          "provider": "anticaptcha",
          "save_as": "captcha_token"
        }
      ]
    },
    { "type": "submit", "selector": "#password" },
    { "type": "wait_network_idle" },
    { "type": "reverse_profile", "save_as": "reverse_runtime" },
    { "type": "assert", "url_contains": "/dashboard" },
    { "type": "save_as", "value": "url", "save_as": "final_url" }
  ]
}
```
