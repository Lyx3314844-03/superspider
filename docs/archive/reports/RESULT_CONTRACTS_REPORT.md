# Result Contracts

Summary: 8 passed, 0 failed

| Check | Status |
| --- | --- |
| contract-schemas | passed |
| control-plane-doc | passed |
| gospider-web-result-contract | passed |
| javaspider-web-result-contract | passed |
| pyspider-web-source-contract | passed |
| rustspider-web-source-contract | passed |
| go-web-source-contract | passed |
| java-web-source-contract | passed |

## contract-schemas

- Status: passed
- Details: graph/result schemas present

## control-plane-doc

- Status: passed
- Details: web control-plane doc references result and graph contracts

## gospider-web-result-contract

- Status: passed
- Command: `C:\Program Files\Go\bin\go.EXE test ./web -run ^TestServerTaskLifecycleProducesResultsAndLogs$`
- Details: ok  	gospider/web	0.117s

## javaspider-web-result-contract

- Status: passed
- Command: `C:\ProgramData\chocolatey\lib\maven\apache-maven-3.9.14\bin\mvn.CMD -q clean -Dtest=SpiderControllerTest test`
- Details: 2026-04-12 00:03:58.798 [Thread-3] INFO  com.javaspider.core.Spider - Spider [web-controller-test] started with 1 threads
2026-04-12 00:03:58.896 [main] INFO  com.javaspider.core.Spider - Executor service shutdown, waiting for tasks to complete...
2026-04-12 00:03:59.805 [main] INFO  com.javaspider.core.Spider - Spider [web-controller-test] stopped. Total: 0, Success: 0, Failed: 0, Duration: 100ms

## pyspider-web-source-contract

- Status: passed
- Details: runtime source carries graph artifact refs

## rustspider-web-source-contract

- Status: passed
- Details: runtime source carries graph artifact refs

## go-web-source-contract

- Status: passed
- Details: runtime source carries graph artifact refs

## java-web-source-contract

- Status: passed
- Details: runtime source carries graph artifact refs
