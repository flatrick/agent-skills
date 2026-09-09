# Timeline

**Use for:** chronology of events, milestones, or periods,
read left-to-right (or top-down) in order.
**Avoid for:** runtime data flow,
or when the reader needs a Gantt chart's task-duration/dependency view instead (use `gantt.md`).

## Core syntax

<!-- mermaid-render: id="timeline--block1" -->
```mermaid
timeline
    title History of Social Media Platform
    2002 : LinkedIn
    2004 : Facebook
         : Google
    2005 : YouTube
    2006 : Twitter
```
<img src="rendered/timeline--block1.svg" alt="timeline--block1" width=900px/>

Each line is `{time period} : {event}`;
multiple colon-separated events stack under the same period (either on one line,
or on continuation lines with a blank period).
Both the period and event are plain text, not limited to years.

## Sections

<!-- mermaid-render: id="timeline--block2" -->
```mermaid
timeline
    title Industrial Revolution
    section 17th-20th century
        Industry 1.0 : Machinery, steam power
        Industry 2.0 : Electricity, mass production
    section 21st century
        Industry 4.0 : Internet, robotics
```
<img src="rendered/timeline--block2.svg" alt="timeline--block2" width=900px/>

`section <name>` groups subsequent periods and gives them a shared color scheme.
Without any section,
each period gets its own color by default (`disableMulticolor: true` turns that off).

## Direction, wrapping, theming (v11.14+)

- `timeline TD` renders top-down instead of the default left-to-right (`LR`).
- Long text wraps automatically; force a break with `<br>`.
- Section/period colors come from `cScale0`-`cScale11` (and matching `cScaleLabel0`-`cScaleLabel11` for foreground text) theme variables,
  repeating cyclically past 12 sections.
