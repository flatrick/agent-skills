# Survey: inspection and interview

The survey has one job.
It finds **every resource that two concurrent test runs could both change**, and learns how the code finds each one.
A resource the survey misses comes back later as an intermittent failure, and costs far more to find then.

## Inspect before you ask

Read-only.
Search for exact anchors with the fastest text-search tool available, and read files only where a match needs context.

| Look for | Typical anchors |
|---|---|
| Test projects and runners | test framework packages, `*.runsettings`, `pytest.ini`, `jest.config`, CI pipeline files |
| Database endpoints | `connectionString`, `Data Source=`, `Server=`, `jdbc:`, `DATABASE_URL`, ORM config |
| Cross-database references | three- and four-part names, `USE <db>`, database links, linked servers |
| Schema source | migration folders, schema scripts, SQL projects, dacpac, DB build scripts |
| File system | absolute paths, drive letters, UNC paths, `/tmp`, temp-dir calls, import/export/drop folders |
| Network endpoints | hosts, ports, FTP/SFTP/SMTP/HTTP clients, queues, message brokers, hard-coded `localhost:<port>` |
| Installed things | service installers, IIS/web server config, scheduled tasks, cron, COM/registry registration, GAC |
| Global identifiers | fixed keys and names in test data, singleton or config rows, sequences, mutex and pipe names |
| Cleanup | teardown that truncates or deletes by pattern rather than by the IDs the test created |
| Time and randomness | wall-clock dependence, time zones, unseeded random values |
| Build outputs | output paths outside the worktree, post-build copies, shared caches |

For each hit, note whether the value comes from **config**, **code**, **test code**, **SQL**, or **data**.
That one fact usually decides the cheapest isolation pattern.

## Interview

Ask in rounds of **at most four questions**.
Give concrete, mutually exclusive options and always leave room for free text.
Use the harness's structured question tool when it has one; otherwise number the questions and their options.

From the second round on, start with a short playback of what you now believe.
The operator corrects it, and that correction is often the most valuable answer of the round.

Keep going until the operator says they are ready.
Include "Are we ready, or keep asking?" as one question when the inventory looks complete.
Don't decide readiness yourself, and don't put a design in the playback.

### Question bank

Pick what the inspection left open.
These are the questions that changed the design in practice.

**Collisions**
- What does a collision look like today: wrong or flaky results, blocking or deadlocks, timeouts, or people deliberately taking turns?
- Do the tests pass reliably when only one run happens at a time? If they do, isolation alone may be enough, without rewriting tests.

**Data and schema**
- Do branches change the schema? If they do, each environment needs to be built from *its* branch, not just separately.
- Can the schema be built from nothing with one command, and how long does it take? Or does it only upgrade an existing copy?
- Do names have to stay fixed (hard-coded database names, cross-database queries)? That rules out renaming and calls for separate instances.
- How do tests get data: a pre-seeded database, each test creating its own, or order dependence between tests?
- Which instance-level objects matter: logins, jobs, linked servers, server configuration, server-name checks?
- Does code inside the database reach outside it (files, network, shell)?
- How large is a from-scratch database compared with a long-lived one?

**Files and endpoints**
- Which folders do the code under test and the tests themselves read or write? Through which protocol? And do tests touch the same files directly on disk?
- Where does each endpoint's host, port, credentials, and path come from? Endpoints stored as *test data* are easy to miss, because the code reads them from the database.
- Can the server software behind each endpoint run as several copies (ports, config files, user home folders)?

**Processes**
- Are services, sites, or daemons installed for tests, or do tests call the same code in-process?
- Does anything run in the background during tests (jobs, schedulers, watchers)?

**Platforms**
- Which operating systems do the product, the developers' machines, and the CI agents run on? Does anyone use a different one from the rest?
- Which shells, and which versions of the key programs, does each have? For example: Windows PowerShell 5.1 or PowerShell 7, GNU or BSD command-line tools, the database engine's version and edition.
- Is any part of the product tied to one platform (for example Windows Services, IIS, launchd, systemd)?

**People and machines**
- Who will use the result: one person or a team? On what hardware, and how many concurrent runs?
- What may developers do on their machines: administrator rights, install database engines, Hyper-V or other virtualization, containers (and their licensing)?
- Which harness, or harnesses, will run the agents?

**The loop**
- How long does a build take, and a full test run? Do agents run the whole suite or subsets?
- Which tests are trusted, and which are ignored as flaky?

## Output

Write to the working record:

1. **Inventory**: one row per shared resource, with how it is found (config, code, data), who uses it (code under test, tests, both), and the collision it causes.
2. **Platforms**: each platform the workflow must support (product, developers, CI), with shell and key tool versions, each marked confirmed or assumed.
3. **Baseline**: build time, fastest useful subset, full suite time, flakiness rate, with the platform, versions, and date.
4. **Unknowns**: anything not yet answered or verified, each with how to settle it.
5. **Playback**: a short prose summary that the operator has confirmed.
