"""Reload the local serving stack (oMLX) at a design's model-selection point.

A local sweep over inference levers (sampling params, quant, model weights) is a
single retort experiment whose **model factor** names a *stack preset*. Each
preset fixes the served model plus its sampling parameters. When the experiment
advances to a cell whose preset differs from the one currently loaded, the runner
calls :meth:`OmlxStackManager.ensure`, which rewrites the oMLX sampling config
(and, if the weights change, the ``~/models`` symlink + Hermes default model),
restarts the oMLX server, and waits for it to come back warm. Sort the design by
preset and reloads happen only at each boundary.

The preset registry is a YAML file::

    serving:
      omlx_bin: /Applications/oMLX.app/Contents/MacOS/omlx-cli
      model_dir: /Users/me/models
      host: 127.0.0.1
      port: 8080
      settings_path: /Users/me/.omlx/settings.json
      hermes_config: /Users/me/.hermes/config.yaml
      serve_flags: ["--memory-guard", "balanced",
                    "--paged-ssd-cache-dir", "/Users/me/.cache/omlx-ssd"]
      log: /tmp/omlx-sweep.log
      warm_timeout_s: 300
    presets:
      s1:
        model: Qwen3.6-35B-A3B
        sampling: {temperature: 0.2, top_p: 0.95, top_k: 0, min_p: 0.0,
                   repetition_penalty: 1.0}
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_SAMPLING_KEYS = ("temperature", "top_p", "top_k", "min_p", "repetition_penalty")


def _sig(preset: dict[str, Any]) -> tuple:
    """A hashable signature: reload iff the (model, sampling) tuple changes."""
    s = preset.get("sampling", {}) or {}
    return (preset.get("model"), tuple((k, s.get(k)) for k in _SAMPLING_KEYS))


class OmlxStackManager:
    """Loads stack presets and (re)starts oMLX to match the requested one."""

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

    # -- internals ----------------------------------------------------------

    def _apply(self, preset: dict) -> None:
        self._write_sampling(preset.get("sampling", {}) or {})
        self._ensure_hermes_model(preset["model"])
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

    def _ensure_hermes_model(self, model: str) -> None:
        """Point Hermes' default model at this preset's served model id."""
        cfg_path = self.serving.get("hermes_config")
        if not cfg_path:
            return
        cfg_path = Path(cfg_path)
        cfg = yaml.safe_load(cfg_path.read_text()) or {}
        if cfg.get("model") == model:
            return
        cfg["model"] = model
        prov = (cfg.get("providers") or {}).get("mlxlocal")
        if prov is not None:
            prov["default_model"] = model
            prov["models"] = {model: prov.get("models", {}).get(model, {}) or {}}
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))

    def _restart_server(self) -> None:
        host = self.serving.get("host", "127.0.0.1")
        port = int(self.serving.get("port", 8080))
        # Kill whatever holds the port.
        pids = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"], capture_output=True, text=True
        ).stdout.split()
        for pid in pids:
            subprocess.run(["kill", "-9", pid], capture_output=True)
        time.sleep(3)
        cmd = [
            self.serving["omlx_bin"], "serve",
            "--model-dir", self.serving["model_dir"],
            "--host", host, "--port", str(port),
            *self.serving.get("serve_flags", []),
        ]
        log_path = self.serving.get("log", "/tmp/omlx-sweep.log")
        log_f = open(log_path, "ab")
        # Detached so it outlives this call; the port-kill above reclaims it next reload.
        subprocess.Popen(cmd, stdout=log_f, stderr=log_f, start_new_session=True)

    def _wait_ready(self, model: str, timeout_s: int | None = None) -> None:
        host = self.serving.get("host", "127.0.0.1")
        port = int(self.serving.get("port", 8080))
        deadline = time.monotonic() + (timeout_s or int(self.serving.get("warm_timeout_s", 300)))
        url = f"http://{host}:{port}/v1/models"
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=5) as r:
                    if model in r.read().decode("utf-8", "replace"):
                        return
            except Exception:
                pass
            time.sleep(3)
        raise RuntimeError(f"oMLX did not expose model {model!r} within timeout")

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
