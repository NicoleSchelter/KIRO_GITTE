# KIRO Prompts (copy/paste)

## 1) Update documentation and highlight changes
We are in Vibe. Please update and regenerate the complete documentation of the GITTE project based on the current repository state.

Requirements:
1. Synchronize all documentation files (README.md, DESIGN.md, DEPLOY.md, REQUIREMENTS.md, QUALITY.md, Arc42) with the current implementation under src/.
2. Clearly mark and highlight all changes compared to the previous version (unified diff or explicit change log in each document).
3. Review the codebase and identify which automated tests need to be updated or newly created due to recent changes in functionality, configuration, or APIs.
4. Provide recommendations for missing tests (unit, integration, UI, performance), referencing the module paths.
5. Ensure consistency with the layer architecture (ui -> logic -> services -> data). Output ONLY the updated docs and test recommendations. Do not execute anything.

## 2) Generate missing tests (focused follow-up)
We are in Vibe. Based on the latest repo state, propose concrete test files and skeletons for modules that currently lack coverage, following pytest conventions and the layer layout (tests/ui, tests/logic, tests/services, tests/data). Do not execute anything. Output ONLY unified diffs or file contents.
