"""Shared fixtures: the real Kaggle data set and small hand-built matches."""

from datetime import date
from pathlib import Path

import pytest

from brazsoccer_mcp.models import Match
from brazsoccer_mcp.store import SoccerData

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "kaggle"


@pytest.fixture(scope="session")
def data() -> SoccerData:
    """The full de-duplicated data set loaded from data/kaggle."""
    return SoccerData.load(DATA_DIR)


def make_match(
    when: str,
    home: str,
    away: str,
    hg: int,
    ag: int,
    competition: str = "Brasileirão Série A",
    season: int | None = None,
    source: str = "test",
) -> Match:
    """Build a Match from display names; keys are the lowercased names."""
    when_date = date.fromisoformat(when)
    return Match(
        date=when_date,
        competition=competition,
        home=home,
        away=away,
        home_key=home.casefold(),
        away_key=away.casefold(),
        home_goals=hg,
        away_goals=ag,
        season=season or when_date.year,
        source=source,
    )
