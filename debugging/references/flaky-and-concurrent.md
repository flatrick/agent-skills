# Flaky and concurrent failures

Do not collapse an intermittent outcome into a single pass or fail.
Define the failure signature, trial conditions, trial count, and observed rate with its time window.

Control or record randomness, scheduling, clocks, time zones, resource pressure, test order, shared state, network conditions, and retries.
Run passing and failing populations under the same observation setup.
Instrumentation that changes the rate is evidence of a timing-sensitive boundary, not proof of a race.

For concurrency failures, test ordering hypotheses with barriers, deterministic schedulers, event logs, lock diagnostics, thread dumps, race detectors, and watchpoints.
Draw a happens-before claim only from synchronization or timestamp evidence whose clock properties are known.
Wall-clock timestamps across hosts do not establish precise order without a clock-error bound.

For flakes, report counts and conditions.
"Could not reproduce" means only that the failure did not occur in the recorded trials.

## Sources

- [Google Testing Blog, Test Flakiness](https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html)
- [Lamport, Time, Clocks, and the Ordering of Events in a Distributed System](https://lamport.azurewebsites.net/pubs/time-clocks.pdf)
