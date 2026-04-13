# Extending Retort

Retort uses a plugin system (via `pluggy`) for custom scorers, runners, and task sources. This guide shows how to extend each.

## Plugin discovery

Retort discovers plugins via Python entry points. Add to your `pyproject.toml`:

```toml
[project.entry-points."retort.scorers"]
my_scorer = "my_package.scorers:MyScorer"

[project.entry-points."retort.runners"]
my_runner = "my_package.runners:MyRunner"
```

List installed plugins:

```bash
retort plugin list
retort plugin show my_scorer
```

## Custom scorers

A scorer evaluates the output of an experiment run and produces a numeric score.

```python
from retort.scoring.registry import Scorer

class SecurityAuditScorer(Scorer):
    """Score code for security vulnerabilities."""

    name = "security_audit"

    def score(self, artifacts) -> float:
        """Return a score between 0.0 and 1.0.

        Args:
            artifacts: RunArtifacts with .output_dir, .stdout, .stderr,
                      .succeeded, .duration_seconds

        Returns:
            Float score. Higher = better.
        """
        # Run your security scanner on artifacts.output_dir
        issues = run_bandit(artifacts.output_dir)
        # Normalize: 1.0 = no issues, 0.0 = critical issues
        return max(0.0, 1.0 - len(issues) * 0.1)
```

Register in `pyproject.toml`:

```toml
[project.entry-points."retort.scorers"]
security_audit = "my_package:SecurityAuditScorer"
```

Then add `security_audit` to the `responses` list in `workspace.yaml`.

## Custom runners

A runner provisions an isolated environment, executes the AI agent, and tears down.

```python
from retort.playpen.runner import PlaypenRunner, StackConfig, TaskSpec

class KubernetesRunner(PlaypenRunner):
    """Run experiments in ephemeral K8s pods."""

    def provision(self, stack: StackConfig, task: TaskSpec) -> str:
        """Create an isolated environment. Return an env_id."""
        # Create a K8s pod with the right language/framework
        pod_name = create_pod(stack.language, stack.framework)
        return pod_name

    def execute(self, env_id: str, stack: StackConfig, task: TaskSpec):
        """Run the AI agent in the environment. Return RunArtifacts."""
        # Copy task spec into pod, invoke the agent, collect output
        return run_in_pod(env_id, stack.agent, task)

    def teardown(self, env_id: str) -> None:
        """Clean up the environment."""
        delete_pod(env_id)
```

Register in `pyproject.toml`:

```toml
[project.entry-points."retort.runners"]
kubernetes = "my_package:KubernetesRunner"
```

Then set `playpen.runner: kubernetes` in `workspace.yaml`.

## Custom task sources

Tasks define what the AI agent builds. Each task needs:

- `task.yaml` — Functional specification the agent receives as a prompt
- `validate.py` — Automated checks that verify the output

### task.yaml structure

```yaml
name: my-custom-task
description: Build a REST API with user authentication
language_agnostic: true

requirements:
  - POST /users creates a new user
  - GET /users/:id returns user details
  - POST /auth/login returns a JWT token
  - All endpoints validate input

validation:
  - endpoint_tests: true
  - schema_validation: true
```

### validate.py structure

```python
def validate(output_dir: str) -> dict:
    """Validate the agent's output.

    Args:
        output_dir: Path to the generated code

    Returns:
        Dict with 'passed' (bool) and 'details' (str)
    """
    # Check the code builds, tests pass, endpoints work
    return {"passed": True, "details": "All 4 endpoints verified"}
```

### Using a custom task

```yaml
tasks:
  - source: local://./my-custom-task
  - source: git://github.com/my-org/my-task-repo
```

Git sources are cloned at experiment time. The repo root must contain `task.yaml` and `validate.py`.

## Built-in scorers

Retort ships with these scorers:

| Scorer | Measures |
|--------|----------|
| `code_quality` | Lint pass rate, cyclomatic complexity, type coverage |
| `token_efficiency` | API tokens consumed per unit of functionality |
| `build_time` | Seconds to first successful build |
| `test_coverage` | Percentage of code covered by generated tests |
| `defect_rate` | Fraction of validation checks that fail |
| `maintainability` | Success rate when a different agent modifies the code |
| `idiomatic` | LLM-as-judge rating of convention adherence (opt-in: per-run claude haiku call) |
