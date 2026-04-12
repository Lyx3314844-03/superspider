# Marketplace Surface

The repository does not claim a public third-party marketplace yet, but it now carries a formal marketplace surface for plugins, starters, and extension governance.

## Marketplace Scope

- plugin catalog
- extension lifecycle rules
- starter templates
- migration guidance
- support and contribution paths

## Current Repository-Owned Surfaces

- `contracts/integration-catalog.json`
- `docs/PLUGIN_GOVERNANCE.md`
- `docs/STARTERS.md`
- `MIGRATION.md`
- `docs/SUPPORT.md`

## Verification

Run:

```bash
python verify_ecosystem_marketplace.py --json --markdown-out artifacts/ecosystem-marketplace.md
```
