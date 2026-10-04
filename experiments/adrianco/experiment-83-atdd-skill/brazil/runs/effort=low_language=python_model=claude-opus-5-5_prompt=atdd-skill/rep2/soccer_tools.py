"""Query tools that turn the knowledge base into formatted answers."""
from collections import Counter, defaultdict

from soccer_data import BRASILEIRAO, SoccerData, competition_name, fold, team_key

_data = None


def data():
    global _data
    if _data is None:
        _data = SoccerData()
    return _data


def _list(matches, limit):
    lines = [m.describe() for m in matches[:limit]]
    if len(matches) > limit:
        lines.append(f"- ... ({len(matches) - limit} more matches in dataset)")
    return lines


def _h2h_line(team, opponent, matches):
    d = data()
    r = d.tally(matches, d.resolve_team(team))
    return (f"Head-to-head in dataset: {d.name_of(next(iter(d.resolve_team(team))))} {r['wins']} wins, "
            f"{d.name_of(next(iter(d.resolve_team(opponent))))} {r['losses']} wins, {r['draws']} draws")


def search_matches(team=None, opponent=None, competition=None, season=None, stage=None,
                   date_from=None, date_to=None, venue="all", derbies_only=False, limit=25):
    d = data()
    ms = d.filter_matches(team, opponent, competition, season, stage, date_from, date_to, venue)
    if derbies_only:
        ms = [m for m in ms if d.is_derby(m)]
    parts = [x for x in (team and f"{team}" + (f" vs {opponent}" if opponent else ""), competition,
                         stage, season and str(season), derbies_only and "derbies") if x]
    lines = [f"Matches ({', '.join(parts) or 'all'}): {len(ms)} found"] + _list(ms, int(limit))
    if team and opponent:
        lines.append(_h2h_line(team, opponent, ms))
    return "\n".join(lines)


def last_meeting(team, opponent):
    ms = data().filter_matches(team, opponent)
    if not ms:
        return f"No matches found between {team} and {opponent}."
    return f"Most recent meeting of {team} and {opponent}:\n" + ms[0].describe()


def team_record(team, season=None, venue="all", competition=None):
    d = data()
    keys = d.resolve_team(team)
    ms = d.filter_matches(team, competition=competition, season=season, venue=venue)
    r = d.tally(ms, keys)
    label = f"{d.name_of(next(iter(keys)))} {'' if venue == 'all' else venue + ' '}record"
    scope = " ".join(str(x) for x in (season, competition_name(competition) if competition else "all competitions") if x)
    rate = 100 * r["wins"] / r["matches"] if r["matches"] else 0
    return "\n".join([
        f"{label} ({scope}):",
        f"- Matches: {r['matches']}",
        f"- Wins: {r['wins']}, Draws: {r['draws']}, Losses: {r['losses']}",
        f"- Goals For: {r['goals_for']}, Goals Against: {r['goals_against']}",
        f"- Win rate: {rate:.1f}%",
    ])


def head_to_head(team, opponent, competition=None):
    d = data()
    ms = d.filter_matches(team, opponent, competition)
    by_comp = Counter(m.competition for m in ms)
    lines = [f"{team} vs {opponent}: {len(ms)} matches in dataset"]
    lines += [f"- {c}: {n} matches" for c, n in by_comp.most_common()]
    lines.append("Recent meetings:")
    lines += _list(ms, 10)
    lines.append(_h2h_line(team, opponent, ms))
    return "\n".join(lines)


def team_competitions(team):
    d = data()
    ms = d.filter_matches(team)
    seasons = defaultdict(set)
    for m in ms:
        seasons[m.competition].add(m.season)
    lines = [f"Competitions played by {team} in dataset:"]
    for c, s in sorted(seasons.items()):
        n = sum(m.competition == c for m in ms)
        lines.append(f"- {c}: {n} matches, seasons {min(s)}-{max(s)}")
    return "\n".join(lines)


def _player_line(i, p):
    return (f"{i}. {p['name']} - Overall: {p['overall']}, Position: {p['position']}, Club: {p['club'] or 'Free agent'}, "
            f"Nationality: {p['nationality']}, Age: {p['age']}, Potential: {p['potential']}")


def search_players(name=None, nationality=None, club=None, position=None, min_overall=None, limit=20):
    ps = data().players
    if name:
        ps = [p for p in ps if fold(name) in fold(p["name"])]
    if nationality:
        ps = [p for p in ps if fold(nationality) == fold(p["nationality"])]
    if club:
        ps = [p for p in ps if fold(club) in fold(p["club"]) or team_key(club) == team_key(p["club"])]
    if position:
        ps = [p for p in ps if fold(position) == fold(p["position"])]
    if min_overall:
        ps = [p for p in ps if p["overall"] >= int(min_overall)]
    ps = sorted(ps, key=lambda p: -p["overall"])
    lines = [f"Players found: {len(ps)}"] + [_player_line(i, p) for i, p in enumerate(ps[:int(limit)], 1)]
    return "\n".join(lines)


def brazilian_club_squads():
    d = data()
    rows = []
    for club in d.brazilian_club_names():
        ps = [p for p in d.players if p["club"] == club and p["nationality"] == "Brazil"]
        rows.append((club, len(ps), sum(p["overall"] for p in ps) / len(ps)))
    rows.sort(key=lambda r: -r[2])
    return "\n".join(["Brazilian players at Brazilian clubs:"] +
                     [f"- {c}: {n} players (avg rating: {a:.0f})" for c, n, a in rows])


def standings(season, competition=BRASILEIRAO, sort_by="points", limit=None):
    d = data()
    table = d.table(int(season), competition_name(competition))
    if not table:
        return f"No {competition} matches for {season}."
    relegated = {r["team"] for r in table[-4:]} if len(table) >= 20 else set()
    champion = table[0]["team"]
    if sort_by != "points":
        table = sorted(table, key=lambda r: -r[sort_by])
    lines = [f"{season} {competition_name(competition)} Final Standings (calculated from matches"
             f"{'' if sort_by == 'points' else ', sorted by ' + sort_by}):"]
    for i, r in enumerate(table[:int(limit) if limit else None], 1):
        tag = " - Champion" if r["team"] == champion else " - Relegated" if r["team"] in relegated else ""
        lines.append(f"{i}. {r['team']} - {r['points']} pts ({r['wins']}W, {r['draws']}D, {r['losses']}L, "
                     f"GF {r['goals_for']}, GA {r['goals_against']}){tag}")
    return "\n".join(lines)


def competition_stats(competition=BRASILEIRAO, season=None):
    ms = data().filter_matches(competition=competition, season=season)
    if not ms:
        return "No matches found."
    n = len(ms)
    goals = sum(m.home_goal + m.away_goal for m in ms)
    hw = sum(m.home_goal > m.away_goal for m in ms)
    aw = sum(m.home_goal < m.away_goal for m in ms)
    return "\n".join([
        f"{competition_name(competition)} statistics ({season or 'all seasons'}):",
        f"- Matches: {n}",
        f"- Total goals: {goals}",
        f"- Average goals per match: {goals / n:.2f}",
        f"- Home win rate: {100 * hw / n:.1f}%",
        f"- Away win rate: {100 * aw / n:.1f}%",
        f"- Draw rate: {100 * (n - hw - aw) / n:.1f}%",
    ])


def biggest_wins(competition=None, season=None, team=None, limit=10):
    ms = data().filter_matches(team, competition=competition, season=season)
    ms = sorted(ms, key=lambda m: (-abs(m.home_goal - m.away_goal), -(m.home_goal + m.away_goal)))
    return "\n".join(["Biggest victories in dataset:"] + [m.describe() for m in ms[:int(limit)]])


def best_records(venue="all", competition=BRASILEIRAO, season=None, min_matches=19, limit=10):
    d = data()
    stats = defaultdict(lambda: [0, 0, 0])
    for m in d.filter_matches(competition=competition, season=season):
        sides = []
        if venue in ("all", "home"):
            sides.append((m.home_key, m.home_goal - m.away_goal))
        if venue in ("all", "away"):
            sides.append((m.away_key, m.away_goal - m.home_goal))
        for key, diff in sides:
            stats[key][0 if diff > 0 else 1 if diff == 0 else 2] += 1
    rows = [(d.name_of(k), w, dr, l) for k, (w, dr, l) in stats.items() if w + dr + l >= int(min_matches)]
    rows.sort(key=lambda r: -r[1] / (r[1] + r[2] + r[3]))
    lines = [f"Best {venue} records ({competition_name(competition)}, {season or 'all seasons'}):"]
    for i, (t, w, dr, l) in enumerate(rows[:int(limit)], 1):
        lines.append(f"{i}. {t} - Win rate: {100 * w / (w + dr + l):.1f}% ({w}W, {dr}D, {l}L)")
    return "\n".join(lines)


def match_statistics(team=None, competition=None, season=None, limit=10):
    """Extended stats (shots, corners, attacks) from BR-Football-Dataset."""
    ms = [m for m in data().filter_matches(team, competition=competition, season=season) if m.extra and "home_shots" in m.extra]
    lines = [f"Matches with extended statistics: {len(ms)}"]
    for m in ms[:int(limit)]:
        e = m.extra
        lines.append(m.describe() + f" shots {e['home_shots']}-{e['away_shots']}, corners "
                     f"{e['home_corner']}-{e['away_corner']}, attacks {e['home_attack']}-{e['away_attack']}")
    return "\n".join(lines)


S, I = {"type": "string"}, {"type": "integer"}
TOOLS = {
    "search_matches": (search_matches, "Find matches by team, opponent, competition (Brasileirão, Copa do Brasil, "
                       "Libertadores, Serie B, Serie C), season, stage (e.g. final), date range, venue, derbies_only.",
                       dict(team=S, opponent=S, competition=S, season=I, stage=S, date_from=S, date_to=S,
                            venue=S, derbies_only={"type": "boolean"}, limit=I)),
    "last_meeting": (last_meeting, "Most recent match between two teams.", dict(team=S, opponent=S)),
    "team_record": (team_record, "Win/draw/loss and goals record for a team; venue is all/home/away.",
                    dict(team=S, season=I, venue=S, competition=S)),
    "head_to_head": (head_to_head, "Head-to-head comparison of two teams.", dict(team=S, opponent=S, competition=S)),
    "team_competitions": (team_competitions, "Competitions a team has played in.", dict(team=S)),
    "search_players": (search_players, "Search FIFA player data by name, nationality, club, position, min_overall.",
                       dict(name=S, nationality=S, club=S, position=S, min_overall=I, limit=I)),
    "brazilian_club_squads": (brazilian_club_squads, "Brazilian players at Brazilian clubs, per club.", {}),
    "standings": (standings, "League table for a season calculated from match results (champion, relegated). "
                  "sort_by: points, goals_for, goals_against, wins.",
                  dict(season=I, competition=S, sort_by=S, limit=I)),
    "competition_stats": (competition_stats, "Average goals per match and home/away/draw rates.",
                          dict(competition=S, season=I)),
    "biggest_wins": (biggest_wins, "Largest victory margins.", dict(competition=S, season=I, team=S, limit=I)),
    "best_records": (best_records, "Teams ranked by win rate; venue all/home/away.",
                     dict(venue=S, competition=S, season=I, min_matches=I, limit=I)),
    "match_statistics": (match_statistics, "Shots, corners and attacks for matches.",
                         dict(team=S, competition=S, season=I, limit=I)),
}
REQUIRED = {"last_meeting": ["team", "opponent"], "team_record": ["team"], "head_to_head": ["team", "opponent"],
            "team_competitions": ["team"], "standings": ["season"]}
