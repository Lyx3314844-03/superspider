# Deprecation Policy

Legacy runtime paths may remain temporarily for compatibility, but they should be isolated and removed deliberately.

Deprecation rules:

- new work lands on the canonical frontier-backed runtime path
- legacy paths should be marked as compatibility-only, not recommended
- removals require a migration note and at least one release-cycle warning
- capability output must not claim removed surfaces

Deprecation workflow:

1. mark the legacy surface in docs and release notes
2. add or update the migration path
3. keep verification green on the canonical path
4. remove the legacy surface only after replacement evidence is stable
