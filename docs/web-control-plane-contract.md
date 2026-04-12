# Web Control Plane Contract

This repository treats the web task surface for `javaspider`, `gospider`, `rustspider`, and `pyspider` as one shared operator contract.

## Canonical Endpoints

Each runtime should expose a task-oriented control plane under:

- `GET /api/tasks`
- `POST /api/tasks`
- `GET /api/tasks/{id}`
- `POST /api/tasks/{id}/start`
- `POST /api/tasks/{id}/stop`
- `DELETE /api/tasks/{id}`
- `GET /api/tasks/{id}/results`
- `GET /api/tasks/{id}/logs`
- `GET /api/stats`
- `POST /api/graph/extract`
- `POST /api/v1/graph/extract`

Legacy aliases may remain for backward compatibility, but the graph surface should support both `/api/graph/extract` and `/api/v1/graph/extract`.

## Auth

Control-plane API routes may be protected by bearer-token authentication.

Recommended behavior:

- protect `/api/*` routes
- keep non-API HTML pages accessible unless explicitly configured otherwise
- accept `Authorization: Bearer <token>`

RustSpider currently supports API auth through environment-driven token configuration.

## List and Detail Shape

Task objects should include:

- `id`
- `name`
- `status`
- `stats`

Recommended fields:

- `url`
- `running`
- `results`
- `logs`
- `artifacts`

## Result Envelope

`GET /api/tasks/{id}/results` should return:

```json
{
  "success": true,
  "data": [],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 0
  }
}
```

The canonical result protocol should align with:

- `contracts/result-envelope.schema.json`
- `contracts/result-artifact.schema.json`
- `contracts/graph.schema.json`

Shared routing and capability matching should align with the vendored SuperSpider V2 control-plane surface under:

- `superspider_control_plane/compiler.py`
- `superspider_control_plane/dispatcher.py`
- `verify_superspider_control_plane.py`

Each result item should aim to include:

- `id`
- `task_id`
- `url`
- `final_url`
- `status`
- `http_status`
- `content_type`
- `title`
- `bytes`
- `duration_ms`
- `created_at`
- `artifacts`

When graph extraction is available, runtimes should attach a `graph` artifact under:

```json
{
  "artifacts": {
    "graph": {
      "kind": "graph",
      "path": "artifacts/control-plane/graphs/<runtime>-<task>-<result>.json",
      "root_id": "document",
      "stats": {
        "total_nodes": 0,
        "total_edges": 0
      }
    }
  }
}
```
- `artifacts`
- `artifact_refs`

## Graph Envelope

`POST /api/graph/extract` and `POST /api/v1/graph/extract` should return:

```json
{
  "success": true,
  "data": {
    "root_id": "document",
    "nodes": {},
    "edges": {},
    "stats": {
      "total_nodes": 0,
      "total_edges": 0
    }
  }
}
```

The request body should accept either:

- `html`
- `url`

When task execution captures HTML, runtimes should persist a `graph` artifact automatically and expose it through both:

- `artifacts.graph`
- `artifact_refs.graph`

## Log Envelope

`GET /api/tasks/{id}/logs` should return:

```json
{
  "success": true,
  "data": [],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 0
  }
}
```

Each log item should aim to include:

- `id`
- `task_id`
- `level`
- `message`
- `created_at`

## Lifecycle Expectations

- `start` should trigger real background work, not only update status.
- `stop` should request cancellation and record a stop log.
- A completed run should produce at least one result or one failure record.
- Logs should capture creation, start, stop/failure, and finish transitions.

## Routing Expectations

- control-plane routing should compile shared `contracts/job.schema.json` jobs before dispatch.
- worker selection should be derived from runtime `capabilities` surfaces, not a hand-maintained static table.
- capability matching should cover `http`, `browser`, `media`, `ai`, and `graph`.
- `verify_superspider_control_plane.py` should prove compiler and dispatcher parity against the four runtime capability payloads.

## Auth Expectations

Control-plane APIs may run in open mode for local development, but when auth is enabled:

- `Authorization: Bearer <token>` should be accepted
- `X-API-Token: <token>` may be accepted as a compatibility header
- unauthorized API requests should return `401`
- non-API pages may remain public for local/operator convenience
