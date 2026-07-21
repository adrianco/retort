"""Serving-backend selection (oMLX / llama.cpp) in the stack manager."""

from __future__ import annotations

from pathlib import Path

import pytest

from retort.playpen.stack_reload import (
    LlamaCppStackManager,
    OmlxStackManager,
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
