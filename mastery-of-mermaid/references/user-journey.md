# User journey

**Use for:** an end-to-end user experience broken into sections and steps, each scored for satisfaction, and attributed to the actor(s) performing it.
**Avoid for:** developer debugging, or any flow where the point is *system* behavior rather than user experience (use a flowchart or sequence diagram instead).

## Core syntax

<!-- mermaid-render: id="user-journey--block1" -->
```mermaid
journey
    title My working day
    section Go to work
      Make tea: 5: Me
      Go upstairs: 3: Me
      Do work: 1: Me, Cat
    section Go home
      Go downstairs: 5: Me
      Sit down: 5: Me
```
![user-journey--block1](rendered/user-journey--block1.svg)

Each `section` groups the steps of one part of the journey. A task line is `Task name: <score>: <actor, actor, ...>`. The score is an integer from 1 (worst) to 5 (best), inclusive, and drives the rendered happiness curve. Multiple actors on one task are comma-separated.
