---
name: review-python-analysis
description: Review changes to Codebase Investigator's deterministic Python source analysis for correctness, scope handling, stable output, and test coverage. Use for analysis code reviews, not unrelated edits or general repository exploration.
---

# Review Python analysis

Review the requested changes and report actionable defects to Root. Remain read-only; Root owns fixes. Follow the independent-review and context-engineering policy in `AGENTS.md` and verify the evidence supporting your findings.

## Establish the contract

Read the repository's applicable AGENTS.md, the requested diff or files, and relevant tests. Resolve paths below from the repository root:

- `src/codebase_investigator/analysis.py`: single-file analysis and result records.
- `tests/test_analysis.py`: analysis behaviour and error coverage.
- `README.md`: public API behaviour and examples.
- `src/codebase_investigator/discovery.py`: inspect only when discovery integration is relevant.

Use the user's requested behaviour and current documented contract as the baseline. Distinguish intentional API changes from regressions.

## Check analysis behaviour

- Keep source inspection static: analysed files must not be executed or imported. Prefer standard-library parsing; agent reasoning must not substitute for deterministic extraction.
- Check the agreed scope. The current API includes only direct `ast.Module.body` functions, async functions, classes, and imports. Methods, nested definitions, and statements inside control-flow blocks are excluded unless the requested change deliberately expands that contract.
- Verify source order within each category and preservation of duplicate definitions and imports. Check definition names, async flags, and one-based line numbers; decorated definitions use the definition header's line.
- Check import forms relevant to the change: multiple names, aliases, dotted names, relative levels, and wildcard imports. Preserve import metadata without resolving or expanding imported objects.
- Check Python encoding declarations and propagation of file, decoding, and syntax errors. Invalid input should not silently produce partial results. Account for syntax support depending on the running Python interpreter.
- Compare documentation and tests with the implementation. Flag missing behaviour coverage when it could conceal a concrete regression; avoid requesting tests that merely mirror implementation details.

## Validate and report

Run relevant existing tests when execution is within the user's requested scope. From the repository root on Windows, use `.venv\Scripts\python.exe -m pytest tests/test_analysis.py`; use the project's configured interpreter on other platforms. Include discovery tests when integration is affected. Respect inspection-only requests and disclose tests not run.

Report actionable findings in severity order with evidence, file and line references, the triggering input or condition, expected versus observed behaviour where applicable, and relevant uncertainty. Separate confirmed defects from open questions. If no actionable findings were identified, say so and identify meaningful coverage limitations. State which tests ran and their results, including skips.
