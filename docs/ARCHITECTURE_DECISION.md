# Architecture Decision

This document records the intended architecture shape for the four primary
runtime frameworks in the Spider Framework Suite:

- `pyspider`
- `gospider`
- `rustspider`
- `javaspider`

It exists to stop the suite from drifting between two different identities:

- one unified operator-facing product family
- four unrelated language ports trying to be equally full-stack

## Core Decision

The suite is a **shared-contract product family**, not four equal-depth ports.

That means:

- the runtimes must share one operator mental model
- the runtimes must share one config / job / artifact / control-plane contract
- the runtimes do **not** need identical internal depth in every subsystem

In practice, the suite should optimize for:

- common CLI shape
- common config shape
- common result envelope
- common task/control-plane behavior
- common operator products

It should not optimize for:

- perfect feature symmetry at all times
- identical implementation strategies across languages
- forcing every runtime to become an equal-weight general-purpose framework

## Reference Runtime

`pyspider` is the reference runtime for authoring and project-model richness.

Reasons:

- it already has the richest project runner shape
- plugin and project authoring fit Python naturally
- AI/extract/research orchestration is strongest there
- it is the easiest place to prove new product surfaces before back-porting

Implication:

- new suite-level product concepts should usually be proven in `pyspider` first
- other runtimes should adopt the contract once it is clear and useful
- the suite should avoid pretending every runtime must lead every capability at the same time

## Runtime Roles

Each runtime should have a primary role.

### PySpider

Primary role:

- reference runtime
- richest project authoring surface
- research / AI / extraction orchestration runtime

Should lead:

- plugin model
- project runner model
- AI-assisted extraction flows
- rapid iteration surfaces

Should not be forced to lead:

- lowest-latency binary deployment
- strongest typed boundary guarantees

### GoSpider

Primary role:

- binary-first operator/runtime surface
- concurrency-heavy execution
- control-plane / queue / batch-service friendliness

Should lead:

- control-plane integration
- service packaging
- distributed worker execution
- high-throughput batch orchestration

Should not be forced to lead:

- deepest project authoring model
- most feature-rich browser/runtime ergonomics

### RustSpider

Primary role:

- strongest bounded runtime
- type-driven contract enforcement
- high-confidence binary shipping

Should lead:

- feature-gated deployability
- strict runtime boundaries
- preflight / readiness rigor
- high-confidence artifact and contract discipline

Should not be forced to lead:

- richest plugin/project ergonomics
- fastest experimentation loop

### JavaSpider

Primary role:

- workflow-centric runtime
- audit / connector / session surface
- enterprise integration path

Should lead:

- workflow execution and replay
- auditability
- enterprise ecosystem integration
- connector/session-heavy scenarios

Should not be forced to lead:

- fastest local experimentation
- lowest-friction binary deployment

## Layering Model

The suite should be reasoned about in two major layers.

### Layer 1: Shared Product Contract

This layer must stay aligned across runtimes.

- unified CLI contract
- shared config contract
- shared `JobSpec` / normalized execution model
- shared result envelope and artifact refs
- shared task/control-plane web surface
- shared operator products:
  - `jobdir`
  - `http_cache`
  - `browser_tooling`
  - `autoscaling_pools`
  - `debug_console`

This is the layer users should rely on for portability.

### Layer 2: Runtime-Specialized Depth

This layer is allowed to differ by language.

- site-specific extractors
- browser implementation details
- media parsing depth
- plugin ergonomics
- anti-bot internals
- live external-service integrations

This is the layer where each runtime is allowed to specialize.

## Symmetry Policy

The suite should pursue **contract symmetry**, not **implementation symmetry**.

Good symmetry:

- same command names
- same JSON/result shapes
- same config concepts
- same release/readiness metrics

Bad symmetry:

- building the same subsystem four times just to claim parity
- adding weak runtime-specific clones of capabilities that are only strong in one runtime
- expanding every runtime equally before one runtime has proven the product surface is worth keeping

## Product Boundary

The suite is not just “crawler libraries”.

It is also an operator platform with:

- control-plane APIs
- artifact surfaces
- replay/benchmark evidence
- release/readiness verification
- optional live external-service validation

This means architecture work should prioritize:

- operator trust
- evidence collection
- contract stability

over:

- language-pure elegance inside one runtime

## Current Known Weaknesses

The suite currently has a few structural risks.

- capability surface is broader than the product story, so discovery can lag implementation
- report/verification maturity can outpace end-user feature maturity
- runtime roles are visible in practice but not always explicit in docs
- “all runtimes should be full-stack” remains a temptation and creates maintenance drag

## Non-Goals

The following are explicitly not goals.

- keeping every runtime equally deep in every subsystem
- guaranteeing that a capability reaching one runtime must immediately ship in all others
- preserving legacy compatibility-only surfaces when they weaken the shared product story
- allowing runtime-specific output or operator surface drift without a contract reason

## Design Consequences

When adding or changing features:

1. decide whether the change belongs to the shared product contract or to runtime-specialized depth
2. if it is a shared product concept, prove it in the reference path and then align other runtimes
3. if it is runtime-specialized depth, do not fake parity unless there is a real operator need
4. preserve one operator-facing story even when implementation depth differs

## Decision Summary

The Spider Framework Suite should behave like **one operator-facing suite with
specialized runtimes**, not like **four equal-depth language ports**.

That is the standard future changes should be judged against.
