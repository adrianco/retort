"""Capture the FULL stack an experiment actually ran on.

Every wrong conclusion in this project so far traced back to a stack variable we
did not record:

* the local leaderboard was measured at oMLX's default ``temperature=1.0`` — nobody
  wrote the sampling params down, so "the 35B scores 0.38" was really "the 35B
  scores 0.38 *at temp 1.0*";
* playpens lived under ``/var/folders``, where Hermes refuses to write — a harness
  path, unrecorded, produced a fake "capability wall";
* the 30B's 0.33 came from the ``omp`` agent, but was later compared against
  Hermes runs as though the agent were the same.

A pass-proportion is meaningless without the stack it was measured on. So the
stack itself is a **reported result**: versions, model revisions, sampling params,
agent config, and the harness settings that turned out to matter — captured at run
start, written next to the data, and quotable in the write-up.

Every probe is best-effort: a missing tool records ``null`` rather than failing the
run.
"""

from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path
from typing import Any

_TIMEOUT = 10


def _sh(cmd: list[str]) -> str | None:
    """Run a probe command, returning its first line or None."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=_TIMEOUT)
        out = (r.stdout or r.stderr or "").strip()
        return out.splitlines()[0][:200] if out else None
    except Exception:  # noqa: BLE001 — a probe must never break a run
        return None


def _git(repo: Path) -> dict[str, Any]:
    def g(*args: str) -> str | None:
        return _sh(["git", "-C", str(repo), *args])
    return {
        "commit": g("rev-parse", "HEAD"),
        "branch": g("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(_sh(["git", "-C", str(repo), "status", "--porcelain"])),
    }


def _host() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "machine": _sh(["sysctl", "-n", "hw.model"]) or platform.machine(),
        "cpu": _sh(["sysctl", "-n", "machdep.cpu.brand_string"]),
        "ram_bytes": _sh(["sysctl", "-n", "hw.memsize"]),
        # The GPU wired limit is a first-order constraint on which models fit.
        "iogpu_wired_limit_mb": _sh(["sysctl", "-n", "iogpu.wired_limit_mb"]),
        "python": platform.python_version(),
    }


def _hermes_bin_from(playpen_config: Any) -> str:
    """The hermes executable provenance should MEASURE.

    `_tool_versions` used to run a bare `hermes --version`, i.e. whatever is on
    PATH — which is not necessarily the binary that ran. Every local experiment
    here pins an absolute `serving.hermes_bin` precisely because hermes is often
    NOT on PATH (exp-43), so the recorded version could describe a different
    install than the one under test, or be null while runs succeeded.
    """
    for spec in (getattr(playpen_config, "local_agents", None) or {}).values():
        candidate = getattr(spec, "bin", None)
        if candidate:
            return candidate
    return "hermes"


def _tool_versions(hermes_bin: str = "hermes") -> dict[str, Any]:
    return {
        "hermes": _sh([hermes_bin, "--version"]),
        # Record WHICH binary was measured — a version with no path cannot be
        # audited after the fact.
        "hermes_bin": hermes_bin,
        "omp": _sh(["omp", "--version"]),
        "claude": _sh(["claude", "--version"]),
        "omlx": _sh(["/Applications/oMLX.app/Contents/MacOS/omlx-cli", "--version"]),
        "llama_server": _sh(["llama-server", "--version"]),
        "go": _sh(["go", "version"]),
        "node": _sh(["node", "--version"]),
        "cargo": _sh(["cargo", "--version"]),
    }


def _hermes_config() -> dict[str, Any] | None:
    """The agent config variables that changed results: model, context, plugins."""
    p = Path.home() / ".hermes" / "config.yaml"
    if not p.exists():
        return None
    try:
        import yaml
        cfg = yaml.safe_load(p.read_text()) or {}
    except Exception:  # noqa: BLE001
        return None
    prov = (cfg.get("providers") or {}).get("mlxlocal") or {}
    model = cfg.get("model")
    # The PER-MODEL context_length is the one Hermes actually honours. A top-level
    # `context_length:` can read 262144 while the model entry is empty, in which case
    # Hermes silently probes down to its 128K fallback tier — and lcm then compacts at
    # ~85% of 128K (~109K), thrashing at half the context you think you configured.
    # Report both, and flag the disagreement, so provenance can never lie about it.
    per_model = (prov.get("models") or {}).get(model, {}).get("context_length")
    top_level = cfg.get("context_length")
    return {
        "model": model,
        "context_length": per_model,          # effective
        "context_length_top_level": top_level,
        "context_length_unset_per_model": per_model is None,
        "max_turns": cfg.get("max_turns"),
        "plugins": (cfg.get("plugins") or {}).get("enabled"),
        "context_engine": (cfg.get("context") or {}).get("engine"),
        "provider_api": prov.get("api"),
        "_config_version": cfg.get("_config_version"),
    }


def _omlx_sampling() -> dict[str, Any] | None:
    """The LIVE sampling defaults the server applies when the client omits them.

    This is the variable that silently halved every local result before exp-27.
    """
    p = Path.home() / ".omlx" / "settings.json"
    if not p.exists():
        return None
    try:
        s = json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None
    return {
        "sampling": s.get("sampling"),
        "cache": s.get("cache"),
        "model_dirs": (s.get("model") or {}).get("model_dirs"),
    }


def _codex_config() -> dict[str, Any] | None:
    """What the Codex CLI actually is. Sampling is the PROVIDER's, not ours."""
    ver = _sh(["codex", "--version"])
    if ver is None:
        return None
    return {
        "cli_version": ver,
        # Recorded explicitly so nobody reads a local sampling block as this
        # run's: a hosted model's temperature/top_p are set server-side and are
        # not observable from here. Saying so beats implying a value we made up.
        "sampling": "provider-side (not observable from the client)",
    }


def _claude_code_config() -> dict[str, Any] | None:
    ver = _sh(["claude", "--version"])
    if ver is None:
        return None
    return {"cli_version": ver,
            "sampling": "provider-side (not observable from the client)"}


def _agent_harnesses(playpen_config: Any, agents: list[str] | None) -> dict[str, str]:
    """{agent name -> harness} for the agents this experiment ACTUALLY uses.

    `claude-code` is the built-in default and is not listed under `local_agents`.
    """
    declared = {k: v.harness for k, v in
                (getattr(playpen_config, "local_agents", {}) or {}).items()}
    if not agents:
        # Nothing told us which agents run; assume every declared one plus the
        # built-in, which is the old always-record-everything behaviour.
        return {**declared, "claude-code": "claude-code"}
    return {a: declared.get(a, "claude-code") for a in agents}


def _model_revisions(model_ids: list[str]) -> dict[str, Any]:
    """Resolve each model to its HF repo + snapshot revision + on-disk size.

    A bare model name is not reproducible: two 4-bit builds of "the same" model
    can differ. Pin the snapshot hash.
    """
    out: dict[str, Any] = {}
    hub = Path.home() / ".cache" / "huggingface" / "hub"
    models_dir = Path.home() / "models"
    # "mlxlocal/X" and "X" name the same model — key on the served name so a
    # provider-prefixed id and a bare one don't both appear.
    for name in sorted({m.split("/", 1)[-1] for m in model_ids}):
        mid = name
        entry: dict[str, Any] = {"served_as": name}
        # a ~/models symlink points at the real snapshot
        link = models_dir / name
        target: Path | None = None
        if link.is_symlink() or link.exists():
            target = link.resolve()
        else:
            repo = hub / f"models--{name.replace('--', '--')}"
            snaps = sorted(hub.glob(f"models--*{name.split('--')[-1]}*/snapshots/*"))
            if snaps:
                target = snaps[-1]
        if target and target.exists():
            entry["snapshot_path"] = str(target)
            entry["revision"] = target.name  # the snapshot hash = the pin
            # repo id sits two levels up: models--<org>--<name>/snapshots/<rev>
            try:
                repo_dir = target.parent.parent.name
                entry["repo"] = repo_dir.replace("models--", "").replace("--", "/", 1)
            except Exception:  # noqa: BLE001
                pass
            sz = _sh(["du", "-shL", str(target)])
            entry["size"] = sz.split()[0] if sz else None
            for f in ("config.json", "generation_config.json"):
                fp = target / f
                if fp.exists():
                    try:
                        d = json.loads(fp.read_text())
                        if f == "generation_config.json":
                            entry["recommended_sampling"] = {
                                k: d[k] for k in
                                ("temperature", "top_p", "top_k", "min_p",
                                 "repetition_penalty") if k in d
                            }
                        else:
                            tc = d.get("text_config", d)
                            entry["quant"] = (d.get("quantization") or {}).get("bits")
                            entry["max_position_embeddings"] = tc.get(
                                "max_position_embeddings"
                            )
                    except Exception:  # noqa: BLE001
                        pass
        out[name] = entry
    return out


def capture(
    *,
    repo: Path,
    config_dir: Path,
    playpen_config: Any = None,
    stack_presets: dict[str, Any] | None = None,
    model_ids: list[str] | None = None,
    agents: list[str] | None = None,
) -> dict[str, Any]:
    """Collect the stack manifest for an experiment run.

    `agents` is the set of agent levels the design actually runs. It matters
    because provenance used to record the LOCAL stack unconditionally: a Codex
    or Claude Code experiment got `agent: hermes`, `serving: oMLX 0.5.0rc1` and a
    sampling dict of `temperature 0.7, top_p 0.95, top_k 40` — none of which had
    anything to do with the run. That is not a cosmetic wart. Provenance exists
    so a result can be tied to the stack that produced it, and the whole reason
    this file exists is that unrecorded sampling silently halved the local
    numbers before exp-27. A manifest that confidently states the wrong
    sampling is worse than one that states none.
    """
    pp = playpen_config
    harness: dict[str, Any] = {}
    if pp is not None:
        harness = {
            "runner": getattr(pp, "runner", None),
            "replicates": getattr(pp, "replicates", None),
            "timeout_minutes": getattr(pp, "timeout_minutes", None),
            # These three are here because each one silently changed results before
            # it was recorded: the stall guard falsely killed slow-but-productive
            # runs; the playpen path decided whether the agent could write at all;
            # the no-write check is what now stops a broken harness masquerading as
            # an incapable model.
            "stall_minutes": getattr(pp, "stall_minutes", None),
            "max_turns": getattr(pp, "max_turns", None),
            "no_write_abort_after": getattr(pp, "no_write_abort_after", None),
            "stack_presets": getattr(pp, "stack_presets", None),
            "local_agents": {
                k: {"harness": v.harness, "model": v.model}
                for k, v in (getattr(pp, "local_agents", {}) or {}).items()
            },
        }
    try:
        from retort.playpen.local_runner import _playpen_root
        harness["playpen_root"] = str(_playpen_root())
    except Exception:  # noqa: BLE001
        pass

    ids = list(model_ids or [])
    if stack_presets:
        ids += [p.get("model") for p in stack_presets.values() if p.get("model")]

    # Record ONLY the stack the agents in play actually use.
    harnesses = _agent_harnesses(pp, agents)
    kinds = set(harnesses.values())
    agent_config: dict[str, Any] = {}
    serving: dict[str, Any] = {}
    if {"hermes", "omp", "lcm"} & kinds:
        agent_config["hermes"] = _hermes_config()
        serving["omlx"] = _omlx_sampling()
    if "codex" in kinds:
        agent_config["codex"] = _codex_config()
    if "claude-code" in kinds:
        agent_config["claude_code"] = _claude_code_config()

    return {
        "retort": _git(repo),
        "host": _host(),
        "tools": _tool_versions(_hermes_bin_from(pp)),
        "harness": harness,
        "agents": harnesses,
        "agent_config": agent_config,
        "serving": serving,
        "stack_presets": stack_presets,
        "models": _model_revisions(sorted({i for i in ids if i})),
    }


def write(manifest: dict[str, Any], config_dir: Path) -> Path:
    """Write ``provenance.json`` next to the experiment's data."""
    out = config_dir / "provenance.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str))
    return out


def summarize(manifest: dict[str, Any]) -> list[str]:
    """A few human-readable lines for the run log / RESULTS.md."""
    r = manifest.get("retort", {})
    h = manifest.get("host", {})
    t = manifest.get("tools", {})
    ac = manifest.get("agent_config", {}) or {}
    lines = [
        f"  retort   : {str(r.get('commit'))[:10]}"
        f"{' (dirty)' if r.get('dirty') else ''} on {r.get('branch')}",
        f"  host     : {h.get('machine')}  wired_limit={h.get('iogpu_wired_limit_mb')}MB",
    ]
    agents = manifest.get("agents") or {}
    if agents:
        lines.append("  agents   : " + ", ".join(f"{a} ({k})" for a, k in sorted(agents.items())))
    # Print each stack only when it is the one that ran. Printing the local
    # block for a hosted run stated sampling values that were never applied.
    hc = ac.get("hermes")
    if hc:
        lines.append(f"  agent    : hermes {t.get('hermes')}  ctx={hc.get('context_length')} "
                     f"max_turns={hc.get('max_turns')} engine={hc.get('context_engine')}")
        lines.append(f"  serving  : oMLX {t.get('omlx')}")
        lines.append(f"  sampling : {(manifest.get('serving', {}).get('omlx') or {}).get('sampling')}")
    for key, label in (("codex", "codex"), ("claude_code", "claude")):
        cfg = ac.get(key)
        if cfg:
            lines.append(f"  agent    : {label} {cfg.get('cli_version')}")
            lines.append(f"  sampling : {cfg.get('sampling')}")
    for mid, m in (manifest.get("models") or {}).items():
        lines.append(
            f"  model    : {mid} rev={str(m.get('revision'))[:12]} "
            f"quant={m.get('quant')} size={m.get('size')}"
        )
    return lines
