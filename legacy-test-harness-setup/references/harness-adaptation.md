# Adapting to the harness

This skill doesn't assume a harness.
In phase 0, find out what the running harness supports, and generate artifacts in its native form.

## Facts to establish

For each item, record how you confirmed it: you checked the harness's own documentation, used its help command, or saw the tool in your own tool list.
Don't fill in a fact from memory, because harness features and file locations change between versions.

| Fact | Why it matters |
|---|---|
| Where repo-local skills are discovered | where the phase 5 skill goes |
| Whether sub-agents can be defined per repository, where, and in what format | how roles are generated |
| Whether the main session can spawn sub-agents at runtime | whether roles run fresh per task |
| Whether sessions can message each other | whether a standing role is possible at all |
| The project-instruction file it reads | where to put the pointer to the workflow skill |
| How it creates or enters git worktrees | whether claiming a slot can hook into worktree creation |
| How it passes the environment and working directory to commands | how runners find the slot file |
| Its permission model for shell commands | which provisioning steps the operator must run themselves |

## Generating artifacts

- **Repo-local skills supported:** write the workflow skill there, using the harness's skill format.
- **Sub-agent definitions supported:** write one definition per staffed role. Use the harness's format for name, description, allowed tools, and model. Read-only roles get read-only tools wherever the format allows.
- **No sub-agent definitions, but runtime spawning works:** write each role brief as a Markdown file in the workflow skill's directory. The workflow skill tells the orchestrator to pass the brief when spawning.
- **No delegation at all:** write the role briefs anyway. The operator, or a single agent, runs them as separate passes in sequence, with fresh context per pass where possible.

When the operator's team uses several harnesses, generate for each one they named.
Write each brief exactly once, in the running harness's workflow skill directory, for example `<skill dir>/roles/debugger.md`.
Every other file, for any harness, holds only its own metadata and one line such as "Follow the brief in `<skill dir>/roles/debugger.md`." Never copy a brief, or the copies drift apart.

## Example: Claude Code

Written 2026-10-11 from the skill author's knowledge of Claude Code; not verified against its documentation.
Confirm each item on the work machine before relying on it.

- Repo-local skills: `.claude/skills/<name>/SKILL.md` with `name` and `description` frontmatter.
- Repo-local sub-agents: `.claude/agents/<name>.md` with frontmatter `name`, `description`, and optionally `tools` and `model`. The body is the one-line pointer to the shared brief.
- Project instructions: `CLAUDE.md` at the repo root.
- Per-worktree environment: an untracked `.claude/settings.local.json` can set `env` for the commands a session runs. The slot file remains the source of truth either way.

Any other harness: establish the same facts from its own documentation, and record them in the working record before generating anything.
