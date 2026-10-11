# Testability for legacy code

Isolation makes slow tests safe to run in parallel.
Testability makes most of them unnecessary for a typical change.
Treat the two as separate tracks, so that either can ship alone.

## Order by payoff

1. **Tiers.** Label existing tests by cost and dependencies (for example `fast`, `db`, `e2e`), using the framework's categories or traits. A fast tier that runs in seconds changes how agents work more than anything else.
2. **Subsets.** Give agents a documented way to run only the tests relevant to a change: by category, by namespace or folder, by changed project. The full suite remains the gate before merge.
3. **Characterization tests** before refactoring anything. Pin down what the code does today, including behavior that looks wrong, so that refactoring can't change it unnoticed. Golden-master or approval tests are cheap ways to cover large untested areas.
4. **Seams**, added where a change is planned anyway. Don't refactor for testability on its own schedule.
5. **Fixing test data hygiene**: replace fixed keys with generated ones, and broad cleanup with deleting by recorded IDs. This lets tests run in parallel *within* a slot later, but isolation must not wait for it.

## Seams that work in legacy code

Choose the smallest one that breaks the dependency in the test.

- **Parameterize the constructor or method**: pass in the dependency (clock, file system, endpoint, connection), and default to the existing behavior.
- **Extract interface**, for a class the code under test calls. Only where a fake is genuinely simpler than the real thing.
- **Subclass and override** a protected method that does the I/O. Useful when constructors are too entangled to change.
- **Sprout** a new, tested method or class for new logic, and call it from the old code. **Wrap** an old method with a new one that adds behavior around it.
- **Link or config seams**: swap an implementation through configuration, rather than editing call sites.

For each seam, state what the test now proves and what it no longer proves.
The end-to-end tier stays as the check that the seams didn't hide an integration defect.

## Loop measurements

Measure the loop in the terms an agent experiences it, before and after:

- time from edit to first relevant test result;
- full suite time in one slot;
- flakiness: failures per N repeated runs of an unchanged tree;
- how many concurrent runs succeed together.

Report each number with platform, tool versions, and date.
