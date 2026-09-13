# Codebase orientation

**Use for:** showing how a codebase is organised, which team owns which part, and where a new piece of work belongs.
These are the diagrams a team opens to onboard a new joiner, or to settle an argument about where code should live.
**Avoid for:** generic workflow templates (feature development, bug fix, CI/CD, OAuth, REST request/response), which live in `common-patterns.md`.
Also avoid for per-type syntax questions; each `references/<type>.md` file covers those.

Find the scenario that matches the question you were asked, copy the block, and swap the names.
Every example states the one question it answers, so if the question in the heading is not your reader's question, keep scrolling.

---

## Structure and dependency

### Which package may import which

**Answers:** "What is allowed to depend on what, and what are we breaking right now?"
**Use when:** you are writing the layering rule down for the first time, reviewing a change that adds an import across a layer boundary, or backing an architecture argument with the current state of the import graph.
**Don't use when:** the reader wants the order calls happen in at runtime; use the sequence diagram in [Tracing one feature from entry point to data store](#tracing-one-feature-from-entry-point-to-data-store) instead.
A dependency graph says what *may* call what, not what *does* call what, and the two are different pictures.
**Detail level:** L2

<!-- mermaid-render: id="scenario-codebase--block1" -->
```mermaid
flowchart TB
  classDef client fill:#80deea,stroke:#00838f,color:#004d40
  classDef service fill:#b39ddb,stroke:#5e35b1,color:#311b92
  classDef external fill:#90a4ae,stroke:#455a64,color:#263238
  classDef standalone fill:#ce93d8,stroke:#7b1fa2,color:#4a148c
  classDef edgeAllowed stroke:#2e7d32,stroke-width:2px
  classDef edgeViolation stroke:#c62828,stroke-width:3px

  subgraph Delivery [Delivery layer]
    WebCheckout["web/checkout-handler"]:::client
    WebAdmin["web/admin-handler"]:::client
  end

  subgraph App [Application layer]
    Checkout["app/checkout-service"]:::service
    Refund["app/refund-service"]:::service
  end

  subgraph Infra [Infrastructure layer]
    Orders["infra/orders-postgres"]:::external
    Pay["infra/payments-gateway"]:::external
  end

  subgraph Domain [Domain layer]
    Pricing["domain/pricing"]:::standalone
    Cart["domain/cart"]:::standalone
  end

  WebCheckout e1@--> Checkout
  WebAdmin e2@--> Refund
  Checkout e3@--> Orders
  Refund e4@--> Pay
  Orders e5@--> Cart
  Pay e6@--> Pricing
  Pricing e7@-->|banned, domain imports application| Refund

  class e1,e2,e3,e4,e5,e6 edgeAllowed
  class e7 edgeViolation

  %% Legend: Green = allowed import, always downward. Red thick = the import our layer lint rejects.
```
<img src="rendered/scenario-codebase--block1.svg" alt="scenario-codebase--block1" width=798px/>

**Adapt it:** rename the four layer subgraphs to your own layers and replace the eight package names with real import paths a reader can grep for.
Keep the rule visible in one sentence next to the diagram: here it is "a package may import only packages in a layer below it, and nothing in `domain/` imports anything at all".
Every allowed edge here drops exactly one layer, which is what keeps the four bands stacked cleanly.
If your rule also permits skipping a layer downward, say so in the prose rather than drawing the skip edge, because a skip edge pulls two bands onto the same row and the downward reading collapses.
Draw at most one or two violation edges.
A diagram with six red arrows stops being an argument and becomes wallpaper, so split the rest into a tracked list.
Edges here point at nodes rather than at the surrounding subgraph, which is the straight-pipeline exception in `style-standard.md`: the layers are one top-down stack and naming the box would hide the package that actually breaks the rule.
Delete the violation edge and its `edgeViolation` class once the import is gone, in the same change that removes it.

### Tracing one feature from entry point to data store

**Answers:** "What actually runs when a shopper submits a checkout with a discount code?"
**Use when:** onboarding someone onto one feature, or writing up a bug where the fault could be in any of four layers.
**Don't use when:** the flow has many independent branches that do not depend on each other; a flowchart handles fan-out better than `alt` blocks do.
**Detail level:** L3

Trace this by reading the code, not by guessing from the layer names.
Every participant and every method below is a name a reader can search for.

<!-- mermaid-render: id="scenario-codebase--block2" -->
```mermaid
sequenceDiagram
    autonumber
    actor Shopper
    participant H as web/checkout-handler
    participant S as app/CheckoutService
    participant Q as domain/pricing.Quote
    participant R as infra/OrdersRepo
    participant DB as orders-db
    participant PG as payments-gateway

    Shopper->>H: POST /v2/checkouts (code=SPRING20)
    activate H
    H->>S: CheckoutService.Checkout(cartID, code)
    activate S
    S->>R: OrdersRepo.LoadCart(cartID)
    R->>DB: SELECT ... FROM carts WHERE id = $1
    DB-->>R: cart row
    R-->>S: Cart
    S->>Q: Quote.Apply(discount)
    alt discount is valid and in date
        Q-->>S: Quote with discounted total
        S->>PG: PaymentsGateway.Authorize(total)
        PG-->>S: authorization id
        S->>R: OrdersRepo.SaveOrder(order)
        R->>DB: INSERT INTO orders
        DB-->>R: ok
        R-->>S: Order
        S-->>H: Order
        H-->>Shopper: 201 Created
    else discount expired
        Q--xS: ErrDiscountExpired
        S-->>H: ErrDiscountExpired
        H-->>Shopper: 422 Unprocessable Entity
    end
    deactivate S
    deactivate H

    Note over H,PG: Traced from checkout_service.go, not from memory.
```
<img src="rendered/scenario-codebase--block2.svg" alt="scenario-codebase--block2" width=1400px/>

**Adapt it:** replace the participants with your own module names and the messages with real method signatures and real SQL or endpoint names.
Keep `activate`/`deactivate` pairs outside the `alt` block so both branches stay balanced; putting a `+` or `-` inside one branch and not the other produces a lopsided activation bar.
One diagram, one feature.
If your trace needs a second `alt` nested inside the first, the feature is two features and deserves two diagrams.
Put the source file name in a `Note` so the next reader can check the trace instead of trusting it.
`common-patterns.md` has a generic layered REST request template; this one goes further by naming the actual packages and the actual failure path.

---

## Ownership and placement

### Who owns what, and where the seams are

**Answers:** "Whose code is this, and who do I have to talk to before I change it?"
**Use when:** a new team member needs the map on day one, or two teams are arguing about which side of a seam a change belongs on.
**Don't use when:** the question is about packages inside one system; `C4Context` is deliberately too coarse for that, so use [Which package may import which](#which-package-may-import-which).
**Detail level:** L0

<!-- mermaid-render: id="scenario-codebase--block3" -->
```mermaid
C4Context
    accTitle: Storefront bounded contexts and owning teams
    accDescr: Four first-party systems inside the storefront platform, each labelled with the team that owns it, plus the two third-party systems they call.
    title Storefront platform, bounded contexts and owning teams

    UpdateLayoutConfig($c4ShapeInRow="2", $c4BoundaryInRow="1")

    Person(shopper, "Shopper", "Browses and buys")
    Person(agent, "Support agent", "Issues refunds")

    Enterprise_Boundary(platform, "Storefront platform") {
        System(checkout, "checkout", "Team Checkout")
        System(catalog, "catalog", "Team Catalog")
        System(fulfilment, "fulfilment", "Team Fulfilment")
        System(identity, "identity", "Team Platform")
    }

    System_Ext(payments, "payments-provider", "Card processor")
    System_Ext(carrier, "carrier-api", "Shipping carrier")

    Rel(shopper, checkout, "Places orders", "HTTPS")
    Rel(agent, fulfilment, "Cancels shipments", "HTTPS")
    Rel(checkout, catalog, "Reads prices", "gRPC")
    Rel(checkout, identity, "Resolves session", "gRPC")
    Rel(checkout, fulfilment, "Publishes OrderPlaced", "Kafka orders.placed")
    Rel(checkout, payments, "Authorises payment", "HTTPS")
    Rel(fulfilment, carrier, "Books collection", "HTTPS")

    UpdateRelStyle(shopper, checkout, $offsetX="-55", $offsetY="-155")
    UpdateRelStyle(agent, fulfilment, $offsetX="60", $offsetY="-255")
    UpdateRelStyle(checkout, payments, $offsetX="-30", $offsetY="-70")
    UpdateRelStyle(checkout, fulfilment, $offsetX="-70", $offsetY="10")
    UpdateRelStyle(checkout, catalog, $offsetX="-50", $offsetY="-15")
    UpdateRelStyle(fulfilment, carrier, $offsetX="-60", $offsetY="-35")
```
<img src="rendered/scenario-codebase--block3.svg" alt="scenario-codebase--block3" width=932px/>

**Adapt it:** put the owning team in the description field of every `System` and nothing else, because that field is the whole point of this diagram.
Keep those descriptions to two or three words.
A long description widens the shape, and wide shapes force Mermaid to stack the boundary one system per row, which is how this diagram turns into an unreadable column.
Set `UpdateLayoutConfig($c4ShapeInRow="2", $c4BoundaryInRow="1")` to get the grid, and raise the number only if your labels stay short.
Name the protocol or the topic on every `Rel`, since the seam is where the protocol is, and "uses" tells a reader nothing.
The `UpdateRelStyle` lines at the bottom exist only to move relationship labels off the boxes they landed on; tune `$offsetX` and `$offsetY` last, once the elements are settled, and delete them if your labels already sit clear.
Keep third-party systems as `System_Ext` black boxes and never draw their internals.
Put each system's responsibilities in prose beside the diagram rather than in the shape.
Stay under about 15 elements; past that, split by team and let each team draw its own `C4Container` diagram.
See `c4.md` for the full element syntax and for the rule on when a microservice is a `Container` and when it is promoted to its own `System`.

### Where does this new code go

**Answers:** "I have a new type to add. Which folder does it belong in?"
**Use when:** the same placement question keeps arriving in review, and you want an answer people can apply without asking.
**Don't use when:** the real question is "who has to approve this", which is an ownership question; use [Who owns what, and where the seams are](#who-owns-what-and-where-the-seams-are).
**Detail level:** L1

<!-- mermaid-render: id="scenario-codebase--block4" -->
```mermaid
flowchart TD
  accTitle: Where new code belongs in the storefront repo
  accDescr: A decision tree routing a new type to one of five folders, based on whether it performs I/O, whether it is an entry point, whether it encodes a business rule, and whether more than one service needs it.

  Start([New type to add]) --> IO{Does it talk to anything outside the process?}
  IO -->|yes| Entry{Is it an entry point we expose?}
  IO -->|no| Rule{Does it encode a business rule?}
  Entry -->|yes| Web["web/ - one handler plus its request and response types"]
  Entry -->|no| Infr["infra/ - one adapter per outside system"]
  Rule -->|yes| Dom["domain/ - pure types and functions, imports nothing of ours"]
  Rule -->|no| Reuse{Do two or more services need it today?}
  Reuse -->|yes| Plat["platform/ - shared kernel, needs review from both teams"]
  Reuse -->|no| Appl["app/ - orchestration inside the one service that needs it"]
```
<img src="rendered/scenario-codebase--block4.svg" alt="scenario-codebase--block4" width=1370px/>

**Adapt it:** the questions in the diamonds are the load-bearing part, so rewrite them to match the distinctions your codebase actually makes.
Order them so the cheapest question comes first.
"Does it do I/O" is one anybody can answer in five seconds, which is why it is at the top.
Note the deliberate "today" in the shared-kernel question: it stops speculative code landing in `platform/` because someone might need it later.
Keep this at L1 with no palette.
If a leaf needs more than one line of explanation, that explanation belongs in prose under the diagram, not in the node.

---

## Lifecycle and surface

### The lifecycle of a published document

**Answers:** "What states can a document be in, and which transitions are legal?"
**Use when:** the entity has a status column and the rules for changing it are spread across several handlers.
**Don't use when:** who performs each transition matters more than which state the record is in; use a swimlane flowchart, see `swimlanes.md`.
**Detail level:** L2

<!-- mermaid-render: id="scenario-codebase--block5" -->
```mermaid
stateDiagram-v2
    direction LR
    [*] --> Draft
    Draft --> InReview : author submits
    InReview --> ChangesRequested : reviewer rejects
    ChangesRequested --> InReview : author resubmits
    InReview --> Approved : reviewer approves
    Approved --> Scheduled : publish_at is in the future
    Approved --> Published : publish now
    Scheduled --> Published : PublishScheduler fires
    Published --> Draft : editor unpublishes to revise
    Published --> Archived : RetentionJob, 24 months after publish
    Archived --> [*]

    note right of ChangesRequested
        The only state carrying reviewer comments.
        Resolving a comment does not move the document.
    end note
```
<img src="rendered/scenario-codebase--block5.svg" alt="scenario-codebase--block5" width=1400px/>

**Adapt it:** the state names must be the exact values stored in the column, here `documents.status`, so a reader can query for them.
Label every transition with what triggers it, and name the job or the handler when the trigger is automatic.
Transitions you did not draw are transitions the code should reject, so add the missing-transition check to the test suite in the same change.
`common-patterns.md` already has order-lifecycle and user-account templates; this one adds a scheduled state and a reversible publish, which is the shape most content and subscription entities have.

### What the public API promises, and for how long

**Answers:** "When does v1 stop working, and what do I move to?"
**Use when:** consumers need the removal date, or you are writing the deprecation note that goes in the changelog.
**Don't use when:** the question is what each lifecycle stage means and which transitions any endpoint may make; that is a rules question, not a calendar question, so use a `stateDiagram-v2` with `Experimental`, `Stable`, `Deprecated` and `Removed` states instead.
A timeline tells one reader when to act.
A state diagram tells every future endpoint how to behave.
**Detail level:** L2

<!-- mermaid-render: id="scenario-codebase--block6" -->
```mermaid
timeline
    title checkout-api public surface, v1 through v3
    section Shipped
        2024-Q1 : v1 ships with GET /v1/carts and POST /v1/checkout
        2024-Q3 : v2 adds POST /v2/checkouts with discount codes
                : v1 stays the documented default
    section Deprecating
        2025-Q1 : v1 marked deprecated in the OpenAPI spec
                : Sunset header on every /v1 response
        2025-Q2 : v2 becomes the documented default
                : new API keys are refused access to /v1
    section Removed
        2025-Q4 : /v1 returns 410 Gone
                : v1 handlers deleted from web/
    section Next
        2026-Q1 : v3 preview behind the checkout_v3 flag
```
<img src="rendered/scenario-codebase--block6.svg" alt="scenario-codebase--block6" width=1400px/>

**Adapt it:** use real quarters or real dates, and name the exact routes, headers, and flags.
"Deprecated" with no removal date is not a deprecation, so every deprecating entry needs a matching removal entry further right, even if the date is provisional.
Each colon starts a new event, so keep colons out of the event text itself.
Put the future entries in their own `section` so a reader can see at a glance which part of the diagram is a promise and which part is history.

---

## Build and verification

### What each test level actually covers

**Answers:** "If this test passes, what do I still not know?"
**Use when:** someone asks why a bug reached production with green tests, or you are deciding which level a new test belongs at.
**Don't use when:** you want the order stages run in and what fails the build; use [What must build before what](#what-must-build-before-what), or the CI/CD pipeline template in `common-patterns.md`.
**Detail level:** L1

<!-- mermaid-render: id="scenario-codebase--block7" -->
```mermaid
flowchart TB
  accTitle: Test scope for the checkout service
  accDescr: Nested boxes show what each test level exercises for real. Unit tests cover the pure domain packages. Integration tests add the HTTP handler, the repository and a real Postgres. End-to-end tests add a browser. The payments gateway is stubbed at every level.

  subgraph E2E ["End to end: real browser, real stack"]
    Browser[Browser session]
    subgraph Integ ["Integration: real HTTP, real Postgres"]
      Handler["web/checkout-handler"]
      Repo["infra/orders-postgres"]
      DB[(orders-db)]
      subgraph Unit ["Unit: pure functions, no I/O"]
        Pricing["domain/pricing"]
        Cart["domain/cart"]
      end
    end
  end

  Stub["payments-gateway stub"]

  Browser --> Integ
  Handler --> Unit
  Handler --> Repo
  Repo --> DB
  E2E -.-> Stub
```
<img src="rendered/scenario-codebase--block7.svg" alt="scenario-codebase--block7" width=1101px/>

**Adapt it:** containment is the message here, so put a component inside the innermost box that exercises it for real.
Anything left outside every box is never covered, and anything faked at every level, like the payments gateway above, sits outside on its own.
That outside node is usually the most useful thing on the diagram, because it names the risk nobody tests.
Keep the level names as your test commands spell them so a reader can run the right one.
Edges are secondary here: the one crossing into a nested box names the box, per the subgraph rule in `style-standard.md`.

### What must build before what

**Answers:** "Why does a one-line change in this package rebuild half the repo?"
**Use when:** the build is slow and you need to show where the fan-out is, or a new package needs slotting into the graph.
**Don't use when:** the reader wants dates, durations, or who is blocked; use a `gantt` chart, see `gantt.md`.
**Detail level:** L2

<!-- mermaid-render: id="scenario-codebase--block8" -->
```mermaid
flowchart LR
  classDef producer fill:#90caf9,stroke:#1565c0,color:#0d47a1
  classDef consumer fill:#81c784,stroke:#2e7d32,color:#1b5e20
  classDef client fill:#80deea,stroke:#00838f,color:#004d40
  classDef standalone fill:#ce93d8,stroke:#7b1fa2,color:#4a148c
  classDef external fill:#90a4ae,stroke:#455a64,color:#263238
  classDef edgeEnqueue stroke:#1565c0,stroke-width:2px
  classDef edgeConsume stroke:#2e7d32,stroke-width:2px
  classDef edgeExternal stroke:#455a64,stroke-width:1.5px

  Gen["task proto-gen"]:::standalone
  Types["packages/shared-types"]:::producer
  Kit["packages/ui-kit"]:::producer
  Api["services/checkout-api"]:::consumer
  Web["apps/storefront-web"]:::client
  Admin["apps/admin-web"]:::client
  Unit["task test-unit"]:::standalone
  E2E["task test-e2e"]:::standalone
  Img["task docker-build"]:::standalone
  Stage[(staging cluster)]:::external

  Gen e1@==> Types
  Types e2@--> Api
  Types e3@--> Web
  Types e4@--> Admin
  Kit e5@--> Web
  Kit e6@--> Admin
  Api e7@--> Unit
  Web e8@--> Unit
  Admin e9@--> Unit
  Unit e10@--> Img
  Img e11@--> E2E
  E2E e12@-.-> Stage

  class e1 edgeEnqueue
  class e2,e3,e4,e5,e6,e7,e8,e9,e10,e11 edgeConsume
  class e12 edgeExternal

  %% Legend: Blue nodes = shared packages; green = service; cyan = client apps; purple = tasks.
  %% Legend: Blue thick edge = generates source. Green edge = must finish first. Grey dotted = deploys to an environment.
```
<img src="rendered/scenario-codebase--block8.svg" alt="scenario-codebase--block8" width=1400px/>

**Adapt it:** an arrow means "must finish before", so read it as the build tool does and keep the direction consistent across the whole diagram.
Use your task runner's real task names, because the value of this diagram is that a reader can run any node on it.
Separate generated artefacts from hand-written ones, as `proto-gen` to `shared-types` does here, since generated inputs are where stale-cache bugs come from.
Fan out from the shared packages, fan back in at the first task that needs everything, and keep the tail after that point linear.
A graph that crosses itself in the middle is usually a graph whose real order you have not decided yet.
If the graph passes 20 nodes, draw the packages only and put the per-package task graph in a second diagram.

### The repo map

**Answers:** "What is in here, and what is each top-level folder for?"
**Use when:** it is someone's first hour in the repo, or a README needs one picture at the top.
**Don't use when:** the relationships between the folders matter more than the listing; use [Which package may import which](#which-package-may-import-which), because a tree cannot show that `domain/` depends on nothing.
**Detail level:** L0

<!-- mermaid-render: id="scenario-codebase--block9" -->
```mermaid
treeView-beta
    accTitle: Storefront monorepo folder map
    accDescr: The five top-level folders of the storefront monorepo and the packages, services and apps directly under each one.
    storefront/
        apps/
            storefront-web/
            admin-web/
        services/
            checkout-api/
            catalog-api/
        packages/
            shared-types/
            ui-kit/
        ops/
            terraform/
            runbooks/
        docs/
            adr/
```
<img src="rendered/scenario-codebase--block9.svg" alt="scenario-codebase--block9" width=200px/>

**Adapt it:** one line per folder and two levels below the root is the whole budget.
The moment a reader has to scroll, the map has stopped being a map.
Put the purpose of each folder in prose beside the tree rather than in the labels, since `treeView-beta` labels cannot hold spaces unless you quote them.
`treeView-beta` is a beta type, so confirm your documentation platform renders it before committing this; a fenced `tree` command output is the fallback that always works.
A trailing `/` marks a directory and renders bold, which is what separates this from a plain list.
