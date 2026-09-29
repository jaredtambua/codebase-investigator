# Codebase Investigator

## Project goals

Codebase Investigator is a Python tool for analysing and understanding
software repositories.

Keep the core analysis deterministic. Agentic reasoning should be layered
on top of deterministic code-analysis capabilities rather than replacing them.

## Development guidelines

- Use British English for project-owned code and identifiers, comments,
  docstrings, documentation, and user-facing text.
- Preserve third-party and standard-library API names, identifiers, and required
  spellings when referencing or calling them.
- Prefer the Python standard library unless an external dependency provides clear value.
- Keep functions and modules focused on a single responsibility.
- Add or update tests whenever behaviour changes.
- Prefer deterministic output where practical.
- Run the relevant tests before declaring a task complete.
- Do not commit changes unless explicitly requested.

## Working approach

For non-trivial changes:

1. Inspect the relevant existing code first.
2. Propose a plan before implementation when architectural decisions are involved.
3. Make the smallest change that satisfies the requirement.
4. Run relevant tests.
5. Report what changed, what was tested, and any limitations or unresolved issues.

## Agent orchestration

- The root agent owns task decomposition, coordination, integration,
  validation and final synthesis.
- Do not delegate by default. Keep simple or tightly dependent work with
  the root. Delegate only when independent work or specialist expertise
  provides a clear benefit.
- Prefer task specialisation over duplicate general-purpose workers.
  Independent subtasks may run in parallel within the environment's
  concurrency limit.
- Give every worker a bounded task: its objective, relevant context and
  paths, applicable instructions and skills, permitted actions, expected
  output and completion criteria.
- All delegated repository work must follow the applicable AGENTS.md.
  Workers must return requests for further decomposition to the root
  rather than spawning additional workers themselves.
- For consequential changes, prefer fresh-context independent review or
  evaluation when useful. Supply the requirements, relevant artefacts
  and evaluation criteria without requiring the reviewer to inherit the
  implementation discussion.
- Only one agent, including the root, may modify the shared working tree
  at a time. The root explicitly assigns and transfers write ownership.
  Concurrent writers require deliberately introduced isolated worktrees;
  do not create worktrees as part of the default workflow.
- Workers normally return results to the root. Use direct sibling
  communication only when their tasks genuinely depend on one another,
  and report resulting decisions to the root.
- Workers report findings or changes, supporting evidence, validation
  performed, and unresolved questions. The root assesses these results
  before incorporating them into the final response.
- Workers are ephemeral by default. Once their task is complete, collect
  their result and release or close them when the environment supports
  it. Otherwise leave them idle and do not retain them as standing agents.

## Agent configuration and skills

- Keep repository-wide behaviour and orchestration policy in AGENTS.md.
- Create reusable .codex/agents/*.toml definitions only for demonstrated
  recurring specialist roles with meaningfully different standing
  instructions or configuration.
- Keep reusable task procedures and expertise in
  .agents/skills/*/SKILL.md; reference relevant skills rather than copying
  their procedures into agent definitions.
- Define one-off specialist roles in runtime delegation instructions.
  Do not create permanent templates or placeholder agent directories
  merely to populate the configuration.
