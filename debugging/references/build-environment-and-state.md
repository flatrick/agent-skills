# Build, environment, and state failures

Compare the failing system with a known-good system across these boundaries:

- source revision, generated files, compiler, SDK, linker, build flags, architecture, and artifact identity;
- direct and transitive dependencies, lockfiles, registries, mirrors, resolution rules, and native libraries;
- configuration source, precedence, defaults, secrets references, feature flags, locale, time zone, and environment variables;
- cache keys, cache provenance, invalidation, incremental outputs, and clean-build behavior;
- schema version, migration history, compatibility window, data shape, encoding, and invariants;
- persistent state, permissions, ownership, filesystem semantics, and external service state.

Hash artifacts when identity matters, but normalize only authored text at ingestion.
Preserve emitted artifacts byte for byte.
A clean rebuild or cache clear is a differential test, not a diagnosis; identify which stale or mismatched artifact caused the behavior.

Do not expose secret values in records.
Record the configuration key, source, presence, version, or fingerprint needed to compare behavior.

## Sources

- [Reproducible Builds documentation](https://reproducible-builds.org/docs/)
- [The Twelve-Factor App, Config](https://12factor.net/config)

