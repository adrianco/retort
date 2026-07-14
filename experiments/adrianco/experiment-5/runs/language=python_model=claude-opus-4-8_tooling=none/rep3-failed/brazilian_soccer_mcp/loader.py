"""Load the Kaggle CSV datasets into normalized :class:`Match` / :class:`Player`
records.

Real column layouts (verified against the files)::

    Brasileirao_Matches.csv:  datetime, home_team, home_team_state, away_team,
                              away_team_state, home_goal, away_goal, season, round
    Brazilian_Cup_Matches.csv: round, datetime, home_team, away_team,
                              home_goal, away_goal, season
    Libertadores_Matches.csv: datetime, home_team, away_team, home_goal,
                              away_goal, season, stage
    novo_campeonato_brasileiro.csv: ID, Data(DD/MM/YYYY), Ano, Rodada,
                              Equipe_mandante, Equipe_visitante, Gols_mandante,
                              Gols_visitante, Mandante_UF, Visitante_UF,
                              Vencedor, Arena, OBS
    BR-Football-Dataset.csv:  tournament, home, home_goal, away_goal, away,
                              home_corner, away_corner, home_attack,
                              away_attack, home_shots, away_shots, time, date,
                              ht_diff, at_diff, ht_result, at_result,
                              total_corners
    fifa_data.csv:            ID, Name, Age, ..., Nationality, Overall,
                              Potential, Club, ..., Position, Jersey Number, ...
"""

from __future__ import annotations

import csv
import os
from typing import List, Optional, Tuple

from .models import Match, Player
from .normalize import (
    canonical_competition,
    normalize_team,
    parse_date,
    parse_int,
    team_key,
)

BRASILEIRAO = "Brasileirão Série A"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"


def find_data_dir(explicit: Optional[str] = None) -> str:
    """Locate the ``data/kaggle`` directory."""
    candidates = []
    if explicit:
        candidates.append(explicit)
    env = os.environ.get("BR_SOCCER_DATA")
    if env:
        candidates.append(env)
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.extend([
        os.path.join(os.getcwd(), "data", "kaggle"),
        os.path.join(here, "..", "data", "kaggle"),
        os.path.join(here, "..", "..", "data", "kaggle"),
    ])
    for c in candidates:
        if c and os.path.isdir(c):
            return os.path.abspath(c)
    raise FileNotFoundError(
        "Could not locate data/kaggle directory. Set BR_SOCCER_DATA or pass "
        "an explicit path. Tried: " + ", ".join(candidates))


def _mk_match(home_raw, away_raw, hg, ag, competition, **kw) -> Match:
    return Match(
        home=normalize_team(home_raw),
        away=normalize_team(away_raw),
        home_key=team_key(home_raw),
        away_key=team_key(away_raw),
        home_goal=parse_int(hg),
        away_goal=parse_int(ag),
        competition=competition,
        **kw,
    )


def _open(path):
    return open(path, encoding="utf-8", newline="")


def load_brasileirao(path: str) -> List[Match]:
    out = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            out.append(_mk_match(
                row["home_team"], row["away_team"],
                row["home_goal"], row["away_goal"],
                BRASILEIRAO,
                season=parse_int(row.get("season")),
                match_date=parse_date(row.get("datetime")),
                round=str(row["round"]).strip() if row.get("round") else None,
                source="Brasileirao_Matches.csv",
            ))
    return out


def load_copa_do_brasil(path: str) -> List[Match]:
    out = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            out.append(_mk_match(
                row["home_team"], row["away_team"],
                row["home_goal"], row["away_goal"],
                COPA_DO_BRASIL,
                season=parse_int(row.get("season")),
                match_date=parse_date(row.get("datetime")),
                round=str(row["round"]).strip() if row.get("round") else None,
                source="Brazilian_Cup_Matches.csv",
            ))
    return out


def load_libertadores(path: str) -> List[Match]:
    out = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            out.append(_mk_match(
                row["home_team"], row["away_team"],
                row["home_goal"], row["away_goal"],
                LIBERTADORES,
                season=parse_int(row.get("season")),
                match_date=parse_date(row.get("datetime")),
                stage=str(row["stage"]).strip() if row.get("stage") else None,
                source="Libertadores_Matches.csv",
            ))
    return out


def load_novo(path: str) -> List[Match]:
    out = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            out.append(_mk_match(
                row["Equipe_mandante"], row["Equipe_visitante"],
                row["Gols_mandante"], row["Gols_visitante"],
                BRASILEIRAO,
                season=parse_int(row.get("Ano")),
                match_date=parse_date(row.get("Data")),
                round=str(row["Rodada"]).strip() if row.get("Rodada") else None,
                venue=(row.get("Arena") or "").strip() or None,
                source="novo_campeonato_brasileiro.csv",
            ))
    return out


def load_br_football(path: str) -> List[Match]:
    """Load the extended-statistics dataset (multiple divisions + cups)."""
    out = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            tournament = (row.get("tournament") or "").strip()
            competition = canonical_competition(tournament) or tournament
            d = parse_date(row.get("date"))
            extra = {}
            for k in ("home_corner", "away_corner", "home_shots", "away_shots",
                      "home_attack", "away_attack", "total_corners"):
                v = parse_int(row.get(k))
                if v is not None:
                    extra[k] = v
            out.append(_mk_match(
                row.get("home"), row.get("away"),
                row.get("home_goal"), row.get("away_goal"),
                competition,
                match_date=d,
                season=d.year if d else None,
                source="BR-Football-Dataset.csv",
                extra=extra,
            ))
    return out


_FIFA_FIELDS = {
    "id": "ID", "name": "Name", "age": "Age", "nat": "Nationality",
    "ovr": "Overall", "pot": "Potential", "club": "Club",
    "pos": "Position", "jersey": "Jersey Number", "height": "Height",
    "weight": "Weight", "foot": "Preferred Foot", "value": "Value",
    "wage": "Wage",
}


def load_players(path: str) -> List[Player]:
    out = []
    with _open(path) as fh:
        for row in csv.DictReader(fh):
            out.append(Player(
                player_id=parse_int(row.get(_FIFA_FIELDS["id"])),
                name=(row.get(_FIFA_FIELDS["name"]) or "").strip(),
                age=parse_int(row.get(_FIFA_FIELDS["age"])),
                nationality=(row.get(_FIFA_FIELDS["nat"]) or "").strip(),
                overall=parse_int(row.get(_FIFA_FIELDS["ovr"])),
                potential=parse_int(row.get(_FIFA_FIELDS["pot"])),
                club=(row.get(_FIFA_FIELDS["club"]) or "").strip(),
                position=(row.get(_FIFA_FIELDS["pos"]) or "").strip(),
                jersey_number=parse_int(row.get(_FIFA_FIELDS["jersey"])),
                height=(row.get(_FIFA_FIELDS["height"]) or "").strip(),
                weight=(row.get(_FIFA_FIELDS["weight"]) or "").strip(),
                preferred_foot=(row.get(_FIFA_FIELDS["foot"]) or "").strip(),
                value=(row.get(_FIFA_FIELDS["value"]) or "").strip(),
                wage=(row.get(_FIFA_FIELDS["wage"]) or "").strip(),
            ))
    return out


_MATCH_LOADERS = [
    ("Brasileirao_Matches.csv", load_brasileirao),
    ("novo_campeonato_brasileiro.csv", load_novo),
    ("Brazilian_Cup_Matches.csv", load_copa_do_brasil),
    ("Libertadores_Matches.csv", load_libertadores),
    ("BR-Football-Dataset.csv", load_br_football),
]


def load_all(data_dir: Optional[str] = None) -> Tuple[List[Match], List[Player]]:
    """Load every dataset. Returns ``(matches, players)``.

    Matches are loaded in a deterministic order; richer sources are loaded
    first so that deduplication (handled by the knowledge graph) keeps them.
    """
    d = find_data_dir(data_dir)
    matches: List[Match] = []
    for filename, loader in _MATCH_LOADERS:
        path = os.path.join(d, filename)
        if os.path.exists(path):
            matches.extend(loader(path))
    players_path = os.path.join(d, "fifa_data.csv")
    players = load_players(players_path) if os.path.exists(players_path) else []
    return matches, players
