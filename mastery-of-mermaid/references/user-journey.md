# User journey

**Use for:** an end-to-end user experience broken into sections and steps,
each scored for satisfaction, and attributed to the actor(s) performing it.
**Avoid for:** developer debugging,
or any flow where the point is *system* behavior rather than user experience (use a flowchart or sequence diagram instead).

## Core syntax

<!-- mermaid-render: id="user-journey--block1" -->
```mermaid
journey
    title New user onboarding
    section Sign up
      Create account: 5: User
      Verify email: 3: User
      Set up workspace: 2: User, Support
    section First project
      Create first project: 4: User
      Invite teammate: 5: User
```
<img src="rendered/user-journey--block1.svg" alt="user-journey--block1" width=1100px/>

Each `section` groups the steps of one part of the journey.
A task line is `Task name: <score>: <actor, actor, ...>`.
The score is an integer from 1 (worst) to 5 (best), inclusive,
and drives the rendered happiness curve.
Multiple actors on one task are comma-separated.
