"""Serving-backend selection (oMLX / llama.cpp / Swiftlet) in the stack manager."""

from __future__ import annotations

from pathlib import Path

import pytest

from retort.playpen.stack_reload import (
    LlamaCppStackManager,
    OmlxStackManager,
    SwiftletStackManager,
    make_stack_manager,
)


def _registry(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "stacks.yaml"
    p.write_text(body)
    return p


def test_factory_selects_backend(tmp_path: Path):
    omlx = _registry(tmp_path, "serving: {backend: omlx}\npresets: {s1: {model: m}}\n")
    assert isinstance(make_stack_manager(omlx), OmlxStackManager)

    lc = tmp_path / "lc.yaml"
    lc.write_text("serving: {backend: llamacpp}\npresets: {s1: {model: m, gguf: r/x:Q4}}\n")
    assert isinstance(make_stack_manager(lc), LlamaCppStackManager)

    # default (no backend key) -> omlx
    d = tmp_path / "d.yaml"
    d.write_text("serving: {}\npresets: {s1: {model: m}}\n")
    assert isinstance(make_stack_manager(d), OmlxStackManager)

    sw = tmp_path / "sw.yaml"
    sw.write_text("serving: {backend: swiftlet}\npresets: {s1: {model: m, qpack: /q}}\n")
    assert isinstance(make_stack_manager(sw), SwiftletStackManager)

    bad = tmp_path / "bad.yaml"
    bad.write_text("serving: {backend: nope}\npresets: {s1: {model: m}}\n")
    with pytest.raises(ValueError, match="unknown serving.backend"):
        make_stack_manager(bad)


def test_llamacpp_launch_cmd_hf_repo(tmp_path: Path):
    reg = _registry(tmp_path,
        "serving: {backend: llamacpp, host: 127.0.0.1, port: 8080, ngl: 999}\n"
        "presets:\n"
        "  laguna:\n"
        "    model: Laguna-XS-2.1\n"
        "    gguf: poolside/Laguna-XS-2.1-GGUF:Q4_K_M\n"
        "    context_length: 262144\n"
        "    sampling: {temperature: 0.6, top_p: 0.95, top_k: 20, repetition_penalty: 1.0}\n")
    m = make_stack_manager(reg)
    cmd = m._launch_cmd(m.presets["laguna"], "127.0.0.1", 8080)
    # HF repo:quant -> -hf (auto-download), served under the alias
    assert "-hf" in cmd and "poolside/Laguna-XS-2.1-GGUF:Q4_K_M" in cmd
    assert cmd[cmd.index("--alias") + 1] == "Laguna-XS-2.1"
    assert "--jinja" in cmd                                   # tool calls via template
    assert cmd[cmd.index("-ngl") + 1] == "999"               # Metal offload
    assert cmd[cmd.index("-c") + 1] == "262144"              # context length
    assert cmd[cmd.index("--temp") + 1] == "0.6"             # sampling as launch defaults
    assert cmd[cmd.index("--repeat-penalty") + 1] == "1.0"


def test_llamacpp_launch_cmd_local_gguf(tmp_path: Path):
    reg = _registry(tmp_path,
        "serving: {backend: llamacpp}\n"
        "presets: {m1: {model: mymodel, gguf: /models/foo.gguf}}\n")
    m = make_stack_manager(reg)
    cmd = m._launch_cmd(m.presets["m1"], "127.0.0.1", 8080)
    # a .gguf path -> -m (local file), not -hf
    assert "-m" in cmd and "/models/foo.gguf" in cmd
    assert "-hf" not in cmd


def _swiftlet_registry(tmp_path: Path, extra_serving: str = "", extra_preset: str = "") -> Path:
    p = tmp_path / "sw.yaml"
    p.write_text(
        "serving:\n"
        "  backend: swiftlet\n"
        "  swiftlet_bin: /opt/swiftlet-server\n"
        "  host: 127.0.0.1\n"
        "  port: 8080\n"
        "  upstream_port: 8081\n"
        f"{extra_serving}"
        "presets:\n"
        "  sw35:\n"
        "    model: Qwen3.6-35B-A3B\n"
        "    qpack: /Volumes/models/q35-qpack\n"
        "    cache_gb: 12\n"
        "    context_length: 262144\n"
        f"{extra_preset}"
    )
    return p


def test_swiftlet_launch_cmd(tmp_path: Path):
    m = make_stack_manager(_swiftlet_registry(tmp_path))
    cmd = m._launch_cmd(m.presets["sw35"], 8081)
    assert cmd[0] == "/opt/swiftlet-server"
    assert cmd[cmd.index("--model") + 1] == "/Volumes/models/q35-qpack"
    # swiftlet-server takes the INTERNAL port; the shim owns the one Hermes uses
    assert cmd[cmd.index("--port") + 1] == "8081"
    assert cmd[cmd.index("--cache-gb") + 1] == "12"


def test_swiftlet_shim_fronts_the_public_port(tmp_path: Path):
    """Hermes must reach the shim, never swiftlet-server directly."""
    m = make_stack_manager(_swiftlet_registry(tmp_path))
    cmd = m._shim_cmd(m.presets["sw35"], "127.0.0.1", 8080, 8081)
    assert "retort.playpen.swiftlet_shim" in cmd
    assert cmd[cmd.index("--listen-port") + 1] == "8080"
    assert cmd[cmd.index("--upstream-port") + 1] == "8081"
    # the shim advertises the design's model id, not Swiftlet's arch string
    assert cmd[cmd.index("--model-name") + 1] == "Qwen3.6-35B-A3B"


def test_swiftlet_refuses_sampling_it_cannot_enforce(tmp_path: Path):
    """The temp-1.0 lesson, enforced in code.

    swiftlet-server has no sampling flags, so a declared `sampling:` block would be
    silently ignored and the run would be published at Swiftlet's built-in 0.7/0.8
    while provenance claimed otherwise.
    """
    reg = _swiftlet_registry(tmp_path, extra_preset="    sampling: {temperature: 0.6}\n")
    m = make_stack_manager(reg)
    with pytest.raises(ValueError, match="cannot enforce sampling"):
        m._check_sampling(m.presets["sw35"])


def test_swiftlet_sampling_override_is_explicit(tmp_path: Path):
    reg = _swiftlet_registry(
        tmp_path,
        extra_serving="  allow_unenforced_sampling: true\n",
        extra_preset="    sampling: {temperature: 0.6}\n",
    )
    m = make_stack_manager(reg)
    m._check_sampling(m.presets["sw35"])  # acknowledged -> warns, does not raise


def test_cache_gb_change_forces_a_reload(tmp_path: Path):
    """The expert-cache sweep is the reason this backend exists.

    Without cache_gb in the signature, consecutive cells at different budgets would
    reuse the first server and the whole sweep would silently measure one setting.
    """
    from retort.playpen.stack_reload import _sig
    base = {"model": "m", "qpack": "/q", "context_length": 262144}
    assert _sig({**base, "cache_gb": 8}) != _sig({**base, "cache_gb": 24})
    assert _sig({**base, "cache_gb": 8}) == _sig({**base, "cache_gb": 8})


def test_swiftlet_prompt_tokens_parse_from_its_own_log(tmp_path: Path):
    """peak_prompt_tokens must understand Swiftlet's log line, not oMLX's."""
    log = tmp_path / "serving.log"
    log.write_text(
        "[chatcmpl-1a2b3c4d] 21806 prompt + 238 generated, prefill 12.4s, 7.30 tok/s\n"
        "[chatcmpl-2b3c4d5e] 88358 prompt + 412 generated, prefill 44.1s, 6.90 tok/s\n"
    )
    reg = _swiftlet_registry(tmp_path, extra_serving=f"  log: {log}\n")
    m = make_stack_manager(reg)
    assert m.peak_prompt_tokens(0) == 88358


def test_hermes_max_turns_is_written_from_the_workspace(tmp_path):
    """Hermes' turn cap must agree with the workspace's `playpen.max_turns`.

    Regression: Hermes takes max_turns from its config file (it has no CLI flag),
    so it ran at whatever the file said — 30 — while workspaces declared 200.
    provenance.json recorded both values without flagging the disagreement, and a
    local run needing >30 turns was truncated and scored as a model failure.
    """
    import yaml as _yaml
    from retort.playpen.stack_reload import OmlxStackManager

    hermes_cfg = tmp_path / "hermes.yaml"
    hermes_cfg.write_text(_yaml.safe_dump({
        "model": "old-model", "context_length": 131072, "max_turns": 30,
        "providers": {"mlxlocal": {"default_model": "old-model", "models": {}}},
    }))
    registry = tmp_path / "stacks.yaml"
    registry.write_text(_yaml.safe_dump({
        "serving": {"hermes_config": str(hermes_cfg)},
        "presets": {"m35": {"model": "Qwen3.6-35B-A3B", "context_length": 262144}},
    }))

    mgr = OmlxStackManager(registry)
    mgr.agent_max_turns = 200
    mgr._ensure_hermes_model("Qwen3.6-35B-A3B", 262144, mgr.agent_max_turns)

    cfg = _yaml.safe_load(hermes_cfg.read_text())
    assert cfg["max_turns"] == 200, "hermes would silently cap runs at its own value"
    assert cfg["context_length"] == 262144
    assert cfg["model"] == "Qwen3.6-35B-A3B"


def test_hermes_max_turns_left_alone_when_unset(tmp_path):
    """agent_max_turns=None ⇒ don't touch the file's existing value."""
    import yaml as _yaml
    from retort.playpen.stack_reload import OmlxStackManager

    hermes_cfg = tmp_path / "hermes.yaml"
    hermes_cfg.write_text(_yaml.safe_dump({"model": "m", "max_turns": 45}))
    registry = tmp_path / "stacks.yaml"
    registry.write_text(_yaml.safe_dump({
        "serving": {"hermes_config": str(hermes_cfg)},
        "presets": {"p": {"model": "m"}},
    }))
    mgr = OmlxStackManager(registry)
    mgr._ensure_hermes_model("m", None, None)
    assert _yaml.safe_load(hermes_cfg.read_text())["max_turns"] == 45
