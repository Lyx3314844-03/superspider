# Industry Proof Surface

This repository separates proof surface from external proof claims.

## Current Proof Surface

- public benchmark site
- benchmark trend history
- runtime stability history
- blackbox and release artifacts
- repository validation stories in `docs/ADOPTERS.md`

## What Still Requires External Time

- long-duration soak under third-party traffic
- public adopter case studies
- issue/support history from external users
- broader benchmark history depth

## Verification

Run:

```bash
python verify_industry_proof_surface.py --json --markdown-out artifacts/industry-proof-surface.md
```
