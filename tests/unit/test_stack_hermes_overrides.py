"""A preset must be able to vary an AGENT setting, not just a model setting.

exp-62 varies exactly one thing — Hermes' `verify_on_stop` — across two arms on
the same model. Before this, both arms shared one `serving.hermes_config` file
and `_sig()` did not look at agent settings, so the two presets were
indistinguishable, `ensure()` returned early, and the second arm would have run
on the first arm's config while reporting itself as the second.

That is not a slow reload. It is an experiment that measures one arm twice and
reports a null, which is the most expensive kind of wrong answer. The same class
of bug was already fixed once for `cache_gb`; this generalises it.
"""
from __future__ import annotations

import pytest

from retort.playpen.stack_reload import _sig


def _preset(**over):
    base = {"model": "qwen-80b", "context_length": 262144,
            "sampling": {"temperature": 0.7}}
    base.update(over)
    return base


class TestReloadSignature:
    def test_two_arms_differing_only_in_verify_on_stop_are_distinguishable(self):
        """The exp-62 design, exactly."""
        off = _preset(hermes={"verify_on_stop": False})
        on = _preset(hermes={"verify_on_stop": True})
        assert _sig(off) != _sig(on), (
            "identical signatures -> ensure() skips the reload -> arm B silently "
            "inherits arm A's agent config")

    def test_identical_presets_still_share_a_signature(self):
        """The early return is a real optimisation; do not break it."""
        assert _sig(_preset(hermes={"verify_on_stop": True})) == \
               _sig(_preset(hermes={"verify_on_stop": True}))

    def test_a_preset_without_overrides_is_unchanged(self):
        """Existing stacks.yaml files carry no `hermes:` block and must keep
        producing a stable signature across runs."""
        assert _sig(_preset()) == _sig(_preset())

    def test_key_order_does_not_change_the_signature(self):
        a = _preset(hermes={"verify_on_stop": True, "max_turns": 200})
        b = _preset(hermes={"max_turns": 200, "verify_on_stop": True})
        assert _sig(a) == _sig(b)

    def test_nested_override_values_do_not_explode(self):
        """YAML gives dicts and lists; a signature must stay hashable."""
        a = _preset(hermes={"verify": {"recipes": ["http", "cli"]}})
        b = _preset(hermes={"verify": {"recipes": ["http"]}})
        assert hash(_sig(a)) != hash(_sig(b))


class TestConfigWriting:
    def test_overrides_are_written_into_the_hermes_config(self, tmp_path):
        import yaml

        from retort.playpen.stack_reload import _BaseStackManager

        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.safe_dump(
            {"model": "old", "max_turns": 50, "verify_on_stop": False}))

        mgr = _BaseStackManager.__new__(_BaseStackManager)
        mgr.serving = {"hermes_config": str(cfg)}
        mgr._ensure_hermes_model("qwen-80b", 262144, 200,
                                 {"verify_on_stop": True})

        written = yaml.safe_load(cfg.read_text())
        assert written["verify_on_stop"] is True, "the override never landed"
        assert written["model"] == "qwen-80b"
        assert written["max_turns"] == 200

    def test_an_override_beats_the_managed_keys(self, tmp_path):
        """Overrides are written last on purpose, so a preset can pin a value
        the stack manager would otherwise compute."""
        import yaml

        from retort.playpen.stack_reload import _BaseStackManager

        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.safe_dump({"model": "old", "max_turns": 50}))
        mgr = _BaseStackManager.__new__(_BaseStackManager)
        mgr.serving = {"hermes_config": str(cfg)}
        mgr._ensure_hermes_model("qwen-80b", 262144, 200, {"max_turns": 999})
        assert yaml.safe_load(cfg.read_text())["max_turns"] == 999

    def test_no_hermes_config_configured_is_not_an_error(self):
        from retort.playpen.stack_reload import _BaseStackManager

        mgr = _BaseStackManager.__new__(_BaseStackManager)
        mgr.serving = {}
        mgr._ensure_hermes_model("m", 1000, 10, {"verify_on_stop": True})


class TestNestedOverrides:
    """Hermes' settings are NESTED, and a flat write is a silent no-op.

    The real ~/.hermes/config.yaml carries

        agent:
          verify_on_stop: false

    The first version of this feature assigned cfg["verify_on_stop"] at the top
    level. That adds a key Hermes never reads while the nested one stays false —
    so BOTH arms of exp-62 would have run verify-OFF and the experiment would have
    reported a confident null. Caught by writing into a copy of the real config
    before running anything, which is what "verify the parameter takes effect"
    means in practice.
    """

    def _cfg(self, tmp_path):
        import yaml
        p = tmp_path / "config.yaml"
        p.write_text(yaml.safe_dump({
            "model": "old", "max_turns": 50,
            "agent": {"verify_on_stop": False, "some_sibling": "keep me"},
        }, sort_keys=False))
        return p

    def _apply(self, cfg, overrides):
        from retort.playpen.stack_reload import _BaseStackManager
        mgr = _BaseStackManager.__new__(_BaseStackManager)
        mgr.serving = {"hermes_config": str(cfg)}
        mgr._ensure_hermes_model("qwen-80b", 262144, 200, overrides)
        import yaml
        return yaml.safe_load(cfg.read_text())

    def test_a_nested_override_lands_where_hermes_reads_it(self, tmp_path):
        cfg = self._cfg(tmp_path)
        got = self._apply(cfg, {"agent": {"verify_on_stop": True}})
        assert got["agent"]["verify_on_stop"] is True

    def test_it_does_not_leave_a_stray_top_level_key(self, tmp_path):
        """The bug's fingerprint: a top-level key that looks right and does
        nothing, sitting beside a nested one that is still false."""
        cfg = self._cfg(tmp_path)
        got = self._apply(cfg, {"agent": {"verify_on_stop": True}})
        assert "verify_on_stop" not in got, "flat write reintroduced"

    def test_siblings_under_the_merged_key_survive(self, tmp_path):
        """A nested override must merge, not replace — replacing `agent` would
        silently drop every other agent setting."""
        cfg = self._cfg(tmp_path)
        got = self._apply(cfg, {"agent": {"verify_on_stop": True}})
        assert got["agent"]["some_sibling"] == "keep me"

    def test_both_arms_actually_differ_in_the_file(self, tmp_path):
        """The end-to-end property exp-62 depends on."""
        cfg = self._cfg(tmp_path)
        off = self._apply(cfg, {"agent": {"verify_on_stop": False}})
        assert off["agent"]["verify_on_stop"] is False
        on = self._apply(cfg, {"agent": {"verify_on_stop": True}})
        assert on["agent"]["verify_on_stop"] is True


def test_a_misnested_override_is_warned_about(tmp_path, caplog):
    """Writing the override FLAT is the trap that started all this.

    `hermes: {verify_on_stop: true}` creates a top-level key while Hermes reads
    `agent.verify_on_stop`. The value is written, reported as written, and never
    read — the project's most expensive failure mode. Make it loud.
    """
    import logging

    import yaml

    from retort.playpen.stack_reload import _BaseStackManager

    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.safe_dump({"model": "old", "agent": {"verify_on_stop": False}}))
    mgr = _BaseStackManager.__new__(_BaseStackManager)
    mgr.serving = {"hermes_config": str(cfg)}

    with caplog.at_level(logging.WARNING):
        mgr._ensure_hermes_model("m", 1000, 10, {"verify_on_stop": True})

    assert any("no-op" in r.message or "TOP-LEVEL" in r.message
               for r in caplog.records), "the silent no-op stayed silent"


def test_a_correctly_nested_override_warns_about_nothing(tmp_path, caplog):
    import logging

    import yaml

    from retort.playpen.stack_reload import _BaseStackManager

    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.safe_dump({"model": "old", "agent": {"verify_on_stop": False}}))
    mgr = _BaseStackManager.__new__(_BaseStackManager)
    mgr.serving = {"hermes_config": str(cfg)}
    with caplog.at_level(logging.WARNING):
        mgr._ensure_hermes_model("m", 1000, 10, {"agent": {"verify_on_stop": True}})
    assert not [r for r in caplog.records if "TOP-LEVEL" in r.message]
