# Public Install Chain Report

Summary: 9 passed, 0 failed

| Check | Status |
| --- | --- |
| public-docs | passed |
| gospider-public-build | passed |
| gospider-public-smoke | passed |
| rustspider-public-build | passed |
| rustspider-public-smoke | passed |
| javaspider-public-package | passed |
| javaspider-public-smoke | passed |
| pyspider-public-package | passed |
| pyspider-public-smoke | passed |

## public-docs

- Status: passed
- Details: public install docs aligned

## gospider-public-build

- Status: passed
- Command: `C:\Program Files\Go\bin\go.EXE build -o C:\Users\ADMINI~1\AppData\Local\Temp\tmp252ow705\gospider.exe ./cmd/gospider`
- Details: command completed

## gospider-public-smoke

- Status: passed
- Command: `C:\Users\ADMINI~1\AppData\Local\Temp\tmp252ow705\gospider.exe version`
- Details: Enhanced Anti-Bot module loaded
Multi-platform media downloader loaded
gospider version 2.0.0

## rustspider-public-build

- Status: passed
- Command: `C:\Program Files\Rust stable MSVC 1.94\bin\cargo.EXE build --release --bin rustspider`
- Details: Compiling rustspider v1.0.0 (C:\Users\Administrator\spider\rustspider)
    Finished `release` profile [optimized] target(s) in 2m 57s

## rustspider-public-smoke

- Status: passed
- Command: `C:\Users\Administrator\spider\rustspider\target\release\rustspider.exe version`
- Details: rustspider 1.0.0

## javaspider-public-package

- Status: passed
- Command: `C:\ProgramData\chocolatey\lib\maven\apache-maven-3.9.14\bin\mvn.CMD -q -Dmaven.javadoc.skip=true -Dmaven.test.skip=true clean package dependency:copy-dependencies`
- Details: command completed

## javaspider-public-smoke

- Status: passed
- Command: `C:\Program Files\Common Files\Oracle\Java\javapath\java.EXE -cp C:\Users\Administrator\spider\javaspider\target\javaspider-1.0.0.jar;C:\Users\Administrator\spider\javaspider\target\dependency\* com.javaspider.EnhancedSpider version`
- Details: JavaSpider Framework CLI v2.1.0

## pyspider-public-package

- Status: passed
- Command: `C:\Python314\python.exe -m pip install . --no-deps --target C:\Users\ADMINI~1\AppData\Local\Temp\tmpendebs4t\site`
- Details: Processing c:\users\administrator\spider\pyspider
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Getting requirements to build wheel: started
  Getting requirements to build wheel: finished with status 'done'
  Preparing metadata (pyproject.toml): started
  Preparing metadata (pyproject.toml): finished with status 'done'
Building wheels for collected packages: pyspider
  Building wheel for pyspider (pyproject.toml): started
  Building wheel for pyspider (pyproject.toml): finished with status 'done'
  Created wheel for pyspider: filename=pyspider-1.0.0-py3-none-any.whl size=327229 sha256=e9b5a33845192ad655c3d3d599237fed9cd4bdde114a59235688508383a7ae0a
  Stored in directory: C:\Users\Administrator\AppData\Local\Temp\pip-ephem-wheel-cache-4ra2g9v6\wheels\8a\d5\70\4b040ec5d15ccb7d2be075a776a4d1f531ca068d49e8ddeb39
Successfully built pyspider
Installing collected packages: pyspider
Successfully installed pyspider-1.0.0
[notice] A new release of pip is available: 25.3 -> 26.0.1
[notice] To update, run: python.exe -m pip install --upgrade pip

## pyspider-public-smoke

- Status: passed
- Command: `C:\Python314\python.exe -c import sys; sys.path.insert(0, r'C:\Users\ADMINI~1\AppData\Local\Temp\tmpendebs4t\site'); from pyspider import __main__ as runtime; raise SystemExit(runtime._print_capabilities())`
- Details: {
  "command": "capabilities",
  "framework": "pyspider",
  "runtime": "python",
  "version": "1.0.0",
  "entrypoints": [
    "config",
    "crawl",
    "browser",
    "doctor",
    "export",
    "version",
    "run",
    "job",
    "async-job",
    "jobdir",
    "http-cache",
    "console",
    "sitemap-discover",
    "plugins",
    "selector-studio",
    "scrapy",
    "profile-site",
    "ultimate",
    "anti-bot",
    "node-reverse",
    "capabilities"
  ],
  "modules": [
    "research.job",
    "runtime.orchestrator",
    "runtime.async_runtime",
    "core.contracts",
    "core.incremental",
    "profiler.site_profiler",
    "extract.studio",
    "dataset.writer",
    "profiler.site_profiler",
    "advanced.ultimate",
    "antibot.antibot",
    "node_reverse.client",
    "node_reverse.fetcher"
  ],
  "runtimes": [
    "http",
    "browser",
    "media",
    "ai"
  ],
  "shared_contracts": [
    "shared-cli",
    "shared-config",
    "runtime-core",
    "autoscaled-frontier",
    "incremental-cache",
    "observability-envelope",
    "scrapy-project",
    "scrapy-plugins-manifest",
    "web-control-plane"
  ],
  "operator_products": {
    "jobdir": {
      "pause_resume": true,
      "state_file": "job-state.json"
    },
    "http_cache": {
      "status_seed_clear": true,
      "backends": [
        "file-json",
        "memory"
      ],
      "strategies": [
        "revalidate",
        "delta-fetch"
      ]
    },
    "browser_tooling": {
      "trace": true,
      "har": true,
      "route_mocking": true,
      "codegen": true
    },
    "autoscaling_pools": {
      "frontier": true,
      "request_queue": "priority-queue",
      "session_pool": true,
      "browser_pool": true
    },
    "debug_console": {
      "snapshot": true,
      "tail": true,
      "control_plane_jsonl": true
    }
  },
  "control_plane": {
    "task_api": true,
    "result_envelope": true,
    "artifact_refs": true,
    "graph_artifact": true,
    "graph_extract": true
  },
  "kernel_contracts": {
    "request": [
      "core.models.Request"
    ],
    "fingerprint": [
      "core.contracts.RequestFingerprint"
    ],
    "frontier": [
      "core.contracts.AutoscaledFrontier"
    ],
    "scheduler": [
      "scheduler.Scheduler"
    ],
    "middleware": [
      "core.contracts.MiddlewareChain"
    ],
    "artifact_store": [
      "core.contracts.FileArtifactStore"
    ],
    "session_pool": [
      "core.contracts.SessionPool"
    ],
    "proxy_policy": [
      "core.contracts.ProxyPolicy"
    ],
    "observability": [
      "core.contracts.ObservabilityCollector"
    ],
    "cache": [
      "core.incremental.IncrementalCrawler"
    ]
  },
  "observability": [
    "doctor",
    "profile-site",
    "selector-studio",
    "scrapy doctor",
    "scrapy profile",
    "scrapy bench",
    "prometheus",
    "opentelemetry-json"
  ]
}
