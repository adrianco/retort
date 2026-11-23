"""In-memory relationships between teams, fixtures, competitions and FIFA players."""
import csv
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

LEAGUE = "Brasileirão Série A"
CUP = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"
HISTORICAL = "novo_campeonato_brasileiro.csv"
SERIE_A = "Brasileirao_Matches.csv"
CUP_FILE = "Brazilian_Cup_Matches.csv"
LIB_FILE = "Libertadores_Matches.csv"
EXTENDED = "BR-Football-Dataset.csv"
FIFA = "fifa_data.csv"
DATA = Path(__file__).resolve().parent / "data" / "kaggle"


def normalized(value):
    plain = unicodedata.normalize("NFKD", value.casefold())
    plain = "".join(char for char in plain if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", plain))


TEAM_ALIASES = {
    "Atlético Mineiro": ["Atlético MG", "Clube Atlético Mineiro"],
    "Atlético Goianiense": ["Atlético GO", "Atlético Clube Goianiense"],
    "Athletico Paranaense": ["Atlético PR", "Athletico PR", "Athletico",
                            "Atlético Paranaense", "Club Athletico Paranaense"],
    "América-MG": ["América FC Minas Gerais", "América Mineiro"],
    "Botafogo-RJ": ["Botafogo", "Botafogo de Futebol e Regatas"],
    "Vasco da Gama": ["Vasco", "Vasco da Gama RJ", "Club de Regatas Vasco da Gama"],
    "Flamengo": ["Clube de Regatas do Flamengo", "CR Flamengo"],
    "Fluminense": ["Fluminense FC", "Fluminense Football Club"],
    "Corinthians": ["Sport Club Corinthians Paulista", "SC Corinthians Paulista"],
    "Palmeiras": ["Sociedade Esportiva Palmeiras", "SE Palmeiras"],
    "São Paulo": ["São Paulo FC", "São Paulo Futebol Clube"],
    "Santos": ["Santos FC", "Santos Futebol Clube"],
    "Cruzeiro": ["Cruzeiro Esporte Clube"],
    "Internacional": ["Sport Club Internacional", "SC Internacional"],
    "Grêmio": ["Grêmio FBPA", "Grêmio Foot-Ball Porto Alegrense"],
    "Bahia": ["EC Bahia", "Esporte Clube Bahia"],
    "Sport": ["Sport Recife", "Sport Club do Recife"],
    "Fortaleza": ["Fortaleza FC", "Fortaleza EC", "Fortaleza Esporte Clube"],
    "Ceará": ["Ceará Sporting Club"],
    "Náutico": ["Náutico Capibaribe", "Clube Náutico Capibaribe"],
    "Juventude": ["EC Juventude"],
    "Red Bull Bragantino": ["Bragantino", "RB Bragantino"],
    "Santa Cruz": ["Santa Cruz FC"],
    "Remo": ["Clube do Remo"],
    "Operário-PR": ["Operário Ferroviário", "Operario Ferroviario Esporte Clube"],
    "ABC": ["A.b.c."],
}
ALIASES = {normalized(alias): name for name, aliases in TEAM_ALIASES.items()
           for alias in [name, *aliases]}
STATES = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO"
STATE_SUFFIX = re.compile(r"\s*-\s*(" + STATES.replace(" ", "|") + r")$", re.I)
# Keep state qualifiers for names shared by multiple clubs.
AMBIGUOUS = {
    "america", "atletico", "athletico", "botafogo", "nacional", "operario", "rio branco",
    "sao jose", "sao raimundo", "ypiranga", "vitoria", "santa cruz", "ferroviario",
    "portuguesa",
}
DEFAULT_STATES = {"vitoria": "BA", "santa cruz": "PE", "ferroviario": "CE", "portuguesa": "SP"}


def team_name(value, state=""):
    value = value.strip()
    key = normalized(value)
    if key in ALIASES:
        return ALIASES[key]
    suffix = STATE_SUFFIX.search(value)
    if suffix:
        state = suffix[1].upper()
        value = value[:suffix.start()]
    else:
        base, _, last = key.rpartition(" ")
        if base in AMBIGUOUS and last.upper() in STATES.split():
            state = last.upper()
            value = value.rsplit(None, 1)[0]
    base_key = normalized(value)
    if base_key in AMBIGUOUS and state and state != DEFAULT_STATES.get(base_key):
        value = f"{value}-{state}"
    return ALIASES.get(normalized(value), value)


def team_key(value):
    return normalized(team_name(value))


def competition_name(value):
    key = normalized(value)
    for name, aliases in {
        LEAGUE: ("brasileirao", "serie a", "campeonato brasileiro", "brasileirao serie a"),
        CUP: ("copa do brasil", "brazilian cup"),
        LIBERTADORES: ("libertadores", "copa libertadores", "copa libertadores da america"),
        "Brasileirão Série B": ("serie b", "brasileirao serie b"),
        "Brasileirão Série C": ("serie c", "brasileirao serie c"),
    }.items():
        if key in aliases:
            return name
    raise ValueError(f"Unknown competition: {value}")


def parse_date(value):
    if "/" in value:
        return datetime.strptime(value.split()[0], "%d/%m/%Y").date()
    return date.fromisoformat(value[:10])


def number(value):
    return None if value in ("", "-", "NA") else int(float(value))


def page(items, limit, offset, key):
    if not 1 <= limit <= 500 or offset < 0:
        raise ValueError("Use a limit of 1–500 and a nonnegative offset.")
    end = offset + limit
    return {"total": len(items), "offset": offset,
            "next_offset": end if end < len(items) else None, key: items[offset:end]}


DERBIES = {
    frozenset(team_key(team) for team in pair)
    for pair in [
        ("Flamengo", "Fluminense"), ("Flamengo", "Vasco"), ("Flamengo", "Botafogo"),
        ("Fluminense", "Vasco"), ("Fluminense", "Botafogo"), ("Vasco", "Botafogo"),
        ("Grêmio", "Internacional"), ("Cruzeiro", "Atlético-MG"),
        ("Athletico-PR", "Coritiba"), ("Bahia", "Vitória"), ("Ceará", "Fortaleza"),
        ("Remo", "Paysandu"), ("Sport", "Náutico"), ("Sport", "Santa Cruz"),
        ("Náutico", "Santa Cruz"),
        *((a, b) for index, a in enumerate(("Corinthians", "Palmeiras", "São Paulo", "Santos"))
          for b in ("Corinthians", "Palmeiras", "São Paulo", "Santos")[index + 1:]),
    ]
}
POSITIONS = {
    "forward": "ST CF LF RF LW RW LS RS",
    "midfielder": "CM CAM CDM LM RM LCM RCM LAM RAM LDM RDM",
    "defender": "CB LB RB LCB RCB LWB RWB",
    "goalkeeper": "GK",
}


def fixture(row, source):
    details = {}
    state_home = state_away = ""
    stage = None
    if source == HISTORICAL:
        competition = LEAGUE
        day, season, stage = row["Data"], row["Ano"], row["Rodada"]
        home, away = row["Equipe_mandante"], row["Equipe_visitante"]
        state_home, state_away = row["Mandante_UF"], row["Visitante_UF"]
        # The historical CSV assigns Vitória the wrong UF in some seasons.
        if normalized(home) == "vitoria":
            state_home = "BA"
        if normalized(away) == "vitoria":
            state_away = "BA"
        goals = row["Gols_mandante"], row["Gols_visitante"]
        details = {"stadium": row["Arena"], "source_id": row["ID"]}
        kickoff = None
    elif source == EXTENDED:
        competition = competition_name(row["tournament"])
        day, kickoff = row["date"], row["time"]
        season = day[:4]
        home, away = row["home"], row["away"]
        goals = row["home_goal"], row["away_goal"]
        details = {"extended_statistics": {
            field: number(row[field]) for field in
            ("home_corner", "away_corner", "home_attack", "away_attack",
             "home_shots", "away_shots", "total_corners")
        } | {field: row[field] for field in ("ht_result", "at_result", "ht_diff", "at_diff")}}
    else:
        competition = {SERIE_A: LEAGUE, CUP_FILE: CUP, LIB_FILE: LIBERTADORES}[source]
        day, _, kickoff = row["datetime"].partition(" ")
        season = row["season"]
        home, away = row["home_team"], row["away_team"]
        state_home, state_away = row.get("home_team_state", ""), row.get("away_team_state", "")
        goals = row["home_goal"], row["away_goal"]
        stage = row.get("round") or row.get("stage")
    return {
        "date": parse_date(day).isoformat() if day != "NA" else None,
        "kickoff": kickoff or None, "season": number(season), "competition": competition,
        "home_team": team_name(home, state_home), "away_team": team_name(away, state_away),
        "home_goal": number(goals[0]), "away_goal": number(goals[1]),
        "round": int(stage) if stage and stage.isdigit() else None,
        "stage": stage if stage and not stage.isdigit() else None,
        "sources": [source], **details,
    }


def ordered_pair(match):
    return match["competition"], normalized(match["home_team"]), normalized(match["away_team"])


def combine_matches(sources):
    fixtures = []
    by_pair = defaultdict(list)
    by_league_season = {}
    for source, matches in sources.items():
        for match in matches:
            pair = ordered_pair(match)
            # The extended export labels this non-Série A fixture as Série A.
            if source == EXTENDED and pair == (LEAGUE, "brasilia fc", "ca taguatinga"):
                continue
            season_key = (pair, match["season"])
            existing = None
            if match["competition"] == LEAGUE and source != EXTENDED:
                existing = by_league_season.get((season_key, match["round"]))
                if existing and source in existing["sources"]:
                    existing = None
            if existing is None and match["date"]:
                day = parse_date(match["date"])
                candidates = [
                    (abs((day - parse_date(other["date"])).days), index, other)
                    for index, other in enumerate(by_pair[pair])
                    if other["date"] and (
                        source not in other["sources"] or (
                            source == EXTENDED
                            and (match["home_goal"], match["away_goal"])
                            == (other["home_goal"], other["away_goal"])
                            and (match["competition"] == LEAGUE or match["date"] == other["date"])
                        )
                    )
                ]
                if candidates:
                    distance, _, closest = min(candidates)
                    if distance <= 1:
                        existing = closest
            if existing is None:
                existing = dict(match, sources=[source])
                fixtures.append(existing)
                by_pair[pair].append(existing)
                if match["competition"] == LEAGUE:
                    by_league_season[season_key, match["round"]] = existing
            else:
                if source not in existing["sources"]:
                    existing["sources"].append(source)
                for name, value in match.items():
                    if existing.get(name) is None:
                        existing[name] = value
    return fixtures


def record(matches, key):
    totals = Counter(matches=0, wins=0, draws=0, losses=0, goals_for=0, goals_against=0)
    for match in matches:
        home = normalized(match["home_team"]) == key
        scored, conceded = match["home_goal"], match["away_goal"]
        if scored is None or conceded is None:
            continue
        if not home:
            scored, conceded = conceded, scored
        totals["matches"] += 1
        totals["goals_for"] += scored
        totals["goals_against"] += conceded
        totals["wins" if scored > conceded else "losses" if scored < conceded else "draws"] += 1
    played = totals["matches"]
    return dict(totals, win_rate=round(100 * totals["wins"] / played, 2) if played else None)


class Soccer:
    def __init__(self, directory=DATA):
        self.sources = {}
        names = {}
        # Prefer season-specific fixtures and historical stadiums to calendar-year inference.
        for source in (SERIE_A, HISTORICAL, CUP_FILE, LIB_FILE, EXTENDED):
            with (directory / source).open(encoding="utf-8-sig", newline="") as stream:
                matches = [fixture(row, source) for row in csv.DictReader(stream)]
            self.sources[source] = matches
            for match in matches:
                for field in ("home_team", "away_team"):
                    key = normalized(match[field])
                    previous = names.get(key, "")
                    if not previous or sum(not c.isascii() for c in match[field]) > sum(
                        not c.isascii() for c in previous
                    ):
                        names[key] = match[field]
        self.names = names
        for matches in self.sources.values():
            for match in matches:
                for field in ("home_team", "away_team"):
                    match[field] = names[normalized(match[field])]
        cup_final_rounds = {2012: 6, 2013: 8, 2014: 8, 2015: 8, 2016: 7,
                            2017: 8, 2018: 8, 2019: 8, 2020: 8}
        for match in self.sources[CUP_FILE]:
            if match["round"] == cup_final_rounds.get(match["season"]):
                match["stage"] = "final"
        # The cup file stops before the 2021 finals. In the extended export,
        # the last two cup fixtures of each of these years are the two final legs.
        for season in (2021, 2022, 2023):
            cup_matches = sorted(
                (match for match in self.sources[EXTENDED]
                 if match["competition"] == CUP and match["season"] == season),
                key=lambda match: match["date"], reverse=True,
            )
            if len(cup_matches) >= 2:
                first, second = cup_matches[:2]
                if ordered_pair(first)[1:] == ordered_pair(second)[1:][::-1]:
                    first["stage"] = second["stage"] = "final"
        self.matches = sorted(combine_matches(self.sources), key=lambda m: m["date"] or "",
                              reverse=True)
        for matches in self.sources.values():
            matches.sort(key=lambda m: m["date"] or "", reverse=True)
        with (directory / FIFA).open(encoding="utf-8-sig", newline="") as stream:
            self.players = []
            for row in csv.DictReader(stream):
                player = {key: value or None for key, value in row.items() if key}
                for key in ("ID", "Age", "Overall", "Potential", "Jersey Number"):
                    player[key] = number(row[key])
                self.players.append(player)
        self.players.sort(key=lambda player: (-player["Overall"], player["Name"], player["ID"]))
        self.player_keys = [
            (normalized(p["Name"]), normalized(p["Nationality"]), team_key(p["Club"] or ""), p)
            for p in self.players
        ]

    def coverage(self):
        """Report source row counts and merged fixture coverage."""
        return {"sources": {name: len(rows) for name, rows in self.sources.items()}
                | {FIFA: len(self.players)}, "merged_fixtures": len(self.matches)}

    def _matches(self, team=None, opponent=None, venue="either", competition=None, season=None,
                 start_date=None, end_date=None, stage=None, round_number=None, derbies=False,
                 source=None):
        if venue not in {"home", "away", "either"}:
            raise ValueError("venue must be home, away or either.")
        if not team and (opponent or venue != "either"):
            raise ValueError("Specify a team when filtering by opponent or home/away venue.")
        if source is not None and source not in self.sources:
            raise ValueError(f"Unknown match source: {source}")
        team, opponent = (team_key(value) if value else None for value in (team, opponent))
        competition = competition_name(competition) if competition else None
        start = parse_date(start_date).isoformat() if start_date else None
        end = parse_date(end_date).isoformat() if end_date else None
        if start and end and start > end:
            raise ValueError("start_date must be on or before end_date.")
        stage = normalized(stage).rstrip("s") if stage else None
        results = []
        for match in self.matches if source is None else self.sources[source]:
            if competition and match["competition"] != competition:
                continue
            if season is not None and match["season"] != season:
                continue
            day = match["date"]
            if (start and (not day or day < start)) or (end and (not day or day > end)):
                continue
            if stage and normalized(match["stage"] or "").rstrip("s") != stage:
                continue
            if round_number is not None and match["round"] != round_number:
                continue
            if team or derbies:
                _, home, away = ordered_pair(match)
                if team:
                    if not ((venue != "away" and home == team and (not opponent or away == opponent))
                            or (venue != "home" and away == team and (not opponent or home == opponent))):
                        continue
                if derbies and frozenset((home, away)) not in DERBIES:
                    continue
            results.append(match)
        return results

    def search_matches(self, team: str | None = None, opponent: str | None = None,
                       venue: str = "either", competition: str | None = None,
                       season: int | None = None, start_date: str | None = None,
                       end_date: str | None = None, stage: str | None = None,
                       round_number: int | None = None, derbies: bool = False,
                       source: str | None = None, limit: int = 25, offset: int = 0):
        """Find fixtures and scores, latest first. Dates are inclusive (ISO or DD/MM/YYYY).
        Use opponent for both orientations of a matchup, stage for finals, derbies for known
        Brazilian rivalries, or a CSV filename as source for original source rows.
        """
        matches = self._matches(team, opponent, venue, competition, season, start_date, end_date,
                                stage, round_number, derbies, source)
        return page(matches, limit, offset, "matches")

    def team_stats(self, team: str, season: int | None = None, competition: str | None = None,
                   venue: str = "either"):
        """Return a team's played matches, wins, losses, draws, goals and win percentage,
        with competition, season and home/away breakdowns.
        """
        matches = self._matches(team=team, season=season, competition=competition, venue=venue)
        key = team_key(team)
        if not key:
            raise ValueError("Supply a team name.")
        groups = {field: defaultdict(list) for field in ("competition", "season", "venue")}
        for match in matches:
            groups["competition"][match["competition"]].append(match)
            if match["season"] is not None:
                groups["season"][match["season"]].append(match)
            site = "home" if normalized(match["home_team"]) == key else "away"
            groups["venue"][site].append(match)
        return {"team": self.names.get(key, team), **record(matches, key),
                "fixtures": len(matches),
                **{f"by_{field}": {str(label): record(group, key)
                                   for label, group in sorted(buckets.items())}
                   for field, buckets in groups.items()}}

    def head_to_head(self, team: str, opponent: str, season: int | None = None,
                     competition: str | None = None, limit: int = 15, offset: int = 0):
        """Compare teams in both orientations, with their records and recent meetings."""
        key, other = team_key(team), team_key(opponent)
        if not key or not other or key == other:
            raise ValueError("Supply two distinct teams.")
        matches = self._matches(team=team, opponent=opponent, season=season, competition=competition)
        return {"records": {self.names.get(k, name): record(matches, k)
                            for k, name in ((key, team), (other, opponent))},
                **page(matches, limit, offset, "matches")}

    def search_players(self, name: str | None = None, nationality: str | None = None,
                       club: str | None = None, position: str | None = None,
                       limit: int = 25, offset: int = 0):
        """Search the FIFA snapshot by name, nationality, club or position, highest Overall first.
        Use a FIFA position code or a group such as forward, midfielder, defender or goalkeeper.
        """
        name = normalized(name or "")
        country = normalized(nationality or "")
        country = "brazil" if country in {"brasil", "brazilian", "brasileiro"} else country
        club = team_key(club) if club else ""
        position = (position or "").strip().lower()
        allowed = POSITIONS.get(position.removesuffix("s"), position.upper()).split()
        players = [p for n, nat, c, p in self.player_keys
                   if all(any(word.startswith(part) for word in n.split()) for part in name.split())
                   and (not country or nat == country)
                   and (not club or club == c)
                   and (not allowed or p["Position"] in allowed)]
        return page(players, limit, offset, "players")

    def team_rankings(self, competition: str | None = None, season: int | None = None,
                      venue: str = "either", sort_by: str = "points", min_matches: int = 1,
                      limit: int = 25, offset: int = 0):
        """Rank teams by points, goals_for, wins or win_rate. Set venue to home or away.
        Use min_matches to exclude clubs with too few played fixtures.
        """
        if venue not in {"home", "away", "either"}:
            raise ValueError("venue must be home, away or either.")
        if sort_by not in {"points", "goals_for", "wins", "win_rate"} or min_matches < 1:
            raise ValueError("Supply a supported sort_by value and a positive min_matches.")
        groups = defaultdict(list)
        for match in self._matches(competition=competition, season=season):
            _, home, away = ordered_pair(match)
            if venue != "away":
                groups[home].append(match)
            if venue != "home":
                groups[away].append(match)
        rows = []
        for key, matches in groups.items():
            totals = record(matches, key)
            if totals["matches"] >= min_matches:
                rows.append({"team": self.names[key], **totals,
                             "points": totals["wins"] * 3 + totals["draws"],
                             "goal_difference": totals["goals_for"] - totals["goals_against"]})
        rows.sort(key=lambda row: (-row[sort_by], -row["wins"], -row["goal_difference"],
                                   -row["goals_for"], normalized(row["team"])))
        for rank, row in enumerate(rows, 1):
            row["rank"] = rank
        return page(rows, limit, offset, "teams")

    def standings(self, season: int, competition: str = LEAGUE):
        """Calculate league standings from scores. Use tournament_bracket for knockout cups."""
        name = competition_name(competition)
        if name in {CUP, LIBERTADORES}:
            raise ValueError("Use tournament_bracket for knockout competitions.")
        table = self.team_rankings(name, season, limit=500)
        games = sum(row["matches"] for row in table["teams"]) // 2
        clubs = table["total"]
        pairings = {ordered_pair(match) for match in self._matches(competition=name, season=season)
                    if match["home_goal"] is not None and match["away_goal"] is not None}
        complete = bool(clubs) and games == len(pairings) == clubs * (clubs - 1)
        return {"competition": name, "season": season, "played_fixtures": games,
                "double_round_robin_complete": complete if name == LEAGUE else None,
                "relegation_places": [row["team"] for row in table["teams"][-4:]]
                if name == LEAGUE and season >= 2007 and clubs == 20 and complete else None,
                "basis": "Match results only. Administrative adjustments and official tie-breaks may differ.",
                **table}

    def tournament_bracket(self, season: int, competition: str = LIBERTADORES):
        """Return knockout fixtures grouped by stage or round. Scores are as supplied,
        with penalties and advancement omitted when the inputs do not identify them.
        """
        name = competition_name(competition)
        if name not in {LIBERTADORES, CUP}:
            raise ValueError("Choose Copa Libertadores or Copa do Brasil.")
        matches = self._matches(competition=name, season=season)
        rounds = defaultdict(list)
        unclassified = []
        for match in reversed(matches):
            stage = match["stage"]
            if stage == "group stage":
                continue
            if stage or match["round"] is not None:
                rounds[stage or f"round {match['round']}"].append(match)
            else:
                unclassified.append(match)
        return {"competition": name, "season": season, "rounds": dict(rounds),
                "unclassified": unclassified}

    def match_statistics(self, competition: str | None = None, season: int | None = None,
                         team: str | None = None, venue: str = "either",
                         biggest_wins_limit: int = 10):
        """Calculate average goals, outcome rates and biggest wins, overall and by season."""
        if not 0 <= biggest_wins_limit <= 100:
            raise ValueError("biggest_wins_limit must be between 0 and 100.")
        matches = self._matches(team=team, venue=venue, competition=competition, season=season)
        groups = defaultdict(Counter)
        totals = Counter()
        wins = []
        for match in matches:
            home, away = match["home_goal"], match["away_goal"]
            if home is None or away is None:
                continue
            outcome = "home_wins" if home > away else "away_wins" if home < away else "draws"
            counts = Counter(played=1, goals=home + away, **{outcome: 1})
            totals.update(counts)
            if match["season"] is not None:
                groups[match["season"]].update(counts)
            if home != away:
                wins.append(dict(match, margin=abs(home - away)))

        def summary(counts):
            played = counts["played"]
            return {"matches": played, "goals": counts["goals"],
                    "average_goals": round(counts["goals"] / played, 3) if played else None,
                    **{f"{side}_rate": round(100 * counts[outcome] / played, 2) if played else None
                       for side, outcome in (("home_win", "home_wins"), ("away_win", "away_wins"),
                                             ("draw", "draws"))}}

        wins.sort(key=lambda match: -match["margin"])
        return {**summary(totals), "fixtures": len(matches),
                "by_season": {str(year): summary(counts) for year, counts in sorted(groups.items())},
                "biggest_wins": wins[:biggest_wins_limit]}

    def club_profile(self, club: str, season: int | None = None, player_limit: int = 25):
        """Join match records and FIFA snapshot players using the normalized club identity."""
        return {"record": self.team_stats(club, season),
                "fifa_snapshot": self.search_players(club=club, limit=player_limit)}

    def top_scorers(self, competition: str | None = None, season: int | None = None):
        """Report whether individual scorers are available for a competition and season."""
        return {"competition": competition_name(competition) if competition else None,
                "season": season, "available": False, "scorers": [],
                "reason": "The supplied fixtures record team scores and omit individual goal events."}
