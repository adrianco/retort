"""Tests for analysis.predict — predictions for unmeasured cells."""

from __future__ import annotations

import json
import pandas as pd
import pytest

from retort.analysis.anova import run_anova
from retort.analysis.predict import (
    predict_unmeasured,
    predictions_to_json,
    render_predictions,
)


@pytest.fixture
def fractional_data():
    """A 2x2x2 design with one cell missing — predictable target for tests."""
    rows = [
        # All 8 combinations except (rust, opus, beads)
        ("python", "opus", "none", 100),
        ("python", "opus", "beads", 110),
        ("python", "sonnet", "none", 200),
        ("python", "sonnet", "beads", 220),
        ("rust", "opus", "none", 50),
        # ("rust", "opus", "beads", ...) MISSING
        ("rust", "sonnet", "none", 100),
        ("rust", "sonnet", "beads", 110),
    ]
    return pd.DataFrame(rows, columns=["language", "model", "tooling", "tokens"])


def test_predicts_missing_cell(fractional_data):
    result = run_anova(
        fractional_data, response="tokens",
        factors=["language", "model", "tooling"],
        transform="log",
    )
    preds = predict_unmeasured(result, fractional_data,
                               factors=["language", "model", "tooling"])

    assert len(preds) == 1
    p = preds[0]
    assert p.factors == {"language": "rust", "model": "opus", "tooling": "beads"}

    # Multiplicative model: rust/opus/none = 50, beads adds ~10% based on
    # python rows (110/100 = 1.1; 220/200 = 1.1). Predicted should be ~55.
    assert 40 < p.predicted < 70
    assert p.ci_lower < p.predicted < p.ci_upper
    # Transform was log10
    assert p.transform == "log10(y)"


def test_no_unmeasured_cells_returns_empty(fractional_data):
    # Add the missing cell — nothing to predict.
    full = pd.concat([
        fractional_data,
        pd.DataFrame([("rust", "opus", "beads", 55)],
                     columns=fractional_data.columns),
    ], ignore_index=True)
    result = run_anova(full, response="tokens", transform="log")
    preds = predict_unmeasured(result, full)
    assert preds == []


def test_render_predictions_human_readable(fractional_data):
    result = run_anova(fractional_data, response="tokens", transform="log")
    preds = predict_unmeasured(result, fractional_data)
    rendered = render_predictions(preds, transform=result.transform)
    assert "rust" in rendered
    assert "predicted" in rendered
    assert "95% CI" in rendered
    assert "log10" in rendered  # transform note


def test_predictions_to_json_round_trip(fractional_data):
    result = run_anova(fractional_data, response="tokens", transform="log")
    preds = predict_unmeasured(result, fractional_data)
    rendered = predictions_to_json(preds)
    parsed = json.loads(rendered)
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert parsed[0]["factors"]["language"] == "rust"
    assert "ci_lower" in parsed[0]
    assert "ci_upper" in parsed[0]


def test_back_transform_when_log(fractional_data):
    """Predictions should be back-transformed from log10(y) → y."""
    result = run_anova(fractional_data, response="tokens", transform="log")
    preds = predict_unmeasured(result, fractional_data)
    # If back-transform worked, predicted value is in the same range as
    # the actual measured tokens (50–220), not in log space (~1.7–2.3).
    assert preds[0].predicted > 10
    assert preds[0].predicted < 1000


def test_log_default_in_anova():
    """run_anova defaults to log transform (the user-requested change)."""
    df = pd.DataFrame({
        "language": ["python", "rust"] * 4,
        "model": ["opus", "sonnet"] * 4,
        "tokens": [100, 200, 110, 220, 50, 100, 55, 110],
    })
    # No explicit transform — should default to log
    result = run_anova(df, response="tokens", factors=["language", "model"])
    assert result.transform.startswith("log")


def test_log_falls_back_to_none_for_negative_data():
    df = pd.DataFrame({
        "language": ["python", "rust"] * 4,
        "score": [-1.0, 0.5, 0.7, 0.8, 0.6, 0.9, 0.4, 0.85],
    })
    result = run_anova(df, response="score", factors=["language"], transform="log")
    assert result.transform == "none"


def test_log_uses_y_plus_1_for_zeros():
    df = pd.DataFrame({
        "language": ["python"] * 4 + ["rust"] * 4,
        "tokens": [0, 100, 200, 50, 0, 50, 100, 25],
    })
    result = run_anova(df, response="tokens", factors=["language"], transform="log")
    assert result.transform == "log10(y+1)"
