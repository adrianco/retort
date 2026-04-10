# Bundled Task Specs

Each task directory contains:
- `task.yaml` — Functional specification, validation criteria, expected outcomes
- `validate.py` — Automated pass/fail validation script

Tasks are referenced in workspace.yaml via `source: bundled://<task-name>`.
