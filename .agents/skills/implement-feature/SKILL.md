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

The Head Worker reports a complete execution plan to Root before editing for every assignment, proportionate to its complexity.

The plan should identify:

- files that need to change,
- important design decisions,
- expected behaviour,
- tests that should be added or changed,
- relevant skills and validation commands,
- useful specialist delegation, or why no specialists are needed,
- anything deliberately left out of scope.

Wait for Root's approval when the task introduces architectural decisions or the assignment requires approval. Root may approve routine technical plans within the user's authorised scope; material product or architectural ambiguity and explicit user approval checkpoints must be escalated to the user.

## 3. Implement

After any required approval and assignment of write ownership:

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

## 6. Report

The Head Worker reports to Root for final supervisory assessment:

- what changed,
- what was tested,
- test results,
- any skipped tests,
- limitations or unresolved issues.

Do not commit changes. Commits remain exclusively under the user's control.