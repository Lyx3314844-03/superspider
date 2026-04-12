# Platform Demo

This is a minimal deployment-oriented demo for the public-facing Spider Framework Suite web surfaces.

## What It Serves

- suite homepage from `web-ui/index.html`
- public benchmark page from `web-ui/public-benchmarks/index.html`
- `gospider` API server with Redis
- `pyspider` web control plane
- `javaspider` web control plane
- `rustspider` web control plane

## Start

```bash
docker compose up --build
```

Then open:

- `http://localhost:8088/`
- `http://localhost:8088/docs/`
- `http://localhost:8088/public-benchmarks/`
- `http://localhost:8080/api/v1/health`
- `http://localhost:5000/api/tasks`
- `http://localhost:7070/api/tasks`
- `http://localhost:9090/api/tasks`

## Why It Exists

This is not the full production topology.
It is the smallest four-runtime multi-service shell for showcasing the suite as a product platform.
