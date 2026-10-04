"""Brazilian Soccer MCP server: natural-language-friendly tools over the Kaggle datasets.

Run with:  python server.py   (stdio transport)
"""
from collections import defaultdict
from typing import Optional

from mcp.server.mcpserver import MCPServer

from soccer_data import (BRASILEIRAO, DERBY_LOOKUP, LIBERTADORES, SoccerData, normalize_competition,
                         normalize_team)

mcp = MCPServer("brazilian-soccer")
data = SoccerData()


def _pct(n, d):
    return f"{(100.0 * n / d):.1f}%" if d else "n/a"


def _scope(competition, season):
    parts = [normalize_competition(competition) or "all competitions"]
    if season:
        parts.append(str(season))
    return ", ".join(parts)


def _format_record(title, rec):
    return "\n".join([
        f"{title}:",
        f"- Matches: {rec['matches']}",
        f"- Wins: {rec['wins']}, Draws: {rec['draws']}, Losses: {rec['losses']}",
        f"- Goals For: {rec['gf']}, Goals Against: {rec['ga']}",
        f"- Win rate: {_pct(rec['wins'], rec['matches'])}",
    ])


@mcp.tool()
def search_matches(team: Optional[str] = None, opponent: Optional[str] = None,
                   competition: Optional[str] = None, season: Optional[int] = None,
                   date_from: Optional[str] = None, date_to: Optional[str] = None,
                   stage: Optional[str] = None, venue: str = "all", limit: int = 50) -> str:
    """Find matches by team (and optional opponent), competition (Brasileirão, Copa do Brasil,
    Libertadores, Serie B, Serie C), season, date range (YYYY-MM-DD or DD/MM/YYYY), stage
    (e.g. 'final', 'semifinals') and venue ('home', 'away', 'all'). Most recent first."""
    ms = data.find_matches(team, opponent, competition, season, date_from, date_to, stage, venue)
    lines = [f"Found {len(ms)} matches ({_scope(competition, season)}):"]
    lines += [f"- {m.describe()}" for m in ms[:limit]]
    if len(ms) > limit:
        lines.append(f"- ... ({len(ms) - limit} more matches in dataset)")
    if team and opponent and ms:
        lines.append("")
        lines.append(_h2h_summary(team, opponent, ms))
    return "\n".join(lines)


def _h2h_summary(team_a, team_b, ms):
    a = data.team_matcher(team_a)
    rec = data.record(ms, a)
    na, nb = data.team_display(team_a), data.team_display(team_b)
    return (f"Head-to-head in dataset: {na} {rec['wins']} wins, {nb} {rec['losses']} wins, "
            f"{rec['draws']} draws (goals {rec['gf']}-{rec['ga']})")


@mcp.tool()
def head_to_head(team_a: str, team_b: str, competition: Optional[str] = None) -> str:
    """Head-to-head record between two teams across all datasets, with recent meetings."""
    ms = data.find_matches(team_a, team_b, competition)
    name = DERBY_LOOKUP.get(frozenset((normalize_team(team_a), normalize_team(team_b))))
    title = f"{data.team_display(team_a)} vs {data.team_display(team_b)}" + (f" ({name})" if name else "")
    lines = [f"{title}: {len(ms)} matches in dataset", _h2h_summary(team_a, team_b, ms), "Recent meetings:"]
    lines += [f"- {m.describe()}" for m in ms[:10]]
    return "\n".join(lines)


@mcp.tool()
def last_meeting(team_a: str, team_b: str) -> str:
    """When did two teams last play each other, and what was the score?"""
    ms = [m for m in data.find_matches(team_a, team_b) if m.date]
    if not ms:
        return f"No matches found between {team_a} and {team_b}."
    return f"Most recent meeting of {data.team_display(team_a)} and {data.team_display(team_b)}:\n- {ms[0].describe()}"


@mcp.tool()
def team_record(team: str, season: Optional[int] = None, competition: Optional[str] = None,
                venue: str = "all") -> str:
    """Win/draw/loss record and goals for a team, optionally by season, competition and venue."""
    ms = data.find_matches(team, competition=competition, season=season, venue=venue)
    rec = data.record(ms, data.team_matcher(team))
    where = {"home": "home record", "away": "away record"}.get(venue, "record")
    return _format_record(f"{data.team_display(team)} {where} ({_scope(competition, season)})", rec)


@mcp.tool()
def team_competitions(team: str) -> str:
    """Which competitions (and seasons) has a team played in?"""
    ms = data.find_matches(team)
    by = defaultdict(set)
    for m in ms:
        by[m.competition].add(m.season)
    lines = [f"{data.team_display(team)} competitions in dataset ({len(ms)} matches):"]
    for comp, seasons in sorted(by.items()):
        s = sorted(x for x in seasons if x)
        lines.append(f"- {comp}: {len(s)} seasons ({s[0]}-{s[-1]})" if s else f"- {comp}")
    return "\n".join(lines)


def _table_lines(rows, champion_label=True, limit=None):
    lines = []
    for i, r in enumerate(rows[:limit] if limit else rows, 1):
        suffix = " - Champion" if i == 1 and champion_label else ""
        lines.append(f"{i}. {r['name']} - {r['points']} pts ({r['wins']}W, {r['draws']}D, {r['losses']}L, "
                     f"GF {r['gf']}, GA {r['ga']}, GD {r['gd']:+d}){suffix}")
    return lines


@mcp.tool()
def standings(season: int, competition: str = BRASILEIRAO) -> str:
    """League table for a season calculated from match results (3 pts win, 1 draw)."""
    comp = normalize_competition(competition)
    rows = data.table(data.season_matches(season, comp))
    if not rows:
        return f"No {comp} matches found for {season}."
    return "\n".join([f"{season} {comp} Final Standings (calculated from matches):"] + _table_lines(rows))


@mcp.tool()
def relegated_teams(season: int, competition: str = BRASILEIRAO) -> str:
    """Teams relegated in a season (bottom four of the calculated table)."""
    rows = data.table(data.season_matches(season, normalize_competition(competition)))
    if not rows:
        return f"No matches found for {season}."
    bottom = rows[-4:]
    return "\n".join([f"Relegated from {season} {normalize_competition(competition)} (bottom 4 of calculated table):"]
                     + [f"- {r['name']} - {r['points']} pts" for r in bottom])


@mcp.tool()
def top_scoring_team(season: Optional[int] = None, competition: str = BRASILEIRAO, limit: int = 5) -> str:
    """Teams that scored the most goals in a competition/season."""
    rows = data.table(data.find_matches(competition=competition, season=season))
    rows.sort(key=lambda r: -r["gf"])
    lines = [f"Top scoring teams ({_scope(competition, season)}):"]
    lines += [f"{i}. {r['name']} - {r['gf']} goals in {r['matches']} matches" for i, r in enumerate(rows[:limit], 1)]
    return "\n".join(lines)


@mcp.tool()
def libertadores_bracket(season: int) -> str:
    """Copa Libertadores knockout matches (round of 16 to final) for a season."""
    order = ["round of 16", "quarterfinals", "semifinals", "final"]
    ms = data.find_matches(competition=LIBERTADORES, season=season)
    lines = [f"{season} Copa Libertadores knockout bracket:"]
    for stage in order:
        stage_ms = sorted((m for m in ms if m.stage == stage), key=lambda m: m.date or 0)
        if stage_ms:
            lines.append(f"{stage.title()} ({stage}):")
            lines += [f"- {m.describe()}" for m in stage_ms]
    if len(lines) == 1:
        lines.append("No knockout matches in dataset.")
    return "\n".join(lines)


def _player_line(i, p):
    return (f"{i}. {p['name']} - Overall: {p['overall']}, Potential: {p['potential']}, Position: {p['position']}, "
            f"Club: {p['club'] or 'Free agent'}, Nationality: {p['nationality']}, Age: {p['age']}")


@mcp.tool()
def search_players(name: Optional[str] = None, nationality: Optional[str] = None, club: Optional[str] = None,
                   position: Optional[str] = None, min_overall: Optional[int] = None, limit: int = 20) -> str:
    """Search FIFA player data by name, nationality, club and position (e.g. 'ST', 'GK', 'forward').
    Results sorted by overall rating."""
    ps = data.find_players(name, nationality, club, position, min_overall)
    lines = [f"Found {len(ps)} players:"]
    lines += [_player_line(i, p) for i, p in enumerate(ps[:limit], 1)]
    if name and len(ps) <= 3:
        for p in ps:
            skills = ", ".join(f"{k}: {v}" for k, v in p["skills"].items() if v)
            lines.append(f"   {p['name']}: #{p['jersey']}, {p['height']}, {p['weight']}, {p['foot']} foot, "
                         f"value {p['value']}; {skills}")
    return "\n".join(lines)


@mcp.tool()
def brazilian_clubs_players_summary() -> str:
    """Brazilian players at Brazilian clubs, grouped by club with average rating."""
    by = defaultdict(list)
    for p in data.find_players(nationality="Brazil"):
        if data.is_brazilian_club(p):
            by[p["club"]].append(p["overall"])
    rows = sorted(by.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    lines = ["Brazilian players at Brazilian clubs:"]
    lines += [f"- {club}: {len(r)} players (avg rating: {sum(r) / len(r):.0f})" for club, r in rows]
    return "\n".join(lines)


@mcp.tool()
def competition_statistics(competition: Optional[str] = None, season: Optional[int] = None) -> str:
    """Average goals per match, home/away win and draw rates for a competition/season."""
    ms = data.find_matches(competition=competition, season=season)
    return _stats_text(f"Statistics ({_scope(competition, season)})", ms)


def _stats_text(title, ms):
    n = len(ms)
    goals = sum(m.home_goals + m.away_goals for m in ms)
    hw = sum(m.home_goals > m.away_goals for m in ms)
    aw = sum(m.home_goals < m.away_goals for m in ms)
    return "\n".join([
        f"{title}:", f"- Matches: {n}", f"- Total goals: {goals}",
        f"- Average goals per match: {goals / n:.2f}" if n else "- Average goals per match: n/a",
        f"- Home win rate: {_pct(hw, n)}", f"- Away win rate: {_pct(aw, n)}", f"- Draw rate: {_pct(n - hw - aw, n)}",
    ])


@mcp.tool()
def biggest_wins(competition: Optional[str] = None, season: Optional[int] = None, limit: int = 10) -> str:
    """Largest winning margins in the dataset."""
    ms = sorted(data.find_matches(competition=competition, season=season),
                key=lambda m: (-abs(m.home_goals - m.away_goals), -(m.home_goals + m.away_goals)))
    lines = [f"Biggest victories ({_scope(competition, season)}):"]
    lines += [f"{i}. {m.describe()}" for i, m in enumerate(ms[:limit], 1)]
    return "\n".join(lines)


@mcp.tool()
def best_record(venue: str = "all", competition: Optional[str] = None, season: Optional[int] = None,
                min_matches: int = 30, limit: int = 10) -> str:
    """Teams ranked by win rate, at home, away or overall."""
    ms = data.find_matches(competition=competition, season=season)
    stats = defaultdict(lambda: [None, 0, 0, 0])  # name, played, wins, draws
    for m in ms:
        sides = []
        if venue in ("all", "home"):
            sides.append((m.home_key, m.home_name, m.home_goals - m.away_goals))
        if venue in ("all", "away"):
            sides.append((m.away_key, m.away_name, m.away_goals - m.home_goals))
        for key, name, diff in sides:
            s = stats[key]
            s[0] = s[0] or name
            s[1] += 1
            s[2] += diff > 0
            s[3] += diff == 0
    rows = [s for s in stats.values() if s[1] >= min_matches] or list(stats.values())
    rows.sort(key=lambda s: -s[2] / s[1])
    label = {"home": "home", "away": "away"}.get(venue, "overall")
    lines = [f"Best {label} records ({_scope(competition, season)}, min {min_matches} matches):"]
    lines += [f"{i}. {s[0]} - win rate {_pct(s[2], s[1])} ({s[2]}W {s[3]}D {s[1] - s[2] - s[3]}L in {s[1]})"
              for i, s in enumerate(rows[:limit], 1)]
    return "\n".join(lines)


@mcp.tool()
def compare_seasons(season_a: int, season_b: int, competition: str = BRASILEIRAO) -> str:
    """Compare aggregate statistics and champions of two seasons."""
    parts = []
    for s in (season_a, season_b):
        ms = data.season_matches(s, normalize_competition(competition))
        text = _stats_text(f"{s} {normalize_competition(competition)}", ms)
        rows = data.table(ms)
        if rows:
            text += f"\n- Champion (calculated): {rows[0]['name']} ({rows[0]['points']} pts)"
            top = max(rows, key=lambda r: r["gf"])
            text += f"\n- Top scoring team: {top['name']} ({top['gf']} goals)"
        parts.append(text.replace("Average goals per match", "Average goals per match (goals per match)"))
    return "\n\n".join(parts)


@mcp.tool()
def derbies(season: Optional[int] = None, competition: Optional[str] = None) -> str:
    """Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista, ...)."""
    out = []
    for m in data.find_matches(competition=competition, season=season):
        name = DERBY_LOOKUP.get(frozenset((m.home_key, m.away_key)))
        if name:
            out.append(f"- {name}: {m.describe()}")
    return "\n".join([f"Derbies found ({_scope(competition, season)}): {len(out)}"] + out[:200])


@mcp.tool()
def club_profile(club: str) -> str:
    """Combined view of a club: FIFA players plus match record per competition."""
    ps = data.find_players(club=club)
    lines = [f"{data.team_display(club)} profile", f"FIFA players: {len(ps)} players"]
    lines += ["  " + _player_line(i, p) for i, p in enumerate(ps[:10], 1)]
    matcher = data.team_matcher(club)
    by = defaultdict(list)
    for m in data.find_matches(club):
        by[m.competition].append(m)
    lines.append("Match record by competition:")
    for comp, ms in sorted(by.items()):
        r = data.record(ms, matcher)
        lines.append(f"- {comp}: {r['matches']} matches, {r['wins']}W {r['draws']}D {r['losses']}L, "
                     f"goals {r['gf']}-{r['ga']}")
    return "\n".join(lines)


@mcp.tool()
def dataset_overview() -> str:
    """List the loaded datasets and their row counts."""
    lines = ["Loaded datasets:"]
    lines += [f"- {name}: {count} rows" for name, count in data.source_counts.items()]
    lines.append(f"Unique matches after merging: {len(data.matches)}; players: {len(data.players)}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
