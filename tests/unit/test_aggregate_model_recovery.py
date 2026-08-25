"""A blank `model` column is recoverable from the design's agent profile.

exp-16..exp-27 predate the model being written into `stack.json`, so
`model_from_archives` correctly finds nothing and 251 master.db rows aggregated
blank -- which is why the reporting layer had to guess a stack from the
experiment slug. Those designs did declare the model, just not as a design
column: `playpen.local_agents.<name>.model`.

That is design-declared evidence, the same grade as a `model` factor level, and
it must be resolved PER AGENT: exp-12 ran `qwen-local` and `llama-local` on
different models in one experiment.
"""
from __future__ import annotations

from pathlib import Path

from retort.analysis.aggregate import models_from_agent_profiles


def _ws(tmp_path: Path, body: str) -> Path:
    (tmp_path / "workspace.yaml").write_text(body)
    return tmp_path


def test_recovers_a_single_agent_model(tmp_path: Path):
    d = _ws(tmp_path, """
playpen:
  local_agents:
    hermes-local: { harness: hermes, model: mlxlocal/Qwen3-Coder-Next }
""")
    assert models_from_agent_profiles(d) == {"hermes-local": "mlxlocal/Qwen3-Coder-Next"}


def test_keys_by_agent_so_a_two_model_experiment_is_not_collapsed(tmp_path: Path):
    # exp-12's real shape. A single per-experiment value would mis-attribute
    # half these rows.
    d = _ws(tmp_path, """
playpen:
  local_agents:
    qwen-local:  { harness: omp, model: lmlocal/qwen2.5-coder:7b }
    llama-local: { harness: omp, model: lmlocal/llama3.2:3b }
""")
    assert models_from_agent_profiles(d) == {
        "qwen-local": "lmlocal/qwen2.5-coder:7b",
        "llama-local": "lmlocal/llama3.2:3b",
    }


def test_agent_without_a_model_is_omitted_rather_than_guessed(tmp_path: Path):
    d = _ws(tmp_path, """
playpen:
  local_agents:
    hermes-0205: { harness: hermes }
""")
    assert models_from_agent_profiles(d) == {}


def test_missing_or_damaged_workspace_returns_empty(tmp_path: Path):
    assert models_from_agent_profiles(tmp_path) == {}
    (tmp_path / "workspace.yaml").write_text("playpen: [this is not a mapping\n")
    assert models_from_agent_profiles(tmp_path) == {}
