# JavaSpider

Java runtime for the Spider Framework Suite.

JavaSpider 偏向浏览器工作流、审计链、企业集成和 Maven 打包，适合已有 Java 生态和构建链的抓取场景。

## Highlights

- unified CLI: `crawl`, `doctor`, `scrapy`, `ultimate`, `anti-bot`, `node-reverse`
- workflow-oriented browser support with Selenium and Playwright helper paths
- audit, connector, session, and anti-bot surfaces
- built-in metadata runner plus optional project runner JAR artifact for `scrapy run --project`

## Quick Start

```bash
mvn -q -Dmaven.test.skip=true package
java -cp "target/classes;target/dependency/*" com.javaspider.EnhancedSpider capabilities
java -cp "target/classes;target/dependency/*" com.javaspider.EnhancedSpider doctor --json
java -cp "target/classes;target/dependency/*" com.javaspider.EnhancedSpider scrapy init --path demo-project
java -cp "target/classes;target/dependency/*" com.javaspider.EnhancedSpider scrapy run --project demo-project
java -cp "target/classes;target/dependency/*" com.javaspider.EnhancedSpider ultimate https://example.com
```

## Key CLI Entrypoints

- `com.javaspider.EnhancedSpider`
- `com.javaspider.cli.SuperSpiderCLI`
- `com.javaspider.cli.WorkflowSpiderCLI`
- `com.javaspider.cli.WorkflowReplayCLI`

## API Surfaces

- Scrapy-style API: `src/main/java/com/javaspider/scrapy`
- Browser/workflow: `src/main/java/com/javaspider/browser`, `src/main/java/com/javaspider/workflow`
- Anti-bot/session: `src/main/java/com/javaspider/antibot`, `src/main/java/com/javaspider/session`
- Audit/connectors: `src/main/java/com/javaspider/audit`, `src/main/java/com/javaspider/connector`

## Extended Surfaces

Hidden-but-supported entrypoints and modules are documented in:

- `../docs/FRAMEWORK_DEEP_SURFACES.md`

Notable extra JavaSpider surfaces beyond the short highlights:

- `ai`, `curl`, `job`, `jobdir`, `http-cache`, `console`
- `selector-studio`, `profile-site`, `workflow`, `media`
- `contracts.AutoscaledFrontier`, audit trail, connector, session profile, runtime artifact store

## Project Runner

`scrapy run --project` no longer compiles project source with `javac` at runtime.

It now:

1. executes the project runner JAR artifact declared in `scrapy-project.json` when present
2. otherwise falls back to the built-in metadata runner

## Deploy

- Maven package: `mvn -q -Dmaven.test.skip=true package`
- wrapper helpers: `run-framework.sh`, `run-framework.bat`
- starter project: `../examples/starters/javaspider-starter`

## Verification

- focused tests: `mvn -q "-Dtest=EnhancedSpiderContractTest,SpiderTest" test`
- broader suite verification lives in the repo root under `tests/`

## Live Captcha Smoke

`CaptchaSolverLiveSmokeTest` is opt-in and safe to run on ordinary developer machines.

- enable all live captcha smoke checks: `JAVASPIDER_LIVE_CAPTCHA_SMOKE=1`
- local Tesseract path: automatically runs only when `tesseract` is available on `PATH`
- DeathByCaptcha: requires `DEATHBYCAPTCHA_USERNAME` and `DEATHBYCAPTCHA_PASSWORD`
- custom endpoint: requires `JAVASPIDER_CUSTOM_CAPTCHA_URL` and optionally `JAVASPIDER_CUSTOM_CAPTCHA_TOKEN`

Run it with:

```bash
mvn -q "-Dtest=CaptchaSolverLiveSmokeTest" test
```

GitHub Actions manual workflow:

- workflow: `.github/workflows/javaspider-live-captcha-smoke.yml`
- required secrets for external providers:
  - `DEATHBYCAPTCHA_USERNAME`
  - `DEATHBYCAPTCHA_PASSWORD`
  - `JAVASPIDER_CUSTOM_CAPTCHA_URL`
  - `JAVASPIDER_CUSTOM_CAPTCHA_TOKEN`
