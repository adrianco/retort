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
