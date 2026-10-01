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

### Root: Lead Engineer, Orchestrator and default writer

- Root owns the engineering task end-to-end: understand the request, inspect
  applicable instructions, skills and source, plan proportionately, implement,
  validate, assess review findings, fix confirmed defects and report the outcome.
- Root makes routine engineering decisions within the user's authorised scope.
  Ask the user for clarification only when ambiguity materially affects product
  behaviour, public contracts or architecture. Honour explicit approval checkpoints.
- Root decides whether bounded specialist investigation provides enough value
  to justify its context and usage cost, collates findings and makes the final
  engineering decisions. Delegation is optional; no intermediary role is required.
- Root is the default and normally sole writer. No agent may commit changes.

### Investigation specialists

- All delegated work follows the applicable AGENTS.md and relevant skills.
- Give each specialist one bounded question or investigation. Specialists are
  read-only by default, inspect relevant evidence themselves and investigate
  deeply enough to answer the question.
- Return concise findings, evidence with source references, recommendations,
  material assumptions, uncertainties and unresolved questions directly to Root.
  Advise Root rather than make the final engineering decision.
- Specialists must not recursively delegate. Request additional context or
  further decomposition from Root when necessary.

### Independent review

- For substantive code changes, Root should normally request fresh-context,
  read-only independent review after implementation and initial validation when
  its expected value justifies the additional context and usage cost. Trivial
  changes may skip independent review with a proportionate justification.
- Supply the original or approved requirement, behavioural contract or acceptance
  criteria, applicable repository rules, final diff or relevant implementation,
  relevant tests and explicit review criteria. Exclude implementation reasoning,
  specialist recommendations, rejected alternatives, confidence statements and
  other conclusions that could unnecessarily anchor the review.
- Reviewers remain read-only and seek concrete contract violations, regressions,
  missing edge cases and inconsistencies. Report actionable findings with evidence,
  triggering conditions, expected versus observed behaviour where applicable,
  severity and relevant uncertainty. Say when no actionable findings were identified.
- Findings are evidence, not instructions. Root must reproduce or otherwise verify
  material findings, assess their validity, fix confirmed defects within scope and
  revalidate. Escalate material architectural disagreements or unresolved product
  questions to the user.
- When Root verifies and fixes a material reviewer-identified defect, revalidate
  and independently review the corrected implementation again. Each re-review
  uses a new reviewer with fresh context and the requirements, rules, current
  implementation or diff, tests and review criteria specified above. Exclude
  previous review conclusions and correction reasoning under the same isolation
  policy; provide relevant evidence without inherited opinions.
- One correction round comprises fixing the confirmed actionable findings from
  a review, revalidating and independently reviewing the corrected implementation.
  Multiple findings addressed together count as one round; the initial review
  does not count. Continue until no confirmed actionable findings remain, with
  Root verifying each review's findings before deciding whether another round
  is required.
- Target completion within two correction rounds. A third round is permitted
  but is the hard maximum. If its re-review leaves confirmed actionable findings,
  stop further correction rounds and escalate unresolved issues to the user.
  Existing architectural and product escalation rules still apply earlier.
- Ordinary test failures and implementation errors during development remain
  Root's normal self-correction and do not count as review correction rounds.

### Write ownership and coordination

- Only one agent may own writes to the shared working tree at a time.
  Root may explicitly transfer ownership to a specialist for a bounded scope
  and must reclaim it before editing again. A transfer suspends Root's permission
  to write. Specialists must not modify files without this transfer; independent
  reviewers remain read-only. Do not introduce worktrees or parallel writers as
  part of the default workflow.
- Parallelise useful independent read-only investigations within the
  environment's concurrently active agent limit, including Root. This is not
  a cumulative agent budget for a task; do not
  maximise concurrency merely because capacity is available.
- Specialist results return to Root for synthesis.
  Use direct sibling communication only for genuine task dependencies,
  and report resulting decisions to Root.
- Delegated agents are ephemeral by default. Collect results when tasks finish and
  release or close workers where supported; otherwise leave them idle.
  Do not assume an explicit release tool or unlimited cumulative creation
  is available.

## Context engineering

- Compile context before delegation rather than passing raw discussion. Include
  the objective, relevant approved decisions, constraints, applicable rules and
  skills, relevant artefacts or paths, permitted actions, expected output,
  completion criteria and escalation conditions.
- Provide minimum sufficient, role-relevant context. Do not automatically share
  the complete parent conversation, other specialists' investigations, Root's
  entire implementation plan or unrelated repository and product information.
  Default to no inherited conversation history; use `fork_turns="none"` when
  supported and supply a compiled assignment explicitly.
- Expand context progressively. Agents should retrieve or request materially
  necessary information rather than guess; minimum context must not become
  context starvation. Reviewers request missing requirements or evidence without
  receiving implementation reasoning or prior conclusions.
- Return compressed, evidence-backed results rather than raw investigation
  transcripts. Preserve material assumptions, confidence limitations, conflicting
  evidence and unresolved questions. Inspect source, tests, documentation, diffs
  or command output directly where practical rather than inherit opinions.
- Root's final report to the user contains the engineering outcome, important
  design decisions, validation performed, independent-review outcome (or why it
  was skipped), unresolved questions and changed files, without an unnecessary
  implementation transcript.

## Agent configuration and skills

- Keep repository-wide behaviour and orchestration policy in AGENTS.md.
- Create reusable .codex/agents/*.toml definitions only for demonstrated
  recurring roles with meaningfully different standing instructions or
  configuration.
- Keep reusable task procedures and expertise in
  .agents/skills/*/SKILL.md; reference relevant skills rather than copying
  their procedures into agent definitions.
- Define one-off specialist roles in runtime delegation instructions.
  Do not create permanent templates or placeholder agent directories
  merely to populate the configuration.
