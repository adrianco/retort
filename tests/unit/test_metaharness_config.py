import pytest
from retort import metaharness_config as mc


def test_shipped_config_valid_and_snapshot_covers_all_roles():
    snap = mc.snapshot()
    assert snap["evaluator"]["pinned"] and snap["experiment"]["pinned"]
    assert not snap["diagnose"]["pinned"]


def test_pinned_roles_refuse_routing():
    with pytest.raises(mc.MetaharnessConfigError):
        mc.resolve("evaluator", quality={"cheap": 1.0})


def test_router_picks_cheapest_qualifying_tier():
    cfg = mc.load()
    assert mc.resolve("diagnose", cfg, {"cheap": 0.95, "mid": 0.99}).model == "claude-haiku-5-5"
    # nothing qualifies -> static tier
    assert mc.resolve("diagnose", cfg, {"cheap": 0.1}).source == "tier:mid"


def test_cli_args_carry_model_and_effort():
    args = mc.resolve("eval_preflight").cli_args()
    assert args == ["--model", "claude-haiku-5-5", "--effort", "low"]
    assert mc.resolve("evaluator").cli_args() == ["--model", "claude-opus-4-8"]


def test_pinned_and_routed_overlap_rejected():
    cfg = mc.load()
    cfg["routed"]["roles"]["evaluator"] = {"tier": "cheap"}
    with pytest.raises(mc.MetaharnessConfigError):
        mc._validate(cfg)


def test_scoring_judges_are_pinned_and_match_scorer_defaults():
    from retort.scoring.scorers import atdd_review, mcp_client_facts
    snap = mc.snapshot()
    for r in ("judge_idiomatic", "judge_atdd", "judge_mcp_facts"):
        assert snap[r]["pinned"]
    assert snap["judge_atdd"]["model"] == atdd_review.DEFAULT_REVIEW_MODEL
    assert snap["judge_mcp_facts"]["model"] == mcp_client_facts.DEFAULT_JUDGE_MODEL


def test_escalation_ladder_is_gated_by_confidence_and_ceiling():
    cfg = mc.load()
    assert mc.ladder("diagnose", cfg) == ["cheap", "mid", "top"]
    assert mc.next_tier("diagnose", "cheap", confidence=0.95, cfg=cfg) is None   # convincing: stop
    assert mc.next_tier("diagnose", "cheap", confidence=0.4, cfg=cfg) == "mid"
    assert mc.next_tier("diagnose", "mid", valid=False, cfg=cfg) == "top"
    assert mc.next_tier("diagnose", "top", confidence=0.0, cfg=cfg) is None      # top of ladder
    assert mc.ladder("evaluator", cfg) == []                                     # pinned never escalates


def test_ceiling_caps_escalation_and_bad_ladders_rejected():
    cfg = mc.load()
    cfg["routed"]["roles"]["diagnose"]["ceiling"] = "mid"
    assert mc.next_tier("diagnose", "mid", confidence=0.0, cfg=cfg) is None
    cfg["escalation"]["ladder"] = ["top", "cheap", "mid"]
    with pytest.raises(mc.MetaharnessConfigError):
        mc._validate(cfg)
