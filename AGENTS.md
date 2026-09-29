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
- Do not commit changes. Commits remain exclusively under the user's control.

## Working approach

For non-trivial changes:

1. Inspect the relevant existing code first.
2. Propose a plan before implementation when architectural decisions are involved.
3. Make the smallest change that satisfies the requirement.
4. Run relevant tests.
5. Report what changed, what was tested, and any limitations or unresolved issues.

## Agent orchestration

### Root: Supervisor and Architect

- The user communicates with Root. Root clarifies intent, owns high-level
  requirements and architecture, and delegates every engineering task,
  including simple tasks, to a Head Worker.
- Give the Head Worker a bounded assignment: objective, relevant context
  and paths, constraints, permitted actions, expected output and completion
  criteria. Root should not normally implement or modify application files.
- Root approves routine technical plans within the user's authorised scope.
  Escalate material product or architectural ambiguity to the user and
  honour explicit user approval checkpoints.
- Root assesses completed work against the user's original intent and owns
  final supervisory assessment and synthesis. Root never commits.

### Head Worker: Lead Engineer and default writer

- Read applicable repository instructions and skills and inspect the
  repository before forming a complete execution plan for every assignment,
  proportionate to its complexity. Cover implementation, relevant skills,
  validation and useful specialist delegation. Report the plan to Root and
  wait for approval before implementation when required by the assignment
  or skills, or when architectural decisions are involved.
- After required approval, the Head Worker is the default owner of writes.
  Integrate specialist findings, make the final engineering judgement,
  implement the change and perform integrated technical validation.
- Use specialists conservatively: bounded investigation, research, parallel
  investigation, independent context or evaluation must justify their
  additional context and usage costs. Prefer task specialisation over
  duplicate general-purpose agents.
- The Head Worker may spawn bounded specialists, or ask Root to spawn them
  when the available tools require it. Do not create another Head Worker
  layer. Escalate assignment-level decomposition or architecture questions
  to Root.
- Report changes, supporting evidence, validation results, limitations and
  unresolved questions to Root. Workers never commit.

### Specialists, verification and coordination

- All delegated repository work follows the applicable AGENTS.md. Every
  specialist receives a bounded objective, relevant context and paths,
  applicable skills, permitted actions, expected output and completion
  criteria.
- Specialists are read-only by default. Investigate deeply, verify evidence
  supporting findings, and return constraints, edge cases and recommendations
  to the Head Worker. Specialists must not spawn workers; return requests
  for further decomposition to the Head Worker or Root as appropriate.
- Every worker verifies the work or evidence it owns. For consequential
  changes, the Head Worker should use fresh-context, read-only independent
  review when its expected value justifies the cost. Supply requirements,
  relevant artefacts and evaluation criteria without requiring the reviewer
  to inherit the implementation discussion.
- The Head Worker assesses review findings, fixes confirmed problems where
  appropriate, and escalates unresolved disagreements or architectural
  questions to Root before reporting completion.
- Only one agent may own writes to the shared working tree at a time.
  Root assigns initial ownership to the Head Worker; the Head Worker may
  explicitly transfer ownership to a specialist and must reclaim it before
  editing again. A transfer suspends the previous owner's permission to
  write. Read-only specialists must not modify files without this transfer.
  Concurrent writers require deliberately isolated worktrees; do not
  introduce worktrees as part of the default workflow.
- Parallelise useful independent read-only investigations within the
  environment's concurrently active agent limit, including Root and the
  Head Worker. This is not a cumulative agent budget for a task; do not
  maximise concurrency merely because capacity is available.
- Specialist results normally return to the Head Worker for synthesis.
  Use direct sibling communication only for genuine task dependencies,
  and report resulting decisions to the Head Worker.
- Workers are ephemeral by default. Collect results when tasks finish and
  release or close workers where supported; otherwise leave them idle.
  Do not assume an explicit release tool or unlimited cumulative creation
  is available.

## Agent configuration and skills

- Keep repository-wide behaviour and orchestration policy in AGENTS.md.
- The recurring Head Worker role is defined in
  `.codex/agents/head-worker.toml`. Use it where custom-agent selection is
  supported. When runtime spawning has no custom-agent selector, Root must
  read that definition and pass its role instructions with the bounded
  assignment explicitly; a matching task name does not load the file.
- Create reusable .codex/agents/*.toml definitions only for demonstrated
  recurring roles with meaningfully different standing instructions or
  configuration.
- Keep reusable task procedures and expertise in
  .agents/skills/*/SKILL.md; reference relevant skills rather than copying
  their procedures into agent definitions.
- Define one-off specialist roles in runtime delegation instructions.
  Do not create permanent templates or placeholder agent directories
  merely to populate the configuration.
