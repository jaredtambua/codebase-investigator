---
name: implement-feature
description: Implement a bounded feature in Codebase Investigator using a plan-first, test-driven, reviewable workflow.
---

# Implement Feature

Use this procedure when implementing a new bounded feature or capability.

## 1. Inspect

Before making changes:

- Read the relevant existing implementation and tests.
- Check the current Git working tree.
- Identify repository instructions that apply.
- Do not modify files during this step.

## 2. Plan

Root prepares an execution plan before editing, proportionate to the task's complexity.

The plan should identify:

- files that need to change,
- important design decisions,
- expected behaviour,
- tests that should be added or changed,
- relevant skills and validation commands,
- useful specialist delegation, when warranted under `AGENTS.md`,
- anything deliberately left out of scope.

Follow `AGENTS.md` for engineering authority, clarification and approval checkpoints.

## 3. Implement

After any required approval, with write ownership governed by `AGENTS.md`:

- Make the smallest change that satisfies the requirement.
- Preserve unrelated existing behaviour.
- Follow `AGENTS.md`.
- Avoid unrelated refactoring.
- Integrate specialist findings and fix confirmed issues within scope.

## 4. Validate

- Add or update tests for changed behaviour.
- Run the relevant tests.
- Run the full test suite when practical.
- Investigate failures rather than assuming the implementation is at fault.

## 5. Review

Before declaring completion:

- Inspect the Git diff.
- Check for accidental or unrelated changes.
- Verify existing documentation was preserved when updating it.
- Check that the implementation still matches the approved plan.
- Apply the independent-review policy in `AGENTS.md`. Verify material findings,
  fix confirmed defects within scope and revalidate after changes.

## 6. Report

Root reports the engineering outcome directly to the user:

- what changed,
- changed files and important design decisions,
- what was tested,
- test results,
- any skipped tests,
- independent-review outcome, or why review was skipped,
- limitations or unresolved issues.

Do not commit changes. Commits remain exclusively under the user's control.
