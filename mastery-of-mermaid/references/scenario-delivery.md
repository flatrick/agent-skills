# Delivery, from a branch to production and back

**Use for:** how a change travels from a developer's branch into production, and how it is reversed when it goes wrong.
Branching strategy, hotfixes, required checks, environment promotion, progressive rollout, feature flags, zero-downtime schema change, deployment topology, and release schedules.
**Avoid for:** how the running system serves a request.
That is `common-patterns.md`, which also holds the basic linear CI/CD pipeline this file deliberately does not repeat.
Per-type syntax lives in the sibling file for each diagram type.

Find the scenario your reader is actually asking about, copy the block, and replace the names.
Every example states the one question it answers, so if that is not the question in the room, keep scrolling.

---

### Where do I branch from, and what gets tagged

**Answers:** "I am starting work.
What do I branch off, where does it merge back, and which commit becomes the release?"
**Use when:** onboarding a new engineer, or writing the paragraph in CONTRIBUTING that says how work starts and ends.
**Don't use when:** the reader wants to know what runs where once the tag exists.
Use the deployment topology example below.
**Detail level:** L1

<!-- mermaid-render: id="scenario-delivery--block1" -->
```mermaid
gitGraph
   accTitle: Feature branches, a release branch, and a tagged release
   accDescr: Two feature branches merge into main. A release branch is cut from main for version bump and notes, then merged back, and that merge commit carries the release tag.
   commit id: "2.4.0 baseline" tag: "v2.4.0"
   branch feature/checkout-retry
   commit id: "retry policy"
   commit id: "retry tests"
   checkout main
   merge feature/checkout-retry
   branch feature/cart-totals
   commit id: "totals rounding"
   checkout main
   merge feature/cart-totals
   branch release/2.5
   commit id: "bump version"
   commit id: "release notes"
   checkout main
   merge release/2.5 tag: "v2.5.0"
```
<img src="rendered/scenario-delivery--block1.svg" alt="scenario-delivery--block1" width=675px/>

**Adapt it:** the branch names and commit ids are placeholders, swap them for two real features from your last release.
If you deploy straight from main, delete the `release/2.5` branch and its two commits and tag the last merge into main instead.
If you run a long-lived `develop` branch, add it as the first branch off main and point the feature branches at it.
Keep the tag on the commit your pipeline actually builds from, because that is the fact readers get wrong.

---

### The hotfix path, next to the normal path

**Answers:** "Production is broken.
Where does the fix branch from, and what do I have to merge it back into so the next release does not undo it?"
**Use when:** writing the incident runbook, or explaining why a hotfix is not just a small feature.
**Don't use when:** the question is who approves the hotfix and what the freeze rules are.
Use the swimlane in the next example, with a hotfix lane.
**Detail level:** L2

<!-- mermaid-render: id="scenario-delivery--block2" -->
```mermaid
gitGraph
   commit id: "2.5.0 release" tag: "v2.5.0"
   branch feature/address-book
   commit id: "address form"
   checkout main
   branch hotfix/2.5.1-null-tax
   commit id: "guard null tax rate" type: HIGHLIGHT
   commit id: "regression test"
   checkout main
   merge hotfix/2.5.1-null-tax tag: "v2.5.1"
   checkout feature/address-book
   merge main id: "pull hotfix into the feature branch"
   commit id: "address validation"
   checkout main
   merge feature/address-book tag: "v2.6.0"
```
<img src="rendered/scenario-delivery--block2.svg" alt="scenario-delivery--block2" width=620px/>

**Adapt it:** the highlighted commit is the actual fix, keep it highlighted so a reader spots it in one second.
The load-bearing edge is `merge main` back into the in-flight feature branch.
Delete that and the diagram stops explaining why the bug came back in v2.6.0.
If you cut hotfixes from the release tag rather than from main, add `branch hotfix/... ` right after the tagged commit and merge it into both main and the release branch.

---

### A required check is red, who unblocks it

**Answers:** "CI failed on my pull request.
Do I fix it, or am I waiting on somebody?"
**Use when:** documenting required checks, code owner rules, and who may grant a waiver.
**Don't use when:** only the order of pipeline stages matters and ownership does not.
Use the linear CI/CD pipeline in `common-patterns.md`.
**Detail level:** L2

<!-- mermaid-render: id="scenario-delivery--block3" -->
```mermaid
swimlane-beta TB
  accTitle: Who unblocks a failed required check
  accDescr: A pull request runs unit, scan and performance checks. A test or scan failure returns to the author. A performance regression instead goes to release management for a documented waiver before code owners can approve.
  subgraph Author
    open[Open pull request]
    fix[Push a fix]
    merge[Merge when all checks green]
  end
  subgraph CI [CI pipeline]
    unit[Unit and contract tests]
    scan[Dependency and secret scan]
    perf[Performance budget check]
  end
  subgraph Owners [Code owners]
    review[Review and approve]
  end
  subgraph Release [Release management]
    waive[Grant a documented waiver]
  end

  open --> unit
  unit -->|fail| fix
  unit -->|pass| scan
  scan -->|fail| fix
  scan -->|pass| perf
  perf -->|regression| waive
  perf -->|pass| review
  waive -->|waiver logged| review
  review -->|approved| merge
  fix --> unit
```
<img src="rendered/scenario-delivery--block3.svg" alt="scenario-delivery--block3" width=1400px/>

**Adapt it:** the lanes are the placeholders, replace them with the teams your org actually has.
Every cross-lane arrow is a handoff, so label each one with the condition that triggers it.
Add a lane only for a group that can block or unblock the merge, not for everyone who gets notified.
`swimlane-beta` needs Mermaid 11.16 or newer, so confirm your renderer before committing this one; a plain `flowchart` with the same nodes is the fallback if lanes will not draw.

---

### What has to be true before this build moves up

**Answers:** "The build passed in staging.
What has to happen before it is allowed into production?"
**Use when:** writing down the promotion rules, or proposing that one of the gates change.
**Don't use when:** the reader needs calendar dates rather than conditions.
Use the schedule example at the end of this file.
**Detail level:** L1

<!-- mermaid-render: id="scenario-delivery--block4" -->
```mermaid
flowchart LR
  accTitle: Promotion of one build from development to production
  accDescr: A single artifact is built once and promoted through development, staging and production. Each hop is guarded by a named gate, and a failed gate sends the change back to a new build rather than patching the environment in place.

  Build[Build artifact once, tag it]
  Dev[Development, auto-deploy every merge]
  G1{Contract tests and smoke pass?}
  Stage[Staging, production-shaped data]
  G2{Release manager approves the change log?}
  Prod[Production]
  Soak[Soak 30 minutes against the error budget]
  Good([Tag marked good for reuse])

  Build -->|promote| Dev
  Dev --> G1
  G1 -->|pass| Stage
  G1 -->|fail, never patch the environment| Build
  Stage --> G2
  G2 -->|approved| Prod
  G2 -->|held for the change freeze| Stage
  Prod --> Soak
  Soak --> Good
```
<img src="rendered/scenario-delivery--block4.svg" alt="scenario-delivery--block4" width=1400px/>

**Adapt it:** name your real environments and your real gates.
The point of the diagram is that one artifact moves and nothing is rebuilt per environment, so keep the single `Build` node even if you add environments.
Delete the `Soak` node first if you do not gate on an error budget.
Add a fourth environment as another pair of an environment node and a gate node, and stop at twelve nodes; past that, split the pre-production hops into their own diagram.

---

### How much traffic is on the new build

**Answers:** "We are halfway through a rollout.
What is being measured, and what makes us stop and go back?"
**Use when:** writing the rollout policy, or arguing about how long each step should bake.
**Don't use when:** exposure is controlled by a flag per user rather than by traffic share.
Use the feature flag state machine below.
**Detail level:** L2

<!-- mermaid-render: id="scenario-delivery--block5" -->
```mermaid
flowchart TB
  classDef producer fill:#90caf9,stroke:#1565c0,color:#0d47a1
  classDef consumer fill:#81c784,stroke:#2e7d32,color:#1b5e20
  classDef external fill:#90a4ae,stroke:#455a64,color:#263238
  classDef standalone fill:#ce93d8,stroke:#7b1fa2,color:#4a148c
  classDef edgeEnqueue stroke:#1565c0,stroke-width:2px
  classDef edgeConsume stroke:#2e7d32,stroke-width:2px
  classDef edgeExternal stroke:#455a64,stroke-width:1.5px
  classDef edgeSend stroke:#bf360c,stroke-width:2px

  Start[release-bot starts rollout of checkout-api v2.5.0]:::producer
  Shift[Shift traffic to the next step: 1, 10, 50, 100 percent]:::standalone
  Bake[Bake 10 minutes at the current step]:::consumer
  Metrics[(slo-dashboard: 5xx rate, p99 latency, saturation)]:::external
  Check{Inside the error budget?}:::standalone
  More{Steps remaining?}:::standalone
  Full[All traffic on v2.5.0, v2.4.1 kept warm for 24h]:::consumer
  Roll[Shift 100 percent back to v2.4.1]:::standalone
  Page[Page the on-call, freeze the pipeline]:::standalone

  Start e1@==> Shift
  Shift e2@--> Bake
  Bake e3@-.-> Metrics
  Bake e4@--> Check
  Check e5@-->|yes| More
  Check e6@-->|no| Roll
  More e7@-->|yes| Shift
  More e8@-->|no| Full
  Roll e9@-.-> Page

  class e1 edgeEnqueue
  class e2,e4,e5,e7,e8 edgeConsume
  class e3 edgeExternal
  class e6,e9 edgeSend

  %% Legend: blue = rollout starts; green = promote path; gray dotted = metric read; red = rollback and alert.
```
<img src="rendered/scenario-delivery--block5.svg" alt="scenario-delivery--block5" width=915px/>

**Adapt it:** the step percentages, the bake time and the three metrics are the placeholders, and they are the numbers your team will argue about, so put the real ones in.
The loop back from `Steps remaining?` to `Shift` is what keeps this at nine nodes instead of one node per step; do not unroll it.
Name the previous version explicitly in the rollback node, because "roll back" without a target is the instruction people get wrong at 3am.
Delete `Page` if rollback is automatic and silent, but then say so somewhere.

---

### Will anybody ever delete this flag

**Answers:** "This flag has been at 100 percent for a year.
What is supposed to happen to it?"
**Use when:** introducing a flag, or running a cleanup sweep and needing to show that the flag is not done until the code is gone.
**Don't use when:** you are showing traffic percentages during a single deploy.
Use the canary rollout above.
**Detail level:** L2

<!-- mermaid-render: id="scenario-delivery--block6" -->
```mermaid
stateDiagram-v2
    classDef debt fill:#ffcc80,stroke:#ef6c00,color:#bf360c
    classDef gone fill:#81c784,stroke:#2e7d32,color:#1b5e20

    [*] --> Added
    Added: Added, defaults off, both branches compiled
    Added --> Internal: allowlist the team
    Internal: Internal only
    Internal --> Ramping: team sign-off
    Ramping: Ramping, 1 then 10 then 50 percent
    Ramping --> FullyOn: 100 percent, two weeks clean
    Ramping --> Disabled: regression, flip off
    Disabled: Disabled, still in the code
    Disabled --> Ramping: fix shipped
    Disabled --> Removed: feature dropped, delete the new branch
    FullyOn: Fully on, old branch never runs
    FullyOn --> DefaultOn: flip the default, stop reading the flag service
    DefaultOn: Default on, flag still referenced
    DefaultOn --> Removed: delete the flag and the dead branch
    Removed: Removed from code and from the flag service
    Removed --> [*]

    class FullyOn,DefaultOn debt
    class Removed gone

    note right of FullyOn
      Flag debt starts here.
      A flag parked at 100 percent is an
      untested branch that nobody owns.
    end note
```
<img src="rendered/scenario-delivery--block6.svg" alt="scenario-delivery--block6" width=804px/>

**Adapt it:** the two orange states are the debt, and `Removed` is the only terminal state, so keep that shape whatever you rename.
A lifecycle that ends at `Fully on` is the bug this diagram exists to expose.
Swap the ramp percentages for yours, and add an expiry transition out of `DefaultOn` if your flag service enforces one.
Delete the `Disabled` state only if you have never turned a flag off, which is unlikely.

---

### Changing a column without taking the site down

**Answers:** "We need to replace a column on a hot table.
In what order do the schema change and the deploys go out, and where is the last point I can still roll back?"
**Use when:** planning or reviewing a schema change on a table that is being written to while you change it.
**Don't use when:** the reader needs the finished table shape rather than the order of operations.
Use an `erDiagram`, see `erd.md`.
**Detail level:** L3

<!-- mermaid-render: id="scenario-delivery--block7" -->
```mermaid
sequenceDiagram
    autonumber
    participant Ops as release-engineer
    participant App as checkout-api
    participant Job as backfill-job
    participant DB as orders-db

    rect rgb(227, 242, 253)
    Note over Ops,DB: Expand. Add the new shape, break nothing.
    Ops->>DB: ALTER TABLE orders ADD COLUMN currency_code text NULL
    Ops->>DB: CREATE INDEX CONCURRENTLY orders_currency_code_idx
    Note right of DB: Nullable and unread, so the build already in production does not care.
    end

    rect rgb(232, 245, 233)
    Note over Ops,DB: Migrate, part one. Write both columns, then fill the past.
    Ops->>App: deploy build 412, writes currency and currency_code
    App->>DB: INSERT INTO orders (currency, currency_code) VALUES (...)
    Ops->>Job: start backfill
    loop until no rows remain
        Job->>DB: UPDATE orders SET currency_code = map(currency) WHERE currency_code IS NULL LIMIT 5000
        DB-->>Job: rows updated
    end
    Job-->>Ops: 0 rows left with currency_code IS NULL
    end

    rect rgb(255, 248, 225)
    Note over Ops,DB: Migrate, part two. Read the new column.
    Ops->>App: deploy build 419, reads currency_code, still writes both
    App->>DB: SELECT currency_code FROM orders WHERE id = $1
    Note right of App: Last cheap exit. Rolling back to build 412 still works, because both columns are still correct.
    end

    rect rgb(255, 235, 238)
    Note over Ops,DB: Contract. Only now is the old column safe to drop.
    Ops->>App: deploy build 425, writes currency_code only
    Ops->>DB: ALTER TABLE orders DROP COLUMN currency
    Note right of DB: Not reversible without a restore. Wait until no running build names the old column.
    end
```
<img src="rendered/scenario-delivery--block7.svg" alt="scenario-delivery--block7" width=1400px/>

**Adapt it:** swap `orders`, `currency` and `currency_code` for your table and columns, and swap the build numbers for yours.
Keep the four colored phases and keep them in this order, because the order is the whole technique.
Keep the note at the end of phase three; that sentence is the one people need when they are deciding whether to proceed on a Friday.
The `loop` is not decoration, batched backfill with a row limit is what keeps the table writable while it runs, so keep the `LIMIT` visible.
If the change is a column rename with no type change, you still need all four phases; only the `map()` call goes away.
If the two columns cannot both be correct at once, this pattern does not apply, and you need a maintenance window instead.

---

### What is running in each region

**Answers:** "Which version is running where, and what happens if a region goes away?"
**Use when:** onboarding to the production estate, planning a failover test, or proposing a new region.
**Don't use when:** each connection needs a label such as a protocol or a failover trigger.
`architecture-beta` draws unlabeled edges, so use `C4Deployment` from `c4.md` instead.
**Detail level:** L2

<!-- mermaid-render: id="scenario-delivery--block8" -->
```mermaid
architecture-beta
    group edge(internet)[Global edge anycast and WAF]

    service cdn(server)[Edge router] in edge

    group eu(cloud)[eu west primary region]
    group euk8s(server)[checkout cluster 6 nodes] in eu
    service euapi(server)[checkout api 12 pods] in euk8s
    service euwork(server)[OrderWorker 4 pods] in euk8s
    service eudb(database)[orders db primary accepts writes] in eu

    group us(cloud)[us east warm standby]
    group usk8s(server)[checkout cluster 3 nodes] in us
    service usapi(server)[checkout api 4 pods idle until failover] in usk8s
    service usdb(database)[orders db replica read only] in us

    align column euapi euwork

    cdn:R --> L:euapi
    cdn:B --> T:usapi
    euapi:R --> L:eudb
    euwork:R --> L:eudb
    eudb:B --> T:usdb
    usapi:R --> L:usdb
```
<img src="rendered/scenario-delivery--block8.svg" alt="scenario-delivery--block8" width=937px/>

**Adapt it:** replace the region names, the node counts and the pod counts with yours.
Because edges carry no labels here, push the facts into the service labels, as `accepts writes`, `read only` and `idle until failover` do.
`align column euapi euwork` stops two siblings that both point at the database from stacking on top of each other; drop it and they overlap.
`architecture-beta` is a beta type, so render it on your documentation platform before you commit it.
Delete the standby region entirely if you run one region, and the diagram is then three services and still worth drawing.

---

### When does each step actually happen

**Answers:** "What is this migration blocked on this week, and when can we promise the release?"
**Use when:** planning a migration that spans weeks, or giving a stakeholder a date.
**Don't use when:** order matters and dates do not.
Use the environment promotion flowchart above.
**Detail level:** L1

<!-- mermaid-render: id="scenario-delivery--block9" -->
```mermaid
gantt
    accTitle: Migration and release schedule
    accDescr: The currency-code migration runs expand, dual write and backfill, then the 2.5 release train, then the contract phase that drops the old column.
    title Currency-code migration and the 2.5 release train
    dateFormat YYYY-MM-DD
    axisFormat %b %d
    excludes weekends

    section Schema change
    Expand, add currency_code       :done,     exp,   2026-03-02, 2d
    Dual-write build to production  :done,     dual,  after exp, 3d
    Backfill 40M order rows         :active,   fill,  after dual, 6d
    Verify no NULLs remain          :crit,     ver,   after fill, 1d

    section Release train
    Cut release 2.5 branch          :          cut,   after ver, 1d
    Staging soak                    :          soak,  after cut, 3d
    Canary rollout to production    :          roll,  after soak, 2d
    Tag v2.5.0                      :milestone, tag,  after roll, 0d

    section Contract
    Read-new-only build             :          ronly, after tag, 2d
    Drop the currency column        :crit,     drop,  after ronly, 1d
```
<img src="rendered/scenario-delivery--block9.svg" alt="scenario-delivery--block9" width=784px/>

**Adapt it:** replace the dates, the durations and the row count.
Never put a colon inside a task title, because the colon is what separates the title from the metadata and your task will silently collapse to zero duration.
`after <id>` chaining is what makes this survive a slip, so prefer it over hard-coded start dates for everything except the first task.
Mark the irreversible steps `crit` so a reader can see at a glance which days have no undo.
Delete the `Contract` section if you are only scheduling the release, and keep the sections named after phases rather than after teams.
