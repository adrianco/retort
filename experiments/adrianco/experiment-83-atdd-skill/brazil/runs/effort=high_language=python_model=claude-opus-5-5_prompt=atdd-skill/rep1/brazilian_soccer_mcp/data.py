"""Loading the Kaggle datasets into one consistent set of matches and players.

Matches appear in up to three files (the Brasileirão files overlap with the extended
statistics file), so a match recorded in several datasets is merged into one record that
remembers every source and keeps the extra statistics.
"""
import csv
import datetime
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from brazilian_soccer_mcp.names import DISPLAY, HOME_STATE, LEAGUES, display_name, simplify, team_key

MERGE_WINDOW_DAYS = 30
CUP_WINDOW_DAYS = 7
DUPLICATE_WINDOW_DAYS = 3
LOOSE_WORDS = {"ec", "fc", "sc", "ce", "ca", "ge", "ad", "ae", "af", "ac", "cr", "fr", "clube", "club", "esporte",
               "futebol", "esportivo", "sport"}
COMMON_WORDS = {"sao", "real", "atletico", "uniao", "santa", "esporte", "clube", "futebol", "club", "sport"}


@dataclass
class Match:
    date: str
    competition: str
    season: int
    home_key: str
    away_key: str
    home_goals: int
    away_goals: int
    round: int = None
    stage: str = None
    arena: str = None
    statistics: dict = None
    sources: list = field(default_factory=list)


@dataclass
class Player:
    name: str
    age: int
    nationality: str
    club: str
    club_key: str
    position: str
    overall: int
    potential: int
    jersey_number: int
    height: str
    weight: str
    preferred_foot: str
    value: str
    wage: str
    skills: dict


@dataclass
class Dataset:
    file: str
    description: str
    records: int = 0
    skipped: int = 0


SKILLS = ["Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling", "Curve",
          "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility", "Reactions",
          "Balance", "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression", "Interceptions",
          "Positioning", "Vision", "Penalties", "Composure", "Marking", "StandingTackle", "SlidingTackle",
          "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes"]

EXTENDED_TOURNAMENTS = {"Serie A": "Brasileirão", "Serie B": "Série B", "Serie C": "Série C",
                        "Copa do Brasil": "Copa do Brasil"}


def parse_date(text):
    """ISO date from '2023-09-24', '2012-05-19 18:30:00' or '29/03/2003'; None when unknown."""
    text = (text or "").strip()
    found = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if found:
        return f"{found[1]}-{found[2]}-{found[3]}"
    found = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if found:
        return f"{found[3]}-{int(found[2]):02d}-{int(found[1]):02d}"
    return None


def parse_int(text):
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _known(key):
    return key in DISPLAY or key in HOME_STATE


def _loose(key):
    """A forgiving identity for minor clubs: 'CE Aimore' and 'Aimoré - RS' both become 'aimore'."""
    if _known(key):
        return key
    base = key.rsplit("-", 1)[0] if "-" in key[-3:] else key
    words = [word for word in base.split() if word not in LOOSE_WORDS]
    return " ".join(words) or base


def _state_of(key):
    if re.search(r"-[a-z]{2}$", key):
        return key[-2:].upper()
    return HOME_STATE.get(key)


def _significant_words(key):
    return {word for word in _loose(key).replace("-", " ").split()
            if len(word) >= 4 and word not in COMMON_WORDS}


def _could_be_same_club(key, other_key, *, by_name_only=False):
    if key == other_key:
        return True
    states = {_state_of(key), _state_of(other_key)} - {None}
    if len(states) > 1:
        return False
    if by_name_only:
        return bool(_significant_words(key) & _significant_words(other_key))
    return True


def _same_score(first, second):
    return (first.home_goals, first.away_goals) == (second.home_goals, second.away_goals)


def _days_apart(first, second):
    if not first or not second:
        return 0
    return abs((datetime.date.fromisoformat(first) - datetime.date.fromisoformat(second)).days)


class SoccerData:
    def __init__(self):
        self.matches = []
        self.players = []
        self.datasets = []
        self._names = {}
        self._by_fixture = defaultdict(list)
        self._by_day = defaultdict(list)
        self._same_club = {}

    # -- names -------------------------------------------------------------------------------

    def register_team(self, raw):
        key = team_key(raw)
        candidate = display_name(raw)
        current = self._names.get(key)
        if current is None or (current.isascii() and not candidate.isascii()
                               and simplify(current) == simplify(candidate)):
            self._names[key] = candidate
        return key

    def canonical(self, key):
        """Follows the spellings found to mean the same club when two datasets record the same match."""
        while key in self._same_club:
            key = self._same_club[key]
        return key

    def name_of(self, key):
        return self._names.get(key, key)

    @property
    def team_keys(self):
        return self._names.keys()

    def _unite(self, key, other_key):
        key, other_key = self.canonical(key), self.canonical(other_key)
        if key == other_key:
            return
        if _known(key) and not _known(other_key):
            key, other_key = other_key, key
        self._same_club[key] = other_key

    # -- matches -----------------------------------------------------------------------------

    def add_match(self, match, *, raw_home, raw_away):
        match.home_key = self.canonical(self.register_team(raw_home))
        match.away_key = self.canonical(self.register_team(raw_away))
        existing = self._same_match(match)
        if existing:
            self._unite(match.home_key, existing.home_key)
            self._unite(match.away_key, existing.away_key)
            self._merge(existing, match)
            return
        self.matches.append(match)
        self._by_fixture[self._fixture(match)].append(match)
        if match.date:
            self._by_day[(match.competition, match.date)].append(match)

    def _fixture(self, match):
        return (match.competition, _loose(match.home_key), _loose(match.away_key))

    def _same_match(self, match):
        """The match already recorded that this record describes, if any.

        Another dataset's record of the same fixture close to the same date is the same match even
        when the score differs (the extended dataset has some wrong scores). Within one dataset only
        an identical result a few days apart is a duplicated row."""
        source = match.sources[0]
        window = MERGE_WINDOW_DAYS if match.competition in LEAGUES else CUP_WINDOW_DAYS

        def same_fixture(other):
            if source in other.sources:
                return _same_score(other, match) and _days_apart(other.date, match.date) <= DUPLICATE_WINDOW_DAYS
            if match.season is not None and other.season is not None and match.competition in LEAGUES:
                return other.season == match.season
            return _days_apart(other.date, match.date) <= window

        def same_clubs(other, *, by_name_only=False):
            return (_could_be_same_club(match.home_key, other.home_key, by_name_only=by_name_only)
                    and _could_be_same_club(match.away_key, other.away_key, by_name_only=by_name_only))

        candidates = [other for other in self._by_fixture[self._fixture(match)]
                      if same_fixture(other) and same_clubs(other)]
        if not candidates and match.date:
            candidates = [other for other in self._near_day(match)
                          if source not in other.sources and _same_score(other, match)
                          and (_loose(other.home_key) == _loose(match.home_key)
                               or _loose(other.away_key) == _loose(match.away_key))
                          and same_clubs(other, by_name_only=True)]
        return min(candidates, key=lambda other: _days_apart(other.date, match.date), default=None)

    def _near_day(self, match):
        day = datetime.date.fromisoformat(match.date)
        for offset in (-1, 0, 1):
            yield from self._by_day[(match.competition, (day + datetime.timedelta(days=offset)).isoformat())]

    @staticmethod
    def _merge(existing, match):
        for source in match.sources:
            if source not in existing.sources:
                existing.sources.append(source)
        existing.date = existing.date or match.date
        existing.round = existing.round or match.round
        existing.stage = existing.stage or match.stage
        existing.arena = existing.arena or match.arena
        existing.statistics = existing.statistics or match.statistics
        if existing.season is None:
            existing.season = match.season

    # -- loading -----------------------------------------------------------------------------

    @classmethod
    def load(cls, directory):
        data = cls()
        directory = Path(directory)
        loaders = [
            ("Brasileirao_Matches.csv", "Brasileirão Serie A matches 2012-2022", data._load_brasileirao),
            ("novo_campeonato_brasileiro.csv", "Historical Brasileirão matches 2003-2019", data._load_historical),
            ("Brazilian_Cup_Matches.csv", "Copa do Brasil matches 2012-2021", data._load_cup),
            ("Libertadores_Matches.csv", "Copa Libertadores matches 2013-2022", data._load_libertadores),
            ("BR-Football-Dataset.csv", "Brazilian matches with corners, shots and attacks 2014-2023",
             data._load_extended),
            ("fifa_data.csv", "FIFA 19 player database", data._load_players),
        ]
        for file_name, description, loader in loaders:
            dataset = Dataset(file_name, description)
            data.datasets.append(dataset)
            path = directory / file_name
            if not path.exists():
                continue
            with open(path, encoding="utf-8-sig", newline="") as source:
                for row in csv.DictReader(source):
                    if loader(row, file_name):
                        dataset.records += 1
                    else:
                        dataset.skipped += 1
        data._use_canonical_keys()
        data._name_cup_stages()
        data._assign_missing_seasons()
        data.matches.sort(key=lambda match: (match.date or "", match.competition), reverse=True)
        return data

    def _add(self, row, source, *, raw_home, raw_away, home_goals, away_goals, **details):
        home_goals, away_goals = parse_int(home_goals), parse_int(away_goals)
        if home_goals is None or away_goals is None or not raw_home.strip() or not raw_away.strip():
            return False
        self.add_match(Match(home_key="", away_key="", home_goals=home_goals, away_goals=away_goals,
                             sources=[source], **details), raw_home=raw_home, raw_away=raw_away)
        return True

    def _load_brasileirao(self, row, source):
        return self._add(row, source, raw_home=row["home_team"], raw_away=row["away_team"],
                         home_goals=row["home_goal"], away_goals=row["away_goal"],
                         date=parse_date(row["datetime"]), competition="Brasileirão",
                         season=parse_int(row["season"]), round=parse_int(row["round"]))

    def _load_historical(self, row, source):
        return self._add(row, source, raw_home=row["Equipe_mandante"], raw_away=row["Equipe_visitante"],
                         home_goals=row["Gols_mandante"], away_goals=row["Gols_visitante"],
                         date=parse_date(row["Data"]), competition="Brasileirão",
                         season=parse_int(row["Ano"]), round=parse_int(row["Rodada"]),
                         arena=row.get("Arena") or None)

    def _load_cup(self, row, source):
        return self._add(row, source, raw_home=row["home_team"], raw_away=row["away_team"],
                         home_goals=row["home_goal"], away_goals=row["away_goal"],
                         date=parse_date(row["datetime"]), competition="Copa do Brasil",
                         season=parse_int(row["season"]), round=parse_int(row["round"]))

    def _load_libertadores(self, row, source):
        return self._add(row, source, raw_home=row["home_team"], raw_away=row["away_team"],
                         home_goals=row["home_goal"], away_goals=row["away_goal"],
                         date=parse_date(row["datetime"]), competition="Copa Libertadores",
                         season=parse_int(row["season"]), stage=(row.get("stage") or "").strip().lower() or None)

    def _load_extended(self, row, source):
        competition = EXTENDED_TOURNAMENTS.get(row["tournament"].strip(), row["tournament"].strip())
        statistics = {name: parse_int(row.get(column)) for name, column in [
            ("home_corners", "home_corner"), ("away_corners", "away_corner"), ("home_shots", "home_shots"),
            ("away_shots", "away_shots"), ("home_attacks", "home_attack"), ("away_attacks", "away_attack")]}
        statistics = {name: value for name, value in statistics.items() if value is not None} or None
        return self._add(row, source, raw_home=row["home"], raw_away=row["away"],
                         home_goals=row["home_goal"], away_goals=row["away_goal"],
                         date=parse_date(row["date"]), competition=competition, season=None,
                         statistics=statistics)

    def _load_players(self, row, source):
        name = (row.get("Name") or "").strip()
        if not name:
            return False
        club = (row.get("Club") or "").strip()
        self.players.append(Player(
            name=name, age=parse_int(row.get("Age")), nationality=(row.get("Nationality") or "").strip(),
            club=club, club_key=team_key(club) if club else "", position=(row.get("Position") or "").strip(),
            overall=parse_int(row.get("Overall")) or 0, potential=parse_int(row.get("Potential")) or 0,
            jersey_number=parse_int(row.get("Jersey Number")), height=row.get("Height") or "",
            weight=row.get("Weight") or "", preferred_foot=row.get("Preferred Foot") or "",
            value=row.get("Value") or "", wage=row.get("Wage") or "",
            skills={skill: parse_int(row.get(skill)) for skill in SKILLS if parse_int(row.get(skill)) is not None}))
        return True

    # -- derived details ---------------------------------------------------------------------

    def _use_canonical_keys(self):
        for match in self.matches:
            match.home_key, match.away_key = self.canonical(match.home_key), self.canonical(match.away_key)
        for player in self.players:
            player.club_key = self.canonical(player.club_key)

    def _name_cup_stages(self):
        """Copa do Brasil rounds are numbered; the last round of a season, when it is a single tie, is the final."""
        cup = defaultdict(list)
        for match in self.matches:
            if match.competition == "Copa do Brasil" and match.round is not None and match.stage is None:
                cup[match.season].append(match)
        for season_matches in cup.values():
            by_round = defaultdict(list)
            for match in season_matches:
                by_round[match.round].append(match)
            last = max(by_round)
            names = {}
            if len(by_round[last]) <= 2:
                names = {last: "final", last - 1: "semifinals", last - 2: "quarterfinals"}
            for number, round_matches in by_round.items():
                for match in round_matches:
                    match.stage = names.get(number, f"round {number}")

    def _assign_missing_seasons(self):
        """Leagues once ran into the following January/February (the 2020 season finished in 2021)."""
        for match in self.matches:
            if match.season is None and match.date:
                year, month = int(match.date[:4]), int(match.date[5:7])
                match.season = year - 1 if match.competition in LEAGUES and month <= 2 else year
