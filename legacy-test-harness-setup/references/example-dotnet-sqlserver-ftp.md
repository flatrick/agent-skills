# Worked example: .NET Framework, SQL Server, and FTP on Windows

Survey and design from an operator interview on 2026-10-11.
Nothing here was measured, and no step was carried out.
The value is in how the answers drove each decision.
Your system's answers will differ.

## Survey

**Stack.** .NET Framework 4.8 (about 70% VB.NET, the rest C#), on Windows only. It depends on pre-4.0 libraries, Windows Services code, and IIS. SQL Server hosts SQLCLR assemblies with `UNSAFE` / `EXTERNAL_ACCESS`.

**Platforms.** Windows only, for the product, every developer, and CI. The operator confirmed this, so single-platform tooling (PowerShell) is acceptable here. Which PowerShell (5.1 built in, or 7 installed) every machine has was not yet confirmed. The tooling must either target 5.1 or check for `pwsh`.

**Use.** A team, each person on one Windows workstation, wants 2–3 concurrent agent sessions in separate git worktrees. Developers have local administrator rights, and SQL Server Developer Edition is allowed. Docker Desktop isn't licensable for the company.

| Shared resource | How code finds it | Used by | Collision |
|---|---|---|---|
| SQL Server instance with a *set* of databases | connection string in config; database names hard-coded; cross-database queries | code under test and tests | data overwritten; one branch's schema change hits every session |
| Local FTP server | partner host, port, user, password, and path hard-coded in **test helpers** and inserted into the database as partner data | code under test (FTP); test helpers (directly on disk) | files picked up or deleted by the other run |

**Operator answers that decided the design:**
- The tests pass reliably when only one run happens at a time, so isolation is enough and test rewrites aren't needed.
- Each test creates its own data, but uses fixed keys and broad cleanup, so concurrent runs in one database are guaranteed to collide.
- Branches change schema. The schema scripts build all databases from nothing with one command in minutes, and the target instance is a parameter.
- Only one SQL login is needed, and the build doesn't create it yet.
- No code inside SQL Server reaches files or the network.
- The Windows Services are not installed for tests. NUnit calls the same code in-process.
- The FTP server software can run as several copies on different ports. Its account config lives outside the repo, but can move into it.
- Builds don't clash. The suite is short, and agents run all of it.

**Corrected assumptions.** The first design assumed installed services and proposed per-slot service installs. The operator corrected this, which removed a whole workstream. This is why the survey keeps asking before designing.

## Design

| Decision | Choice | Rests on |
|---|---|---|
| Isolation pattern | fixed pool of 3 slots | expensive resources (instances), few concurrent runs |
| Database | SQL Server Developer named instance per slot (`.\E2E0N`), max memory capped | names hard-coded and cross-database, so separate instances; Developer Edition allows many instances and full CLR |
| Containers | rejected | Docker Desktop licensing; Linux SQL Server supports only `SAFE` CLR; no vendor Windows SQL Server images |
| FTP | one FTP server copy per slot on port `2100+N`, root `C:\e2e\slot0N\ftp\`, accounts from a repo template | the product supports multiple copies; credentials and relative paths stay the same in every slot |
| Per-worktree truth | untracked `.e2e-slot.json` (slot, instance, FTP port, FTP root, schema hash) | read the same way by agents, Visual Studio, and console runners |
| Connection string | custom `KeyValueConfigBuilder` in the test project's `app.config` | production code keeps reading `ConfigurationManager` unchanged |
| FTP constants | test helpers read host, port, and root from the slot file | they were hard-coded in test code only |
| Schema | `rebuild` runs the from-scratch build from the worktree's own scripts; the fixture compares the schema hash | branches change schema |
| Guard rails | assembly-level `[SetUpFixture]`: no slot file means fail; stale hash means fail; named mutex `Global\e2e-slot-0N`; print the slot first | never fall back to shared state |
| Lease | `C:\e2e\slot0N\lease.json` created with `FileMode.CreateNew` | atomic claim |
| Untouched | the default instance and the original FTP server | the operator's manual work continues as before |

**Rollout:**
1. Spike one slot by hand, and run the full suite against it.
2. Change the code: login creation, config builder, helper constants, fixture.
3. Script provisioning, claim, rebuild, and release; add slots.
4. Move the FTP config into the repo; write the agent docs.

**Planned done check:**
- Two worktrees on different slots run the full suite at the same time, green three times in a row.
- A schema change rebuilt in one slot leaves the other slot's schema unchanged.
- The guard rails trigger on purpose.
- The default environment shows no changes.
