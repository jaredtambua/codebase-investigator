# Codebase Investigator

## Project goals

Codebase Investigator is a Python tool for analyzing and understanding
software repositories.

Keep the core analysis deterministic. Agentic reasoning should be layered
on top of deterministic code-analysis capabilities rather than replacing them.

## Development guidelines

- Prefer the Python standard library unless an external dependency provides clear value.
- Keep functions and modules focused on a single responsibility.
- Add or update tests whenever behavior changes.
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