# Isolation patterns

The goal is that a single test run behaves the same whether or not other runs are happening.
Copy what changes.
Share only what nobody writes.

## Choosing a pattern per resource

Prefer the cheapest pattern that removes the collision.
Earlier rows are cheaper but need more control over the code.

| Pattern | Use when | Costs |
|---|---|---|
| **Unique keys in a shared store** | Runs share one database or folder, tests create their own rows or files, and their keys and names can be made unique (run ID prefix, generated keys) | Test changes. Doesn't help with schema differences between branches or broad cleanup |
| **Fake or in-process substitute** | The resource is an external endpoint whose behavior is simple and well understood | Tests stop proving the real integration. Keep at least one run against the real thing |
| **Per-worktree copy** | The resource is cheap and fast to create: a folder, a file database, a process on a free port, or a database on an existing server when its name is configurable and it builds in seconds | Creation time on every new worktree; cleanup of abandoned copies |
| **Fixed pool of slots** | The resource is expensive to create, such as a whole database *server instance* (needed when database names are hard-coded) or a server installation, and the number of concurrent runs is small | Provisioning per machine, plus a lease mechanism |
| **Serialization** | Nothing else is practical, or the resource is a true singleton (licensed hardware, an external sandbox account) | Waiting. Use a lock with a timeout, never people taking turns |

Several resources often move together.
In that case, bundle them into one **slot**: a numbered environment holding a copy of every expensive resource.

## Slots

A slot is permanent and numbered (01, 02, …), and a worktree leases one slot at a time.
In slot N, only the **values that must differ** vary, such as instance name, port, and disk root.
Everything the code hard-codes stays the same inside every slot, including database names, account names, and relative paths.
This is what makes slots cheap for legacy code: hard-coded values stop mattering once each slot holds its own copy of whatever they point to.

### Lease

- One lease file per slot in a machine-wide slot directory, created with an atomic *create-new* operation. Two concurrent claims can't both succeed.
- The lease records the worktree path and the time. `status` lists slots, owners, and leases whose worktree no longer exists.
- Release deletes the lease. A stale lease (worktree gone) can be reclaimed, but only by an explicit command, never silently.

### Single source of truth per worktree

The claim writes one **untracked** file at the worktree root, for example `.test-slot.json`, holding every value that varies per slot.
Every runner reads that file: agents, the IDE's test explorer, the console runner, and scripts.
Environment variables are a weaker choice, because each launcher (terminal, IDE, harness, CI) inherits them differently, and a missing variable silently means "use the default".
The test assembly can find the file by walking up from its output directory to the worktree root.

### Getting values into legacy configuration

Avoid forking committed config files per worktree.
Prefer a hook that rewrites values at load time:

- **.NET Framework 4.7.1+:** configuration builders (`Microsoft.Configuration.ConfigurationBuilders.*`). A small custom `KeyValueConfigBuilder` can read the slot file.
- **Java:** a system-property or profile overlay loaded by the test bootstrap.
- **Node, Python, Ruby, and others:** the test bootstrap loads the slot file before the app's config module is first imported.
- **Values in test code:** replace the constants with reads from the slot file. These are often endpoint constants in test helpers.
- **Values stored as data:** if tests insert endpoints into the database, the test helpers must take them from the slot file.

### Schema per branch

When branches change the schema, a slot must be built **from the worktree's own scripts**.
Record a hash of the schema sources in the slot file when you build.
The test fixture compares it on start-up, and stops with "rebuild your slot" when they differ.
Normalize line endings before hashing, so the hash doesn't depend on how the file was checked out.

### Reset between runs

If the tests pass reliably when run alone, a clean starting state may be all a run needs.

- Database snapshots (for example SQL Server `CREATE DATABASE … AS SNAPSHOT OF` and `RESTORE … FROM DATABASE_SNAPSHOT`) revert in seconds. A revert needs exclusive access, and SQL Server allows only one snapshot per database for a revert.
- If a from-scratch build takes minutes, rebuilding per branch change and resetting per run is usually the right split.
- Wipe and recreate per-slot folders at the same point.

### Guard rails in the test fixture

At start-up, before any test runs:

1. Fail if the slot file is missing. Never fall back to the shared default environment.
2. Fail if the schema hash is stale.
3. Hold a machine-wide named lock for the slot for the whole run, so a second run in the same slot waits with a timeout and a clear message.
4. Print slot, endpoints, and paths as the first line of output, so a wrong slot is visible immediately.

## Containers and VMs

Consider them as a pattern for the whole slot, not per resource.

- **Containers** isolate everything, including hard-coded absolute paths, but the whole stack must run in them. Check the licensing of the container tooling for the organization, the engine's platform support (for example, SQL Server on Linux supports only `SAFE` CLR assemblies), and whether the vendor still publishes images.
- **One VM per slot** needs no code change at all. Use a checkpoint as the reset point, and run tests remotely. It costs more memory and is slower to set up. It is the fallback when hard-coded absolute paths can't be parameterized.

## What not to share, even when it looks harmless

- Build outputs written outside the worktree.
- Machine-wide registrations (COM, GAC, services), when branches can change what they register.
- Ports picked by convention: each slot gets its own.
- Temp directories with fixed names.
