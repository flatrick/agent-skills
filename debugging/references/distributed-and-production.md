# Distributed and production systems

Preserve safety and customer impact before pursuing a perfect reproduction.
Prefer read-only queries, existing telemetry, traffic replay into isolated systems, and narrow reversible probes.
Follow incident and change-control authority; diagnosis does not authorize production mutation.

Do not terminate processes, restart services, change production configuration, deploy code, delete data, or contact customers merely to test a hypothesis.
If a disruptive action is necessary, state its expected diagnostic value, blast radius, rollback method, and required authorization.
Wait for that authorization.

Build a request or event path across clients, gateways, services, queues, stores, and external dependencies.
Record deployment versions, feature flags, routing, retries, timeouts, cancellation, idempotency keys, consistency model, replication lag, and clock uncertainty.

Distinguish original failures from retry amplification and recovery behavior.
Check for partial success, duplicate delivery, reordering, split views of state, stale reads, poison messages, backpressure, cascading saturation, and control-plane or data-plane divergence.

Absence in one service's telemetry does not prove the event never occurred.
Confirm instrumentation coverage, sampling, retention, and correlation propagation.

## Sources

- [Google SRE, Effective Troubleshooting](https://sre.google/sre-book/effective-troubleshooting/)
- [Google SRE, Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/)

