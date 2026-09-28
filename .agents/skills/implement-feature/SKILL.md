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

For non-trivial changes, propose a concise implementation plan before editing.

The plan should identify:

- files that need to change,
- important design decisions,
- expected behaviour,
- tests that should be added or changed,
- anything deliberately left out of scope.

Wait for approval before implementing when the task introduces architectural decisions.

## 3. Implement

After the plan is approved:

- Make the smallest change that satisfies the requirement.
- Preserve unrelated existing behaviour.
- Follow `AGENTS.md`.
- Avoid unrelated refactoring.

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

## 6. Report

Report:

- what changed,
- what was tested,
- test results,
- any skipped tests,
- limitations or unresolved issues.

Do not commit changes unless explicitly requested.