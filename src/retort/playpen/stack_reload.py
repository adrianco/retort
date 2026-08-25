"""Reload the local serving stack at a design's model-selection point.

A local sweep over inference levers (sampling params, quant, model weights) is a
single retort experiment whose **model factor** names a *stack preset*. Each
preset fixes the served model plus its sampling parameters. When the experiment
advances to a cell whose preset differs from the one currently loaded, the runner
calls :meth:`ensure`, which restarts the serving layer to match and waits for it
to come back warm. Sort the design by preset and reloads happen only at each
boundary.

**Three serving backends are supported**, selected by ``serving.backend`` (default
``omlx``). All expose the same OpenAI-compatible endpoint on ``host:port``, so the
Hermes agent talks to any of them transparently:

- **oMLX** (Apple-Silicon MLX): fastest for the arches its bundled ``mlx-lm``
  supports (Qwen, DeepSeek, …) and the tool formats it parses (Qwen/Llama/Harmony).
- **llama.cpp** (``llama-server``): Metal-native, serves **GGUF**, and renders tool
  calls from the model's own chat template via ``--jinja`` — so it handles models
  oMLX can't (custom tool formats like Mistral ``[TOOL_CALLS]`` or poolside's XML,
  and arches mlx-lm lacks). This is how a model outside oMLX's support gets tested.
- **Swiftlet** (``swiftlet-server``): a Swift + Metal runtime that streams routed MoE
  experts from SSD, so model size stops being bounded by RAM — the reason to care is
  models that do *not* fit (an 80B on a 32 GB box, or the Qwen3.5-397B config it
  ships), not faster inference on ones that do. Its own endpoint cannot do tool
  calls at all, so this backend launches ``swiftlet-server`` on an internal port and
  puts :mod:`retort.playpen.swiftlet_shim` in front of it to translate; see that
  module for what the translation costs. **Slow**: 7–11 tok/s (35B) / 4.5–5 tok/s
  (80B) published, against ~54/~61 measured on oMLX — budget the timeout accordingly.

The preset registry is a YAML file::

    serving:
      backend: omlx                     # or: llamacpp
      # --- oMLX fields ---
      omlx_bin: /Applications/oMLX.app/Contents/MacOS/omlx-cli
      model_dir: /Users/me/models
      settings_path: /Users/me/.omlx/settings.json
      # --- llama.cpp fields ---
      llama_bin: llama-server           # on PATH via `brew install llama.cpp`
      ngl: 999                          # layers to offload to Metal (999 = all)
      # --- swiftlet fields ---
      swiftlet_bin: swiftlet-server     # built from the Swiftlet checkout
      upstream_port: 8081               # swiftlet-server; the shim owns `port`
      shim_max_tokens: 4096             # Swiftlet's own default (512) truncates agents
      # --- shared ---
      host: 127.0.0.1
      port: 8080
      hermes_config: /Users/me/.hermes/config.yaml
      serve_flags: [...]                # extra flags passed to the server
      log: /tmp/serving.log
      warm_timeout_s: 300
    presets:
      s1:                               # oMLX preset
        model: Qwen3.6-35B-A3B
        context_length: 262144
        sampling: {temperature: 0.6, top_p: 0.95, top_k: 20, repetition_penalty: 1.0}
      laguna:                           # llama.cpp preset
        model: Laguna-XS-2.1            # the served alias Hermes addresses
        gguf: poolside/Laguna-XS-2.1-GGUF:Q4_K_M   # HF repo[:quant], or a local .gguf path
        context_length: 262144
        sampling: {temperature: 0.6, top_p: 0.95, top_k: 20, repetition_penalty: 1.0}
      sw35:                             # swiftlet preset
        model: Qwen3.6-35B-A3B          # the name Hermes addresses; the shim advertises it
        qpack: /Volumes/models/Qwen3.6-35B-A3B-qpack   # the .qpack container directory
        cache_gb: 12                    # expert-cache budget (see the sweep note below)
        context_length: 262144
        # NOTE: no `sampling:` — Swiftlet hardcodes its own and this backend
        # REFUSES a preset that declares sampling it cannot enforce.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_SAMPLING_KEYS = ("temperature", "top_p", "top_k", "min_p", "repetition_penalty")

# oMLX logs the prompt length of every completion:
#   "Chat completion: 88 tokens in 2.58s (52.0 tok/s), prompt: 21806, finish_reason=..."
_OMLX_PROMPT_RE = re.compile(r"prompt:\s*(\d+)")
# llama-server logs per-slot prompt token counts, e.g.
#   "slot update_slots: id  0 | task 0 | n_prompt_tokens = 21806 ..."
_LLAMA_PROMPT_RE = re.compile(r"n_prompt_tokens\s*[=:]\s*(\d+)")

# swiftlet-server logs one line per completion to stderr:
#   "[chatcmpl-1a2b3c4d] 21806 prompt + 238 generated, prefill 12.4s, 7.30 tok/s"
_SWIFTLET_PROMPT_RE = re.compile(r"(\d+)\s+prompt\s*\+")

# sampling key -> llama-server CLI flag (min_p/others map directly)
_LLAMA_SAMPLING_FLAG = {
    "temperature": "--temp",
    "top_p": "--top-p",
    "top_k": "--top-k",
    "min_p": "--min-p",
    "repetition_penalty": "--repeat-penalty",
}


def _sig(preset: dict[str, Any]) -> tuple:
    """A hashable signature: reload iff the served stack changes.

    ``cache_gb`` is part of it so that a Swiftlet **expert-cache sweep** — the §3
    inference lever this backend exists to measure — actually restarts the server
    between cells instead of silently reusing the previous budget.
    """
    s = preset.get("sampling", {}) or {}
    # `hermes` overrides are in the signature for the same reason `cache_gb` is:
    # two arms that differ ONLY in an agent setting produce an identical
    # signature otherwise, `ensure()` returns early, and the second arm silently
    # runs on the first arm's config. That is not a slow reload, it is a
    # confidently wrong result — exp-62 varies `verify_on_stop` and nothing else,
    # so without this it would measure one arm twice.
    h = preset.get("hermes", {}) or {}
    return (
        preset.get("model"),
        preset.get("gguf"),
        preset.get("qpack"),
        preset.get("cache_gb"),
        preset.get("context_length"),
        tuple((k, s.get(k)) for k in _SAMPLING_KEYS),
        tuple(sorted((str(k), _hashable(v)) for k, v in h.items())),
    )


def _find_nested(cfg: dict, key: str, _depth: int = 0) -> str | None:
    """Path to ``key`` if it exists somewhere BELOW the top level, else None."""
    if _depth > 4:
        return None
    for k, v in cfg.items():
        if not isinstance(v, dict):
            continue
        if key in v:
            return f"{k}.{key}"
        found = _find_nested(v, key, _depth + 1)
        if found:
            return f"{k}.{found}"
    return None


def _warn_misnested(cfg: dict, overrides: dict) -> None:
    """Shout when an override would create a top-level key that really lives nested.

    This is the project's most expensive failure mode in miniature: a setting
    that is written, reported as written, and silently not read. Writing
    `hermes: {verify_on_stop: true}` puts a key at the top level while Hermes
    reads `agent.verify_on_stop`, so the toggle no-ops and the experiment reports
    a confident null. Caught exactly this way while preparing exp-62.
    """
    for key, value in overrides.items():
        if key in cfg or isinstance(value, dict):
            continue
        nested = _find_nested(cfg, key)
        if nested:
            logger.warning(
                "hermes override %r would create a NEW TOP-LEVEL key, but %r "
                "already exists at %r — this almost certainly no-ops. Nest the "
                "override to match the config: hermes: {%s: {...}}",
                key, key, nested, nested.split(".")[0],
            )


def _deep_merge(dst: dict, src: dict) -> bool:
    """Merge ``src`` into ``dst`` in place. True if anything changed.

    Nested dicts merge rather than replace, so setting one key under ``agent``
    does not delete its siblings.
    """
    changed = False
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            if _deep_merge(dst[key], value):
                changed = True
        elif dst.get(key) != value:
            dst[key] = value
            changed = True
    return changed


def _hashable(v: Any) -> Any:
    """Make a nested config value usable in a signature tuple."""
    if isinstance(v, dict):
        return tuple(sorted((str(k), _hashable(x)) for k, x in v.items()))
    if isinstance(v, list):
        return tuple(_hashable(x) for x in v)
    return v


def make_stack_manager(registry_path: str | Path) -> "_BaseStackManager":
    """Build the stack manager for the backend named in ``serving.backend``
    (default ``omlx``)."""
    data = yaml.safe_load(Path(registry_path).read_text()) or {}
    backend = (data.get("serving", {}) or {}).get("backend", "omlx")
    if backend == "omlx":
        return OmlxStackManager(registry_path)
    if backend in ("llamacpp", "llama.cpp", "llama_cpp"):
        return LlamaCppStackManager(registry_path)
    if backend == "swiftlet":
        return SwiftletStackManager(registry_path)
    raise ValueError(
        f"unknown serving.backend {backend!r} (expected omlx, llamacpp or swiftlet)"
    )


class _BaseStackManager:
    """Backend-agnostic stack manager: preset bookkeeping, readiness/warm probes,
    peak-context telemetry, and the Hermes config update. Subclasses implement
    ``_apply`` (the backend-specific restart)."""

    _prompt_re: re.Pattern = _OMLX_PROMPT_RE

    def __init__(self, registry_path: str | Path) -> None:
        data = yaml.safe_load(Path(registry_path).read_text()) or {}
        self.serving: dict[str, Any] = data.get("serving", {})
        self.presets: dict[str, dict] = data.get("presets", {})
        if not self.presets:
            raise ValueError(f"no presets in stack registry {registry_path}")
        self._loaded_sig: tuple | None = None
        # Workspace `playpen.max_turns`, written into the Hermes config on each
        # reload. Hermes has no --max-turns CLI flag, so the config file is the
        # only way to make its cap agree with the one the experiment declared.
        # Left None ⇒ leave whatever the file says (and it said 30, silently
        # truncating local runs — see _ensure_hermes_model).
        self.agent_max_turns: int | None = None

    # -- public API ---------------------------------------------------------

    def ensure(self, preset_name: str | None) -> None:
        """Reload the stack for ``preset_name`` unless it is already loaded."""
        if preset_name is None or preset_name not in self.presets:
            logger.warning(
                "stack preset %r not in registry; leaving server as-is", preset_name
            )
            return
        preset = self.presets[preset_name]
        sig = _sig(preset)
        if sig == self._loaded_sig:
            return  # already the active stack — no reload at this cell
        logger.info("reloading serving stack -> preset %s (%s)", preset_name, sig)
        self._apply(preset)
        self._loaded_sig = sig

    # -- peak context -------------------------------------------------------

    def log_offset(self) -> int:
        """Current size of the serving log — a cursor to measure one run from."""
        try:
            return Path(self.serving.get("log", "/tmp/serving.log")).stat().st_size
        except OSError:
            return 0

    def peak_prompt_tokens(self, since_offset: int) -> int | None:
        """Largest prompt (context) the model was fed since ``since_offset`` —
        best-effort, parsed from the serving log (returns None if unavailable)."""
        path = Path(self.serving.get("log", "/tmp/serving.log"))
        try:
            with open(path, "rb") as f:
                f.seek(since_offset)
                chunk = f.read()
        except OSError:
            return None
        peaks = self._prompt_re.findall(chunk.decode("utf-8", "replace"))
        return max((int(p) for p in peaks), default=None)

    # -- shared internals ---------------------------------------------------

    def _apply(self, preset: dict) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def _kill_port(self, port: int | None = None) -> None:
        port = int(self.serving.get("port", 8080)) if port is None else int(port)
        pids = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"], capture_output=True, text=True
        ).stdout.split()
        for pid in pids:
            subprocess.run(["kill", "-9", pid], capture_output=True)
        time.sleep(3)

    def _launch(self, cmd: list[str]) -> None:
        log_path = self.serving.get("log", "/tmp/serving.log")
        log_f = open(log_path, "ab")
        # Detached so it outlives this call; the port-kill above reclaims it next reload.
        subprocess.Popen(cmd, stdout=log_f, stderr=log_f, start_new_session=True)

    def _ensure_hermes_model(
        self, model: str, context_length: int | None, max_turns: int | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> None:
        """Point Hermes at this preset's model, WITHOUT losing its context length.

        The per-model ``context_length`` is load-bearing: without it Hermes probes
        its fallback tiers (256K -> 128K -> 64K…) and lands on 128K, and lcm then
        compacts at ~85% of *that*. Never rebuild the ``models`` map (that silently
        dropped the setting when switching models); always write context length back.

        ``max_turns`` is equally load-bearing and was NOT managed here until
        2026-07-25. Hermes takes its turn cap from this config file (it has no CLI
        flag), so it ran at whatever the file happened to say — 30 — while retort's
        workspace declared 200 and `provenance.json` dutifully recorded *both*
        without anyone noticing they disagreed. A local run needing more than 30
        turns was silently truncated and scored as a failure, indistinguishable
        from a model that could not do the task. Three of exp-39's twelve brazil
        runs stopped at exactly 90 api_calls (3 per turn x 30), two with near-zero
        coverage — which is why the local hard-task "capability wall" needs
        re-testing with the cap lifted.
        """
        cfg_path = self.serving.get("hermes_config")
        if not cfg_path:
            return
        cfg_path = Path(cfg_path)
        cfg = yaml.safe_load(cfg_path.read_text()) or {}
        prov = (cfg.get("providers") or {}).get("mlxlocal")

        changed = False
        if cfg.get("model") != model:
            cfg["model"] = model
            changed = True
        if max_turns and cfg.get("max_turns") != max_turns:
            cfg["max_turns"] = max_turns
            changed = True
        if context_length and cfg.get("context_length") != context_length:
            cfg["context_length"] = context_length
            changed = True
        if prov is not None:
            if prov.get("default_model") != model:
                prov["default_model"] = model
                changed = True
            models = prov.setdefault("models", {}) or {}
            entry = dict(models.get(model) or {})
            if context_length and entry.get("context_length") != context_length:
                entry["context_length"] = context_length
                changed = True
            if models.get(model) != entry:
                models[model] = entry
                changed = True
            prov["models"] = models
        # Arbitrary per-preset agent settings, written LAST so a preset can
        # override anything above it. This is what lets an experiment vary an
        # agent capability (`verify_on_stop`) as a factor instead of editing a
        # single shared config file by hand between arms.
        #
        # DEEP MERGE, because Hermes' settings are NESTED and a flat write is a
        # silent no-op. The real config carries
        #
        #     agent:
        #       verify_on_stop: false
        #
        # so assigning cfg["verify_on_stop"] adds a top-level key Hermes never
        # reads while the nested one stays false — both arms of exp-62 would have
        # run verify-OFF and reported a null. Mirror the config's own shape:
        # `hermes: {agent: {verify_on_stop: true}}` merges into `agent`, leaving
        # its siblings intact.
        _warn_misnested(cfg, overrides or {})
        if _deep_merge(cfg, overrides or {}):
            changed = True
        if changed:
            cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))

    def _wait_ready(self, model: str, timeout_s: int | None = None) -> None:
        host = self.serving.get("host", "127.0.0.1")
        port = int(self.serving.get("port", 8080))
        deadline = time.monotonic() + (timeout_s or int(self.serving.get("warm_timeout_s", 300)))
        url = f"http://{host}:{port}/v1/models"
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=5) as r:
                    # llama-server may serve under the alias; accept any 200 that
                    # lists a model, and match by name when present.
                    body = r.read().decode("utf-8", "replace")
                    if model in body or '"object"' in body:
                        return
            except Exception:
                pass
            time.sleep(3)
        raise RuntimeError(f"server did not expose model {model!r} within timeout")

    def _warm(self, model: str) -> None:
        """One tiny generation so the model is resident before the timed run."""
        host = self.serving.get("host", "127.0.0.1")
        port = int(self.serving.get("port", 8080))
        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 2,
        }).encode()
        req = urllib.request.Request(
            f"http://{host}:{port}/v1/chat/completions",
            data=body, headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=int(self.serving.get("warm_timeout_s", 300)))
        except Exception as exc:
            logger.warning("warm request failed (continuing): %s", exc)


class OmlxStackManager(_BaseStackManager):
    """Serve MLX models via oMLX (Apple-Silicon mlx-lm)."""

    _prompt_re = _OMLX_PROMPT_RE

    def _apply(self, preset: dict) -> None:
        self._write_sampling(preset.get("sampling", {}) or {})
        self._ensure_hermes_model(
            preset["model"], preset.get("context_length"), self.agent_max_turns,
            preset.get("hermes"),
        )
        self._restart_server()
        self._wait_ready(preset["model"])
        self._warm(preset["model"])

    def _write_sampling(self, sampling: dict) -> None:
        """Patch oMLX settings.json sampling — the request default oMLX applies
        when the client (Hermes) omits sampling params (verified honored)."""
        path = Path(self.serving["settings_path"])
        settings = json.loads(path.read_text())
        s = settings.setdefault("sampling", {})
        for k in _SAMPLING_KEYS:
            if k in sampling and sampling[k] is not None:
                s[k] = sampling[k]
        path.write_text(json.dumps(settings, indent=2))

    def _restart_server(self) -> None:
        host = self.serving.get("host", "127.0.0.1")
        port = int(self.serving.get("port", 8080))
        self._kill_port()
        cmd = [
            self.serving["omlx_bin"], "serve",
            "--model-dir", self.serving["model_dir"],
            "--host", host, "--port", str(port),
            *self.serving.get("serve_flags", []),
        ]
        self._launch(cmd)


class LlamaCppStackManager(_BaseStackManager):
    """Serve GGUF models via llama.cpp's ``llama-server`` (Metal-native).

    Renders tool calls from the model's own chat template with ``--jinja``, so it
    handles tool formats oMLX can't parse. Sampling is baked into the launch as
    server defaults (llama-server has no runtime settings file); the model source
    is the preset's ``gguf`` (a local ``.gguf`` path, or an HF ``repo[:quant]`` that
    llama-server downloads), served under the preset's ``model`` name via ``--alias``.
    """

    _prompt_re = _LLAMA_PROMPT_RE

    def _apply(self, preset: dict) -> None:
        # llama-server takes sampling as launch-time defaults, so there is no
        # separate settings write — it's folded into the restart.
        self._ensure_hermes_model(
            preset["model"], preset.get("context_length"), self.agent_max_turns,
            preset.get("hermes"),
        )
        self._restart_server(preset)
        self._wait_ready(preset["model"])
        self._warm(preset["model"])

    def _restart_server(self, preset: dict) -> None:
        host = self.serving.get("host", "127.0.0.1")
        port = int(self.serving.get("port", 8080))
        self._kill_port()
        cmd = self._launch_cmd(preset, host, port)
        self._launch(cmd)

    def _launch_cmd(self, preset: dict, host: str, port: int) -> list[str]:
        gguf = str(preset["gguf"])
        model_flag = (
            ["-m", gguf]
            if (gguf.endswith(".gguf") or gguf.startswith(("/", "~", ".")))
            else ["-hf", gguf]
        )
        cmd = [
            self.serving.get("llama_bin", "llama-server"),
            *model_flag,
            "--alias", str(preset["model"]),          # serve under the design's model id
            "--host", host, "--port", str(port),
            "-ngl", str(self.serving.get("ngl", 999)),  # offload all layers to Metal
            "--jinja",                                   # tool calls via the model's template
        ]
        if preset.get("context_length"):
            cmd += ["-c", str(preset["context_length"])]
        for k, v in (preset.get("sampling") or {}).items():
            flag = _LLAMA_SAMPLING_FLAG.get(k)
            if flag and v is not None:
                cmd += [flag, str(v)]
        cmd += list(self.serving.get("serve_flags", []))
        return cmd


class SwiftletStackManager(_BaseStackManager):
    """Serve ``.qpack`` models via Swiftlet, fronted by the tool-calling shim.

    Two processes per reload, because Swiftlet's endpoint cannot do tool calls:

    - ``swiftlet-server`` on ``serving.upstream_port`` (default 8081), and
    - :mod:`retort.playpen.swiftlet_shim` on ``serving.port`` — the address Hermes
      is pointed at. The shim renders ``tools`` into the prompt and parses
      ``<tool_call>`` tags back into OpenAI ``tool_calls``.

    **Sampling is not configurable and this class refuses to pretend otherwise.**
    ``swiftlet-server`` exposes no sampling flags at all; ``SwiftletSession``
    hardcodes temperature 0.7 / top-p 0.8 and bans EOS below a minimum length. A
    preset that declares ``sampling:`` here would be silently ignored — the exact
    set-but-unverified failure that made "the 35B scores 0.38" really mean "0.38 *at
    temp 1.0*". So a declared sampling block raises unless
    ``serving.allow_unenforced_sampling: true`` says the divergence is understood.

    **``cache_gb`` is passed but unenforceable on the stock binary**, and that is
    worth stating plainly: ``Sources/SwiftletServer/main.swift`` builds a
    ``QwenCPUModel`` with ``retainAllLayers = true`` — the *CPU* path. The Metal
    expert cache (``QwenMetalModel(modelDir:cacheBudgetGB:)``) and its ``--cache-gb``
    flag exist only on the ``swiftlet`` CLI's ``--gpu`` path. Until the server is
    taught to use the Metal model, a cache sweep through this backend measures
    nothing. The flag is emitted so it works the moment that lands, and
    :meth:`_launch_cmd` is the one place to change.
    """

    _prompt_re = _SWIFTLET_PROMPT_RE

    def _apply(self, preset: dict) -> None:
        self._check_sampling(preset)
        self._ensure_hermes_model(
            preset["model"], preset.get("context_length"), self.agent_max_turns,
            preset.get("hermes"),
        )
        self._restart_server(preset)
        self._wait_ready(preset["model"])
        self._warm(preset["model"])

    def _check_sampling(self, preset: dict) -> None:
        declared = {
            k: v for k, v in (preset.get("sampling") or {}).items() if v is not None
        }
        if not declared or self.serving.get("allow_unenforced_sampling"):
            if declared:
                logger.warning(
                    "swiftlet cannot enforce sampling %s; running at its built-in "
                    "temperature 0.7 / top_p 0.8 (allow_unenforced_sampling is set)",
                    declared,
                )
            return
        raise ValueError(
            f"swiftlet backend cannot enforce sampling {sorted(declared)} — "
            "swiftlet-server has no sampling flags and SwiftletSession hardcodes "
            "temperature 0.7 / top_p 0.8. Drop the sampling block from the preset, "
            "or set serving.allow_unenforced_sampling: true to record that the "
            "run does NOT use the declared values."
        )

    def _restart_server(self, preset: dict) -> None:
        host = self.serving.get("host", "127.0.0.1")
        port = int(self.serving.get("port", 8080))
        upstream_port = int(self.serving.get("upstream_port", 8081))
        self._kill_port(port)
        self._kill_port(upstream_port)
        self._launch(self._launch_cmd(preset, upstream_port))
        self._launch(self._shim_cmd(preset, host, port, upstream_port))

    def _launch_cmd(self, preset: dict, upstream_port: int) -> list[str]:
        """The ``swiftlet-server`` command.

        Note it binds 127.0.0.1 itself and takes no ``--host``; only the shim is
        reachable on ``serving.host``.
        """
        cmd = [
            str(self.serving.get("swiftlet_bin", "swiftlet-server")),
            "--model", str(preset["qpack"]),
            "--port", str(upstream_port),
        ]
        if preset.get("cache_gb") is not None:
            # No-op on the stock CPU-path server; see the class docstring.
            cmd += ["--cache-gb", str(preset["cache_gb"])]
        cmd += list(self.serving.get("serve_flags", []))
        return cmd

    def _shim_cmd(
        self, preset: dict, host: str, port: int, upstream_port: int
    ) -> list[str]:
        return [
            sys.executable, "-m", "retort.playpen.swiftlet_shim",
            "--listen-host", host,
            "--listen-port", str(port),
            "--upstream-port", str(upstream_port),
            "--model-name", str(preset["model"]),
            "--read-timeout-s", str(int(self.serving.get("warm_timeout_s", 300)) * 6),
            "--max-tokens", str(int(self.serving.get("shim_max_tokens", 4096))),
        ]
