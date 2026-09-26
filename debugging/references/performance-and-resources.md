# Performance and resource failures

Define the service-level symptom and workload before profiling.
Record latency distribution, throughput, concurrency, input size, warm-up, cache state, hardware, limits, and time window.
A mean alone can hide the failing tail.

Separate demand, utilization, saturation, and errors.
Follow the constrained resource rather than the busiest-looking metric.
Check CPU run queues, allocation and retention, garbage collection, I/O waits, file descriptors, threads, sockets, connection pools, queue depth, storage capacity, and external quotas as relevant.

Compare against a passing baseline under the same load shape.
Use profiles, traces, and controlled load steps to find where marginal demand causes nonlinear delay or failure.
Account for observer overhead and coordinated omission in load tests.

For leaks, demonstrate growth after work completes or across equivalent cycles and identify the retention or unreleased resource path.
High steady usage alone is not a leak.

## Sources

- [Google SRE Workbook, Implementing SLOs](https://sre.google/workbook/implementing-slos/)
- [Gil Tene, How NOT to Measure Latency](https://www.infoq.com/presentations/latency-pitfalls/)

