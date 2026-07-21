"""Reload the local serving stack at a design's model-selection point.

A local sweep over inference levers (sampling params, quant, model weights) is a
single retort experiment whose **model factor** names a *stack preset*. Each
preset fixes the served model plus its sampling parameters. When the experiment
advances to a cell whose preset differs from the one currently loaded, the runner
calls :meth:`ensure`, which restarts the serving layer to match and waits for it
to come back warm. Sort the design by preset and reloads happen only at each
boundary.

**Two serving backends are supported**, selected by ``serving.backend`` (default
``omlx``). Both expose the same OpenAI-compatible endpoint on ``host:port``, so the
Hermes agent talks to either one transparently:

- **oMLX** (Apple-Silicon MLX): fastest for the arches its bundled ``mlx-lm``
  supports (Qwen, DeepSeek, …) and the tool formats it parses (Qwen/Llama/Harmony).
- **llama.cpp** (``llama-server``): Metal-native, serves **GGUF**, and renders tool
  calls from the model's own chat template via ``--jinja`` — so it handles models
  oMLX can't (custom tool formats like Mistral ``[TOOL_CALLS]`` or poolside's XML,
  and arches mlx-lm lacks). This is how a model outside oMLX's support gets tested.

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
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
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

# sampling key -> llama-server CLI flag (min_p/others map directly)
_LLAMA_SAMPLING_FLAG = {
    "temperature": "--temp",
    "top_p": "--top-p",
    "top_k": "--top-k",
    "min_p": "--min-p",
    "repetition_penalty": "--repeat-penalty",
}


def _sig(preset: dict[str, Any]) -> tuple:
    """A hashable signature: reload iff (model, gguf, context_length, sampling) changes."""
    s = preset.get("sampling", {}) or {}
    return (
        preset.get("model"),
        preset.get("gguf"),
        preset.get("context_length"),
        tuple((k, s.get(k)) for k in _SAMPLING_KEYS),
    )


def make_stack_manager(registry_path: str | Path) -> "_BaseStackManager":
    """Build the stack manager for the backend named in ``serving.backend``
    (default ``omlx``)."""
    data = yaml.safe_load(Path(registry_path).read_text()) or {}
    backend = (data.get("serving", {}) or {}).get("backend", "omlx")
    if backend == "omlx":
        return OmlxStackManager(registry_path)
    if backend in ("llamacpp", "llama.cpp", "llama_cpp"):
        return LlamaCppStackManager(registry_path)
    raise ValueError(f"unknown serving.backend {backend!r} (expected omlx or llamacpp)")


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

    def _kill_port(self) -> None:
        port = int(self.serving.get("port", 8080))
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

    def _ensure_hermes_model(self, model: str, context_length: int | None) -> None:
        """Point Hermes at this preset's model, WITHOUT losing its context length.

        The per-model ``context_length`` is load-bearing: without it Hermes probes
        its fallback tiers (256K -> 128K -> 64K…) and lands on 128K, and lcm then
        compacts at ~85% of *that*. Never rebuild the ``models`` map (that silently
        dropped the setting when switching models); always write context length back.
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
        self._ensure_hermes_model(preset["model"], preset.get("context_length"))
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
        self._ensure_hermes_model(preset["model"], preset.get("context_length"))
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
