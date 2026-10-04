"""
The Brazilian football knowledge base: every dataset merged into one picture.

Loading (once, at start-up):
  1. datasets.load_all() reads the six CSV files into raw records.
  2. Every raw team/club name is registered with the TeamRegistry, so
     "Palmeiras-SP", "Palmeiras - SP" and "Sociedade Esportiva Palmeiras" share
     one key and one display name.
  3. Matches recorded by more than one dataset (e.g. a 2015 Série A match is in
     Brasileirao_Matches, novo_campeonato_brasileiro and BR-Football-Dataset)
     are merged into one Match, keeping the preferred dataset's details and
     adding any match statistics the others have.
  4. Copa do Brasil numbered rounds are named (final, semifinals, ...) per
     season, counting back from the final.

Queries return an Answer: human-readable text for the LLM, plus structured
data with the same facts. Every query works on in-memory indexes, so answers
take milliseconds.
"""
import collections
import dataclasses
import datetime

from . import competitions, datasets
from .competitions import UnknownCompetition
from .teams import TeamNotFound, TeamRegistry
from .text import parse_date, plain

RIVALRIES = [
    ("Fla-Flu", "flamengo|RJ", "fluminense|RJ"),
    ("Clássico dos Milhões", "flamengo|RJ", "vasco da gama|RJ"),
    ("Clássico da Rivalidade", "flamengo|RJ", "botafogo|RJ"),
    ("Clássico dos Gigantes", "fluminense|RJ", "vasco da gama|RJ"),
    ("Clássico Vovô", "fluminense|RJ", "botafogo|RJ"),
    ("Clássico da Amizade", "botafogo|RJ", "vasco da gama|RJ"),
    ("Derby Paulista", "corinthians|SP", "palmeiras|SP"),
    ("Choque-Rei", "palmeiras|SP", "sao paulo|SP"),
    ("Majestoso", "corinthians|SP", "sao paulo|SP"),
    ("San-São", "santos|SP", "sao paulo|SP"),
    ("Clássico Alvinegro", "santos|SP", "corinthians|SP"),
    ("Clássico da Saudade", "santos|SP", "palmeiras|SP"),
    ("Grenal", "gremio|RS", "internacional|RS"),
    ("Clássico Mineiro", "atletico|MG", "cruzeiro|MG"),
    ("Atletiba", "athletico|PR", "coritiba|PR"),
    ("Ba-Vi", "bahia|BA", "vitoria|BA"),
    ("Clássico-Rei", "ceara|CE", "fortaleza|CE"),
    ("Clássico das Multidões", "sport|PE", "santa cruz|PE"),
    ("Clássico dos Clássicos", "sport|PE", "nautico|PE"),
]
_RIVALRY_BY_PAIR = {frozenset((a, b)): name for name, a, b in RIVALRIES}

POSITION_GROUPS = {
    "forward": {"ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"},
    "midfielder": {"CM", "CAM", "CDM", "LM", "RM", "LCM", "RCM", "LAM", "RAM", "LDM", "RDM"},
    "defender": {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
    "goalkeeper": {"GK"},
}
_POSITION_WORDS = {"forwards": "forward", "attacker": "forward", "attackers": "forward", "striker": "forward",
                   "strikers": "forward", "midfielders": "midfielder", "midfield": "midfielder",
                   "defenders": "defender", "defence": "defender", "defense": "defender",
                   "goalkeepers": "goalkeeper", "keeper": "goalkeeper", "keepers": "goalkeeper"}
_NATIONALITY_WORDS = {"brazilian": "brazil", "argentinian": "argentina", "argentine": "argentina",
                      "uruguayan": "uruguay", "colombian": "colombia", "chilean": "chile", "paraguayan": "paraguay",
                      "portuguese": "portugal", "spanish": "spain", "french": "france", "german": "germany",
                      "english": "england", "italian": "italy", "dutch": "netherlands"}


class QueryError(ValueError):
    """A question the data cannot answer as asked (unknown team, bad date, ...)."""


@dataclasses.dataclass
class Answer:
    text: str
    data: dict


@dataclasses.dataclass
class Match:
    competition: str
    season: int
    date: datetime.date | None
    home: str
    away: str
    home_goals: int
    away_goals: int
    round: int | None
    stage: str | None
    arena: str | None
    statistics: dict | None
    sources: list

    def goals_for(self, team):
        return self.home_goals if team == self.home else self.away_goals

    def goals_against(self, team):
        return self.away_goals if team == self.home else self.home_goals

    def winner(self):
        if self.home_goals > self.away_goals:
            return self.home
        if self.away_goals > self.home_goals:
            return self.away
        return None


@dataclasses.dataclass
class Record:
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0

    def add(self, match, team):
        scored, conceded = match.goals_for(team), match.goals_against(team)
        self.played += 1
        self.goals_for += scored
        self.goals_against += conceded
        if scored > conceded:
            self.won += 1
        elif scored == conceded:
            self.drawn += 1
        else:
            self.lost += 1

    @property
    def points(self):
        return 3 * self.won + self.drawn

    @property
    def goal_difference(self):
        return self.goals_for - self.goals_against

    @property
    def win_rate(self):
        return round(100.0 * self.won / self.played, 1) if self.played else 0.0

    def as_dict(self):
        return {**dataclasses.asdict(self), "goal_difference": self.goal_difference, "points": self.points,
                "win_rate": self.win_rate}

    def describe(self):
        return (f"- Matches: {self.played}\n- Wins: {self.won}, Draws: {self.drawn}, Losses: {self.lost}\n"
                f"- Goals For: {self.goals_for}, Goals Against: {self.goals_against}\n"
                f"- Win rate: {self.win_rate:.1f}%")


class SoccerKnowledge:
    def __init__(self, data_dir):
        raw_matches, self._raw_players, self.datasets = datasets.load_all(data_dir)
        self.teams = TeamRegistry()
        for raw in raw_matches:
            self.teams.observe(raw.home)
            self.teams.observe(raw.away)
        for player in self._raw_players:
            if player.club:
                self.teams.observe(player.club)
        self.discarded = []
        self.matches = _merge(raw_matches, self.teams, self.discarded)
        _name_cup_stages(self.matches)
        self.matches.sort(key=lambda m: (m.date or datetime.date.min), reverse=True)
        self._by_team = collections.defaultdict(list)
        for match in self.matches:
            self._by_team[match.home].append(match)
            self._by_team[match.away].append(match)
            self.teams.count_activity(match.home)
            self.teams.count_activity(match.away)
        self.players = self._raw_players
        self._player_club = {id(p): self.teams.key_for(p.club, international=True) if p.club else None
                             for p in self.players}
        self.brazilian_clubs = {key for m in self.matches if m.competition in competitions.LEAGUES
                                for key in (m.home, m.away)}

    # --- matches --------------------------------------------------------------------------------------------------

    def find_matches(self, team=None, opponent=None, venue="any", competition=None, season=None,
                     date_from=None, date_to=None, stage=None, limit=20):
        found = self._select(team=team, opponent=opponent, venue=venue, competition=competition, season=season,
                             date_from=date_from, date_to=date_to, stage=stage)
        team_key = self._team(team) if team else None
        opponent_key = self._team(opponent) if opponent else None
        title = self._describe_selection(team_key, opponent_key, venue, competition, season, date_from, date_to,
                                         stage)
        lines = [f"{title}: {len(found)} match{'es' if len(found) != 1 else ''} in dataset"]
        lines += [f"- {self._summary(m)}" for m in found[:limit]]
        if len(found) > limit:
            lines.append(f"- ... ({len(found) - limit} more matches in dataset)")
        data = {"total": len(found), "matches": [self._match_dict(m) for m in found[:limit]], "head_to_head": None}
        if team_key and opponent_key:
            h2h = self._head_to_head(team_key, opponent_key, found)
            lines += ["", self._h2h_line(team_key, opponent_key, h2h)]
            data["head_to_head"] = h2h
        return Answer("\n".join(lines), data)

    def head_to_head(self, team, opponent, competition=None, limit=10):
        team_key, opponent_key = self._team(team), self._team(opponent)
        found = self._select(team=team, opponent=opponent, competition=competition)
        h2h = self._head_to_head(team_key, opponent_key, found)
        names = f"{self.teams.display(team_key)} vs {self.teams.display(opponent_key)}"
        rivalry = _RIVALRY_BY_PAIR.get(frozenset((team_key, opponent_key)))
        lines = [f"{names}{f' ({rivalry})' if rivalry else ''}: {len(found)} meetings in dataset"]
        lines += [f"- {self._summary(m)}" for m in found[:limit]]
        if len(found) > limit:
            lines.append(f"- ... ({len(found) - limit} more matches in dataset)")
        lines += ["", self._h2h_line(team_key, opponent_key, h2h),
                  f"Goals: {self.teams.display(team_key)} {h2h['goals_for']}, "
                  f"{self.teams.display(opponent_key)} {h2h['goals_against']}"]
        if found:
            lines.append(f"Last meeting: {self._summary(found[0])}")
        h2h["recent_matches"] = [self._match_dict(m) for m in found[:limit]]
        return Answer("\n".join(lines), h2h)

    def biggest_wins(self, competition=None, season=None, team=None, limit=10):
        found = [m for m in self._select(team=team, competition=competition, season=season) if m.winner()]
        found.sort(key=lambda m: (-abs(m.home_goals - m.away_goals), -max(m.home_goals, m.away_goals),
                                  m.date or datetime.date.min))
        scope = self._scope(competition, season)
        lines = [f"Biggest victories{scope}:"]
        lines += [f"{i}. {self._summary(m, with_round=False)}" for i, m in enumerate(found[:limit], 1)]
        return Answer("\n".join(lines), {"matches": [self._match_dict(m, with_round=False) for m in found[:limit]]})

    def find_derbies(self, season=None, competition=None, rivalry=None, limit=50):
        found = []
        for match in self._select(competition=competition, season=season):
            name = _RIVALRY_BY_PAIR.get(frozenset((match.home, match.away)))
            if name and (not rivalry or plain(rivalry) in plain(name)):
                found.append((name, match))
        scope = self._scope(competition, season)
        lines = [f"Derbies between traditional rivals{scope}: {len(found)} matches"]
        lines += [f"- {name}: {self._summary(m)}" for name, m in found[:limit]]
        if len(found) > limit:
            lines.append(f"- ... ({len(found) - limit} more derbies in dataset)")
        derbies = [{**self._match_dict(m), "rivalry": name} for name, m in found[:limit]]
        return Answer("\n".join(lines), {"total": len(found), "derbies": derbies,
                                         "rivalries": [name for name, _, _ in RIVALRIES]})

    # --- teams ----------------------------------------------------------------------------------------------------

    def team_record(self, team, season=None, competition=None, venue="all"):
        key = self._team(team)
        found = self._select(team=team, season=season, competition=competition, venue=venue)
        record = _record(found, key)
        by_competition = collections.defaultdict(Record)
        for match in found:
            by_competition[match.competition].add(match, key)
        venue_text = {"home": "home ", "away": "away "}.get(_venue(venue), "")
        lines = [f"{self.teams.display(key)} {venue_text}record{self._scope(competition, season)}:", record.describe()]
        if len(by_competition) > 1:
            lines.append("By competition:")
            lines += [f"- {name}: {r.played} matches, {r.won}W {r.drawn}D {r.lost}L, "
                      f"{r.goals_for}-{r.goals_against} goals" for name, r in sorted(by_competition.items())]
        return Answer("\n".join(lines), {
            "team": self.teams.display(key), **record.as_dict(),
            "by_competition": {name: r.as_dict() for name, r in by_competition.items()},
        })

    def team_competitions(self, team):
        key = self._team(team)
        seasons = collections.defaultdict(set)
        counts = collections.Counter()
        for match in self._by_team[key]:
            seasons[match.competition].add(match.season)
            counts[match.competition] += 1
        rows = [{"competition": c, "matches": counts[c], "seasons": sorted(seasons[c])}
                for c in competitions.ALL if c in counts]
        lines = [f"Competitions {self.teams.display(key)} has played in (provided data):"]
        lines += [f"- {r['competition']}: {r['matches']} matches, seasons {_season_span(r['seasons'])}" for r in rows]
        return Answer("\n".join(lines), {"team": self.teams.display(key), "competitions": rows})

    def club_profile(self, team):
        key = self._team(team)
        squad = sorted(self._players_at(key), key=lambda p: (-p.overall, p.name))
        record = _record(self._by_team[key], key)
        average = round(sum(p.overall for p in squad) / len(squad), 1) if squad else None
        name = self.teams.display(key)
        competitions_played = self.team_competitions(team).data["competitions"]
        lines = [f"{name} - club profile",
                 f"Brazilian league club: {'yes' if key in self.brazilian_clubs else 'no'}",
                 f"All matches in dataset:", record.describe(),
                 "Competitions: " + (", ".join(f"{c['competition']} ({c['matches']})" for c in competitions_played)
                                     or "none"),
                 f"FIFA squad: {len(squad)} players" + (f" (avg rating: {average:.1f})" if squad else "")]
        lines += [f"- {p.name} - Overall: {p.overall}, Position: {p.position}, Nationality: {p.nationality}"
                  for p in squad[:15]]
        return Answer("\n".join(lines), {
            "team": name, "brazilian_club": key in self.brazilian_clubs,
            "squad": {"size": len(squad), "average_overall": average,
                      "players": [p.as_dict(name) for p in squad[:30]]},
            "record": record.as_dict(), "competitions": competitions_played,
        })

    # --- competitions ---------------------------------------------------------------------------------------------

    def league_table(self, season, competition=competitions.SERIE_A):
        competition = self._competition(competition)
        if competition in competitions.CUPS:
            raise QueryError(f"{competition} is a knockout cup; ask for its knockout bracket instead of a table.")
        standings = self._standings(competition, season)
        if not standings:
            raise QueryError(f"No {competition} matches for {season} in the dataset.")
        champion = standings[0]["team"]
        relegated = []
        if competition == competitions.SERIE_A and len(standings) >= 8:
            relegated = [row["team"] for row in standings[-(2 if season == 2003 else 4):]]
        lines = [f"{season} {competition} Final Standings (calculated from matches):"]
        for row in standings:
            note = " - Champion" if row["team"] == champion else " - Relegated" if row["team"] in relegated else ""
            lines.append(f"{row['position']}. {row['team']} - {row['points']} pts ({row['won']}W, {row['drawn']}D, "
                         f"{row['lost']}L, GD {row['goal_difference']:+d}){note}")
        return Answer("\n".join(lines), {"competition": competition, "season": season, "standings": standings,
                                         "champion": champion, "relegated": relegated})

    def top_scoring_teams(self, season=None, competition=competitions.SERIE_A, limit=10):
        competition = self._competition(competition) if competition else None
        totals = collections.defaultdict(Record)
        for match in self._select(competition=competition, season=season):
            totals[match.home].add(match, match.home)
            totals[match.away].add(match, match.away)
        ranked = sorted(totals.items(), key=lambda kv: (-kv[1].goals_for, kv[1].played, self.teams.display(kv[0])))
        rows = [{"team": self.teams.display(k), "goals": r.goals_for, "matches": r.played,
                 "goals_per_match": round(r.goals_for / r.played, 2)} for k, r in ranked[:limit]]
        lines = [f"Top-scoring teams{self._scope(competition, season)}:"]
        lines += [f"{i}. {r['team']} - {r['goals']} goals in {r['matches']} matches ({r['goals_per_match']:.2f}/match)"
                  for i, r in enumerate(rows, 1)]
        return Answer("\n".join(lines), {"competition": competition, "season": season, "teams": rows})

    def knockout_bracket(self, competition, season):
        competition = self._competition(competition)
        stages = []
        for stage in competitions.KNOCKOUT_STAGES:
            ties = collections.OrderedDict()
            for match in sorted(self._select(competition=competition, season=season, stage=stage),
                                key=lambda m: m.date or datetime.date.min):
                ties.setdefault(frozenset((match.home, match.away)), []).append(match)
            if ties:
                stages.append({"stage": stage, "ties": [self._tie(legs) for legs in ties.values()]})
        if not stages:
            raise QueryError(f"No knockout matches for {competition} {season} in the dataset.")
        lines = [f"{season} {competition} knockout bracket:"]
        for stage in stages:
            lines.append(f"{stage['stage'].title()}:")
            for tie in stage["ties"]:
                legs = "; ".join(leg["summary"] for leg in tie["matches"])
                winner = f" - {tie['winner']} advance" if tie["winner"] else ""
                lines.append(f"- {tie['label']} (aggregate {tie['aggregate'][0]}-{tie['aggregate'][1]}){winner}: "
                             f"{legs}")
        return Answer("\n".join(lines), {"competition": competition, "season": season, "stages": stages})

    # --- statistics -----------------------------------------------------------------------------------------------

    def competition_summary(self, competition=None, season=None):
        competition = self._competition(competition) if competition else None
        summary = self._summary_stats(self._select(competition=competition, season=season))
        lines = [f"Match statistics{self._scope(competition, season)}:",
                 f"- Matches: {summary['matches']}",
                 f"- Goals: {summary['goals']}",
                 f"- Average goals per match: {summary['average_goals']:.2f}",
                 f"- Home win rate: {summary['home_win_rate']:.1f}%",
                 f"- Draw rate: {summary['draw_rate']:.1f}%",
                 f"- Away win rate: {summary['away_win_rate']:.1f}%"]
        return Answer("\n".join(lines), {"competition": competition, "season": season, **summary})

    def compare_seasons(self, season, other_season, competition=competitions.SERIE_A):
        competition = self._competition(competition)
        rows, lines = [], [f"{competition}: {season} vs {other_season}"]
        for year in (season, other_season):
            stats = self._summary_stats(self._select(competition=competition, season=year))
            standings = self._standings(competition, year) if competition in competitions.LEAGUES else []
            stats["season"] = year
            stats["champion"] = standings[0]["team"] if standings else None
            stats["top_scoring_team"] = (max(standings, key=lambda r: r["goals_for"])["team"] if standings else None)
            rows.append(stats)
            lines.append(f"{year}: {stats['matches']} matches, {stats['goals']} goals, "
                         f"{stats['average_goals']:.2f} goals/match, home wins {stats['home_win_rate']:.1f}%, "
                         f"draws {stats['draw_rate']:.1f}%, away wins {stats['away_win_rate']:.1f}%"
                         + (f", champion {stats['champion']}" if stats["champion"] else ""))
        return Answer("\n".join(lines), {"competition": competition, "seasons": rows})

    def best_records(self, venue="all", competition=None, season=None, min_matches=None, limit=10):
        competition = self._competition(competition) if competition else None
        venue = _venue(venue)
        records = collections.defaultdict(Record)
        for match in self._select(competition=competition, season=season):
            if venue in ("any", "home"):
                records[match.home].add(match, match.home)
            if venue in ("any", "away"):
                records[match.away].add(match, match.away)
        if not records:
            raise QueryError("No matches found for that selection.")
        if min_matches is None:
            min_matches = max(1, round(0.25 * max(r.played for r in records.values())))
        eligible = [(k, r) for k, r in records.items() if r.played >= min_matches]
        eligible.sort(key=lambda kv: (-kv[1].win_rate, -kv[1].points / kv[1].played, -kv[1].goal_difference,
                                      -kv[1].played, self.teams.display(kv[0])))
        rows = [{"team": self.teams.display(k), **r.as_dict()} for k, r in eligible[:limit]]
        label = {"home": "home", "away": "away"}.get(venue, "overall")
        lines = [f"Best {label} records{self._scope(competition, season)} (minimum {min_matches} matches):"]
        lines += [f"{i}. {r['team']} - win rate {r['win_rate']:.1f}% ({r['won']}W, {r['drawn']}D, {r['lost']}L "
                  f"in {r['played']} matches)" for i, r in enumerate(rows, 1)]
        return Answer("\n".join(lines), {"venue": label, "min_matches": min_matches, "teams": rows})

    # --- players --------------------------------------------------------------------------------------------------

    def search_players(self, name=None, nationality=None, club=None, position=None, min_overall=None, limit=20):
        found = self._find_players(name=name, nationality=nationality, club=club, position=position,
                                   min_overall=min_overall)
        criteria = ", ".join(f"{k}: {v}" for k, v in (("name", name), ("nationality", nationality), ("club", club),
                                                     ("position", position), ("min overall", min_overall)) if v)
        lines = [f"Players ({criteria or 'all'}): {len(found)} found, highest rated first"]
        lines += [f"{i}. {p.name} - Overall: {p.overall}, Position: {p.position}, Club: {p.club or 'none'}, "
                  f"Nationality: {p.nationality}" for i, p in enumerate(found[:limit], 1)]
        if len(found) > limit:
            lines.append(f"... ({len(found) - limit} more players)")
        return Answer("\n".join(lines), {"total": len(found), "players": [p.as_dict() for p in found[:limit]]})

    def player_profile(self, name):
        candidates = self._find_players(name=name)
        if not candidates:
            similar = self._similar_players(name)
            if not similar:
                raise QueryError(f"No player called {name!r} in the FIFA dataset.")
            lines = [f"{name} is not in the FIFA dataset. Players with similar names:"]
            lines += [f"- {p.name} - Overall: {p.overall}, Position: {p.position}, Club: {p.club or 'none'}"
                      for p in similar]
            return Answer("\n".join(lines), {"player": None, "similar_players": [p.as_dict() for p in similar]})
        wanted = plain(name)
        player = next((p for p in candidates if plain(p.name) == wanted), candidates[0])
        others = [p for p in candidates if p is not player][:10]
        club_key = self._player_club[id(player)]
        lines = [f"{player.name}",
                 f"- Club: {player.club or 'none'}", f"- Nationality: {player.nationality}",
                 f"- Position: {player.position}, Jersey Number: {player.jersey_number}",
                 f"- Overall: {player.overall}, Potential: {player.potential}", f"- Age: {player.age}",
                 f"- Height: {player.height}, Weight: {player.weight}, Preferred foot: {player.preferred_foot}",
                 f"- Value: {player.value}, Wage: {player.wage}"]
        top_skills = sorted(player.skills.items(), key=lambda kv: -kv[1])[:6]
        if top_skills:
            lines.append("- Best attributes: " + ", ".join(f"{k} {v}" for k, v in top_skills))
        if club_key in self.brazilian_clubs:
            record = _record(self._by_team[club_key], club_key)
            lines.append(f"- {self.teams.display(club_key)} in the match data: {record.played} matches, "
                         f"{record.won}W {record.drawn}D {record.lost}L")
        if others:
            lines.append("Other players matching that name: " + ", ".join(f"{p.name} ({p.club})" for p in others))
        return Answer("\n".join(lines), {"player": player.as_dict(), "other_matches": [p.as_dict() for p in others]})

    def brazilian_players_by_club(self, nationality="Brazil", brazilian_clubs_only=True):
        clubs = collections.defaultdict(list)
        for player in self._find_players(nationality=nationality):
            key = self._player_club[id(player)]
            if key and (key in self.brazilian_clubs or not brazilian_clubs_only):
                clubs[key].append(player)
        rows = sorted(({"club": self.teams.display(k), "players": len(ps),
                        "average_overall": round(sum(p.overall for p in ps) / len(ps), 1),
                        "top_players": [p.name for p in sorted(ps, key=lambda p: -p.overall)[:5]]}
                       for k, ps in clubs.items()), key=lambda r: (-r["players"], -r["average_overall"], r["club"]))
        where = "Brazilian clubs" if brazilian_clubs_only else "each club"
        lines = [f"{nationality} players at {where}:"]
        lines += [f"- {r['club']}: {r['players']} players (avg rating: {r['average_overall']:.1f}) - top: "
                  f"{', '.join(r['top_players'])}" for r in rows]
        return Answer("\n".join(lines), {"nationality": nationality, "clubs": rows})

    # --- the data itself ------------------------------------------------------------------------------------------

    def dataset_overview(self):
        coverage = collections.defaultdict(set)
        for match in self.matches:
            coverage[match.competition].add(match.season)
        rows = [dataclasses.asdict(info) for info in self.datasets]
        lines = ["Datasets:"]
        lines += [f"- {d['name']} ({d['file']}): {d['rows']} rows" + ("" if d["loaded"] else f" - {d['problem']}")
                  for d in rows]
        lines.append(f"Distinct matches after merging datasets: {len(self.matches)} "
                     f"({len(self.discarded)} records discarded as contradicting another dataset)")
        lines += [f"- {c}: seasons {_season_span(sorted(coverage[c]))}" for c in competitions.ALL if c in coverage]
        lines.append(f"Players: {len(self.players)}")
        return Answer("\n".join(lines), {
            "datasets": rows, "matches": len(self.matches), "discarded_records": len(self.discarded),
            "players": len(self.players),
            "competitions": {c: sorted(s) for c, s in coverage.items()},
        })

    # --- internals ------------------------------------------------------------------------------------------------

    def _team(self, name):
        try:
            return self.teams.resolve(name)
        except TeamNotFound as error:
            raise QueryError(str(error)) from None

    def _competition(self, name):
        try:
            return competitions.resolve(name)
        except UnknownCompetition as error:
            raise QueryError(str(error)) from None

    def _select(self, team=None, opponent=None, venue="any", competition=None, season=None, date_from=None,
                date_to=None, stage=None):
        team_key = self._team(team) if team else None
        opponent_key = self._team(opponent) if opponent else None
        competition = self._competition(competition) if competition else None
        start, end = _date(date_from, "date_from"), _date(date_to, "date_to")
        stage = competitions.stage_name(stage) if stage else None
        venue = _venue(venue)
        pool = self._by_team[team_key] if team_key else self._by_team[opponent_key] if opponent_key else self.matches
        found = []
        for m in pool:
            if team_key and ((venue == "home" and m.home != team_key) or (venue == "away" and m.away != team_key)):
                continue
            if opponent_key and opponent_key not in (m.home, m.away):
                continue
            if team_key and opponent_key and {m.home, m.away} != {team_key, opponent_key}:
                continue
            if competition and m.competition != competition:
                continue
            if season and m.season != int(season):
                continue
            if (start or end) and (not m.date or (start and m.date < start) or (end and m.date > end)):
                continue
            if stage and (m.stage or "").lower() != stage.lower():
                continue
            found.append(m)
        return found

    def _standings(self, competition, season):
        records = collections.defaultdict(Record)
        for match in self._select(competition=competition, season=season):
            records[match.home].add(match, match.home)
            records[match.away].add(match, match.away)
        if records:
            # A team with under half the matches of the busiest team only appears through stray or
            # mislabelled results (e.g. a regional match tagged as Série A), so it is not ranked.
            busiest = max(r.played for r in records.values())
            records = {k: r for k, r in records.items() if r.played * 2 >= busiest}
        ranked = sorted(records.items(), key=lambda kv: (-kv[1].points, -kv[1].won, -kv[1].goal_difference,
                                                         -kv[1].goals_for, self.teams.display(kv[0])))
        return [{"position": i, "team": self.teams.display(k), **r.as_dict()} for i, (k, r) in enumerate(ranked, 1)]

    def _head_to_head(self, team, opponent, found):
        wins = sum(1 for m in found if m.winner() == team)
        losses = sum(1 for m in found if m.winner() == opponent)
        return {"team": self.teams.display(team), "opponent": self.teams.display(opponent), "matches": len(found),
                "wins": wins, "opponent_wins": losses, "draws": len(found) - wins - losses,
                "goals_for": sum(m.goals_for(team) for m in found),
                "goals_against": sum(m.goals_against(team) for m in found),
                "last_meeting": self._match_dict(found[0]) if found else None}

    def _h2h_line(self, team, opponent, h2h):
        return (f"Head-to-head in dataset: {self.teams.display(team)} {h2h['wins']} wins, "
                f"{self.teams.display(opponent)} {h2h['opponent_wins']} wins, {h2h['draws']} draws")

    def _tie(self, legs):
        first = legs[0]
        a, b = first.home, first.away
        aggregate = [sum(m.goals_for(a) for m in legs), sum(m.goals_for(b) for m in legs)]
        winner = None
        if aggregate[0] != aggregate[1]:
            winner = self.teams.display(a if aggregate[0] > aggregate[1] else b)
        return {"label": f"{self.teams.display(a)} vs {self.teams.display(b)}",
                "teams": [self.teams.display(a), self.teams.display(b)], "aggregate": aggregate, "winner": winner,
                "matches": [self._match_dict(m) for m in legs]}

    def _players_at(self, club_key):
        return [p for p in self.players if self._player_club[id(p)] == club_key]

    def _find_players(self, name=None, nationality=None, club=None, position=None, min_overall=None):
        found = self.players
        if name:
            words = plain(name).split()
            found = [p for p in found if all(w in plain(p.name).split() or w in plain(p.name) for w in words)]
        if nationality:
            wanted = plain(nationality)
            wanted = _NATIONALITY_WORDS.get(wanted, wanted)
            found = [p for p in found if plain(p.nationality) == wanted]
        if club:
            try:
                key = self.teams.resolve(club)
                found = [p for p in found if self._player_club[id(p)] == key]
            except TeamNotFound:
                wanted = plain(club)
                found = [p for p in found if wanted in plain(p.club)]
        if position:
            wanted = plain(position)
            wanted = _POSITION_WORDS.get(wanted, wanted)
            codes = POSITION_GROUPS.get(wanted, {position.strip().upper()})
            found = [p for p in found if p.position in codes]
        if min_overall is not None:
            found = [p for p in found if p.overall >= int(min_overall)]
        return sorted(found, key=lambda p: (-p.overall, -(p.potential or 0), p.name))

    def _similar_players(self, name, limit=10):
        """Players sharing any part of the name, best known first."""
        words = [w for w in plain(name).split() if len(w) > 2]
        similar = [p for p in self.players if any(w in plain(p.name).split() for w in words)]
        return sorted(similar, key=lambda p: (-p.overall, p.name))[:limit]

    def _summary_stats(self, found):
        goals = sum(m.home_goals + m.away_goals for m in found)
        home = sum(1 for m in found if m.home_goals > m.away_goals)
        away = sum(1 for m in found if m.away_goals > m.home_goals)
        draws = len(found) - home - away

        def rate(n):
            return round(100.0 * n / len(found), 1) if found else 0.0

        return {"matches": len(found), "goals": goals,
                "average_goals": round(goals / len(found), 2) if found else 0.0,
                "home_wins": home, "draws": draws, "away_wins": away,
                "home_win_rate": rate(home), "draw_rate": rate(draws), "away_win_rate": rate(away)}

    def _summary(self, match, with_round=True):
        detail = ""
        if with_round and match.competition in competitions.LEAGUES and match.round:
            detail = f", Round {match.round}"
        elif with_round and match.stage:
            detail = f", {match.stage[0].upper()}{match.stage[1:]}"
        when = match.date.isoformat() if match.date else f"{match.season} (date unknown)"
        return (f"{when}: {self.teams.display(match.home)} {match.home_goals}-{match.away_goals} "
                f"{self.teams.display(match.away)} ({match.competition}{detail})")

    def _match_dict(self, match, with_round=True):
        return {"date": match.date.isoformat() if match.date else None, "competition": match.competition,
                "season": match.season, "round": match.round, "stage": match.stage,
                "home_team": self.teams.display(match.home), "away_team": self.teams.display(match.away),
                "home_goals": match.home_goals, "away_goals": match.away_goals, "arena": match.arena,
                "statistics": match.statistics, "sources": match.sources,
                "summary": self._summary(match, with_round)}

    def _describe_selection(self, team, opponent, venue, competition, season, date_from, date_to, stage):
        if team and opponent:
            title = f"{self.teams.display(team)} vs {self.teams.display(opponent)}"
            rivalry = _RIVALRY_BY_PAIR.get(frozenset((team, opponent)))
            title += f" ({rivalry})" if rivalry else ""
        elif team:
            title = f"{self.teams.display(team)} {_venue(venue) + ' ' if _venue(venue) != 'any' else ''}matches"
        else:
            title = "Matches"
        if stage:
            title += f" - {competitions.stage_name(stage)}"
        title += self._scope(competition, season)
        if date_from or date_to:
            title += f" from {date_from or 'the start'} to {date_to or 'the end'}"
        return title

    def _scope(self, competition, season):
        parts = [self._competition(competition) if competition else None, str(season) if season else None]
        parts = [p for p in parts if p]
        return f" ({' '.join(parts)})" if parts else " (all provided data)"


def _merge(raw_matches, teams, discarded):
    """One Match per real match, however many datasets recorded it. Contradictory records go to discarded."""
    groups = collections.defaultdict(list)
    for raw in raw_matches:
        international = raw.source == datasets.LIBERTADORES
        groups[(raw.competition, teams.key_for(raw.home, international),
                teams.key_for(raw.away, international))].append(raw)
    merged = []
    for (competition, home, away), records in groups.items():
        fixtures = []
        for raw in sorted(records, key=lambda r: datasets.PRIORITY[r.source]):
            candidates = [m for m in fixtures if raw.source not in m.sources and _same_fixture(m, raw)]
            if not candidates and _contradicts_league_fixture(fixtures, raw):
                discarded.append(raw)
                continue
            if candidates:
                match = min(candidates, key=lambda m: _days_apart(m.date, raw.date))
                match.sources.append(raw.source)
                match.statistics = match.statistics or raw.statistics
                match.round = match.round or raw.round
                match.stage = match.stage or raw.stage
                match.arena = match.arena or raw.arena
                match.date = match.date or raw.date
            else:
                fixtures.append(Match(competition, raw.season, raw.date, home, away, raw.home_goals, raw.away_goals,
                                      raw.round, raw.stage, raw.arena, raw.statistics, [raw.source]))
        merged.extend(fixtures)
    return merged


def _contradicts_league_fixture(fixtures, raw):
    """A league pairing happens once a season. A secondary dataset recording it again (e.g. a cup tie
    mislabelled as Série A) contradicts the dataset that is primary for that fixture."""
    return raw.competition in competitions.LEAGUES and any(
        m.season == raw.season and m.sources[0] != raw.source for m in fixtures)


def _same_fixture(match, raw):
    if match.competition in competitions.LEAGUES:
        return match.season == raw.season  # each home/away pairing happens once per league season
    return _days_apart(match.date, raw.date) <= 3


def _days_apart(a, b):
    return abs((a - b).days) if a and b else 10_000


def _name_cup_stages(matches):
    """Copa do Brasil rounds are numbered; count back from the final (a lone two-team last round)."""
    by_season = collections.defaultdict(list)
    for match in matches:
        if match.competition == competitions.COPA_DO_BRASIL and match.round:
            by_season[match.season].append(match)
    for season_matches in by_season.values():
        last = max(m.round for m in season_matches)
        pairs = {frozenset((m.home, m.away)) for m in season_matches if m.round == last}
        final_round = last if last >= 5 and len(pairs) == 1 else None
        for match in season_matches:
            if final_round and final_round - match.round < len(competitions.KNOCKOUT_STAGES):
                match.stage = competitions.KNOCKOUT_STAGES[-1 - (final_round - match.round)]
            else:
                match.stage = f"Round {match.round}"


def _record(found, key):
    record = Record()
    for match in found:
        record.add(match, key)
    return record


def _venue(venue):
    venue = plain(venue or "any")
    if venue in ("home", "at home", "mandante"):
        return "home"
    if venue in ("away", "away from home", "visitante", "visiting"):
        return "away"
    if venue in ("any", "all", "either", "both", ""):
        return "any"
    raise QueryError(f"Unknown venue {venue!r}: use 'home', 'away' or 'any'.")


def _date(value, name):
    if not value:
        return None
    parsed = parse_date(str(value))
    if not parsed:
        raise QueryError(f"Could not understand {name} {value!r}; use YYYY-MM-DD or DD/MM/YYYY.")
    return parsed


def _season_span(seasons):
    if not seasons:
        return "none"
    return str(seasons[0]) if len(seasons) == 1 else f"{seasons[0]}-{seasons[-1]}"
