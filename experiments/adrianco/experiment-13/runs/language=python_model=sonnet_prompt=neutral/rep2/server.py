"""Brazilian Soccer MCP Server."""

from __future__ import annotations

import json
from typing import Optional

import pandas as pd
from mcp.server.fastmcp import FastMCP

from data_loader import (
    find_team_matches,
    get_fifa,
    get_matches,
    normalize_team,
)

mcp = FastMCP("Brazilian Soccer Knowledge Graph")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_match(row: pd.Series) -> str:
    date = row["datetime"]
    date_str = date.strftime("%Y-%m-%d") if pd.notna(date) else "unknown date"
    hg = int(row["home_goal"]) if pd.notna(row["home_goal"]) else "?"
    ag = int(row["away_goal"]) if pd.notna(row["away_goal"]) else "?"
    comp = row.get("competition", "")
    rnd = f" Round {int(row['round'])}" if "round" in row.index and pd.notna(row.get("round")) else ""
    stage = f" ({row['stage']})" if "stage" in row.index and pd.notna(row.get("stage")) else ""
    return f"{date_str}: {row['home_team']} {hg}-{ag} {row['away_team']} ({comp}{rnd}{stage})"


def _h2h_summary(df: pd.DataFrame, norm_a: str, norm_b: str) -> str:
    """Return win/draw/loss counts for team A vs team B."""
    wins_a = draws = wins_b = 0
    for _, r in df.iterrows():
        hg, ag = r["home_goal"], r["away_goal"]
        if pd.isna(hg) or pd.isna(ag):
            continue
        if r["home_norm"] == norm_a:
            if hg > ag:
                wins_a += 1
            elif hg == ag:
                draws += 1
            else:
                wins_b += 1
        else:
            if ag > hg:
                wins_a += 1
            elif hg == ag:
                draws += 1
            else:
                wins_b += 1
    return f"Wins: {wins_a} / Draws: {draws} / Losses: {wins_b}"


# ---------------------------------------------------------------------------
# Tool: search_matches
# ---------------------------------------------------------------------------

@mcp.tool()
def search_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Search matches across all competitions.

    Args:
        team: Team name (home or away). Partial match, e.g. "Flamengo".
        opponent: Optional opponent name to filter head-to-head.
        competition: Competition filter: "Brasileirao", "Copa do Brasil", "Libertadores", "all".
        season: Filter by season year, e.g. 2023.
        start_date: Start date filter YYYY-MM-DD.
        end_date: End date filter YYYY-MM-DD.
        limit: Maximum number of matches to return (default 20).
    """
    df = get_matches()

    if team:
        df = find_team_matches(team, df)
        if df.empty:
            return f"No matches found for team '{team}'."

    if opponent:
        opp_norm = normalize_team(opponent)
        df = df[
            df["home_norm"].str.contains(opp_norm, na=False) |
            df["away_norm"].str.contains(opp_norm, na=False)
        ]

    if competition and competition.lower() != "all":
        c_lower = competition.lower()
        df = df[df["competition"].str.lower().str.contains(c_lower, na=False)]

    if season:
        df = df[df["season"] == season]

    if start_date:
        df = df[df["datetime"] >= pd.Timestamp(start_date)]

    if end_date:
        df = df[df["datetime"] <= pd.Timestamp(end_date)]

    if df.empty:
        return "No matches found matching the given criteria."

    total = len(df)
    df_show = df.head(limit)

    lines = [f"Found {total} match(es) (showing {min(limit, total)}):"]
    for _, row in df_show.iterrows():
        lines.append("  " + _fmt_match(row))

    # Head-to-head summary when two teams specified
    if team and opponent:
        t_norm = normalize_team(team)
        o_norm = normalize_team(opponent)
        h2h = _h2h_summary(df, t_norm, o_norm)
        lines.append(f"\nHead-to-head ({team} perspective): {h2h}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_team_stats
# ---------------------------------------------------------------------------

@mcp.tool()
def get_team_stats(
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    home_only: bool = False,
    away_only: bool = False,
) -> str:
    """Get win/loss/draw record and goal statistics for a team.

    Args:
        team: Team name (partial match).
        competition: Filter by competition name.
        season: Filter by season year.
        home_only: Only count home matches.
        away_only: Only count away matches.
    """
    df = get_matches()
    t_norm = normalize_team(team)

    home_mask = df["home_norm"].str.contains(t_norm, na=False)
    away_mask = df["away_norm"].str.contains(t_norm, na=False)

    if home_only:
        df = df[home_mask]
    elif away_only:
        df = df[away_mask]
    else:
        df = df[home_mask | away_mask]

    if competition and competition.lower() != "all":
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]

    if season:
        df = df[df["season"] == season]

    if df.empty:
        return f"No matches found for '{team}'."

    wins = draws = losses = goals_for = goals_against = 0
    for _, r in df.iterrows():
        hg, ag = r["home_goal"], r["away_goal"]
        if pd.isna(hg) or pd.isna(ag):
            continue
        if r["home_norm"] and t_norm in r["home_norm"]:
            gf, ga = hg, ag
        else:
            gf, ga = ag, hg
        goals_for += gf
        goals_against += ga
        if gf > ga:
            wins += 1
        elif gf == ga:
            draws += 1
        else:
            losses += 1

    played = wins + draws + losses
    win_pct = f"{100 * wins / played:.1f}%" if played > 0 else "N/A"
    parts = [f"Team stats for '{team}'"]
    if competition:
        parts[0] += f" in {competition}"
    if season:
        parts[0] += f" ({season})"
    if home_only:
        parts[0] += " [home]"
    elif away_only:
        parts[0] += " [away]"

    parts += [
        f"  Played: {played}",
        f"  Wins: {wins}, Draws: {draws}, Losses: {losses}",
        f"  Goals for: {int(goals_for)}, Goals against: {int(goals_against)}",
        f"  Win rate: {win_pct}",
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Tool: get_competition_standings
# ---------------------------------------------------------------------------

@mcp.tool()
def get_competition_standings(
    season: int,
    competition: str = "Brasileirao",
    top_n: int = 20,
) -> str:
    """Calculate and return competition standings for a given season.

    Args:
        season: Season year, e.g. 2019.
        competition: Competition name ("Brasileirao", "Copa do Brasil", "Libertadores").
        top_n: Number of teams to show.
    """
    df = get_matches()
    df = df[df["season"] == season]
    df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
    df = df.dropna(subset=["home_goal", "away_goal"])

    if df.empty:
        return f"No matches found for {competition} {season}."

    table: dict[str, dict] = {}

    def _record(team_norm: str) -> dict:
        if team_norm not in table:
            table[team_norm] = dict(name=team_norm, p=0, w=0, d=0, l=0, gf=0, ga=0, pts=0)
        return table[team_norm]

    for _, r in df.iterrows():
        hn, an = r["home_norm"], r["away_norm"]
        hg, ag = int(r["home_goal"]), int(r["away_goal"])
        h = _record(hn)
        a = _record(an)

        h["p"] += 1
        a["p"] += 1
        h["gf"] += hg
        h["ga"] += ag
        a["gf"] += ag
        a["ga"] += hg

        if hg > ag:
            h["w"] += 1; h["pts"] += 3
            a["l"] += 1
        elif hg == ag:
            h["d"] += 1; h["pts"] += 1
            a["d"] += 1; a["pts"] += 1
        else:
            a["w"] += 1; a["pts"] += 3
            h["l"] += 1

    rows = sorted(table.values(), key=lambda x: (-x["pts"], -(x["gf"] - x["ga"]), -x["gf"]))
    lines = [f"{competition} {season} Standings (top {min(top_n, len(rows))}):", ""]
    for i, r in enumerate(rows[:top_n], 1):
        gd = r["gf"] - r["ga"]
        lines.append(
            f"  {i:>2}. {r['name']:<30} {r['pts']:>3} pts  "
            f"{r['w']}W {r['d']}D {r['l']}L  GF:{r['gf']} GA:{r['ga']} GD:{gd:+d}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: search_players
# ---------------------------------------------------------------------------

@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> str:
    """Search FIFA player database.

    Args:
        name: Partial player name search.
        nationality: Player nationality, e.g. "Brazilian".
        club: Club name (partial match), e.g. "Flamengo".
        position: Position filter, e.g. "GK", "ST", "CB".
        min_overall: Minimum FIFA overall rating.
        limit: Max results to return.
    """
    df = get_fifa()

    if name:
        df = df[df["name_norm"].str.contains(name.lower(), na=False)]

    if nationality:
        df = df[df["Nationality"].str.lower().str.contains(nationality.lower(), na=False)]

    if club:
        c_norm = normalize_team(club)
        df = df[df["club_norm"].str.contains(c_norm, na=False)]

    if position:
        df = df[df["Position"].str.upper().str.contains(position.upper(), na=False)]

    if min_overall is not None:
        df = df[df["Overall"] >= min_overall]

    if df.empty:
        return "No players found matching the criteria."

    df = df.sort_values("Overall", ascending=False)
    total = len(df)
    lines = [f"Found {total} player(s) (showing {min(limit, total)}, sorted by rating):"]
    for i, (_, r) in enumerate(df.head(limit).iterrows(), 1):
        age = int(r["Age"]) if pd.notna(r.get("Age")) else "?"
        overall = int(r["Overall"]) if pd.notna(r["Overall"]) else "?"
        pot = int(r["Potential"]) if pd.notna(r.get("Potential")) else "?"
        lines.append(
            f"  {i:>2}. {r['Name']:<25} Overall:{overall} Pot:{pot} "
            f"Pos:{r.get('Position','?'):<4} Age:{age} Club:{r.get('Club','?')}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_biggest_wins
# ---------------------------------------------------------------------------

@mcp.tool()
def get_biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    team: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Return the biggest winning margins in the dataset.

    Args:
        competition: Competition filter.
        season: Season filter.
        team: Only show wins by this team.
        limit: Number of results.
    """
    df = get_matches().dropna(subset=["home_goal", "away_goal"])

    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
    if season:
        df = df[df["season"] == season]
    if team:
        t_norm = normalize_team(team)
        df = df[
            df["home_norm"].str.contains(t_norm, na=False) |
            df["away_norm"].str.contains(t_norm, na=False)
        ]

    df = df.copy()
    df["margin"] = (df["home_goal"] - df["away_goal"]).abs()
    df = df[df["margin"] > 0].sort_values("margin", ascending=False)

    if df.empty:
        return "No matches found."

    lines = [f"Top {min(limit, len(df))} biggest wins:"]
    for i, (_, r) in enumerate(df.head(limit).iterrows(), 1):
        lines.append(f"  {i:>2}. {_fmt_match(r)}  (margin: {int(r['margin'])})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_overall_stats
# ---------------------------------------------------------------------------

@mcp.tool()
def get_overall_stats(
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    """Get aggregate statistics (avg goals, home win rate, etc.).

    Args:
        competition: Competition filter.
        season: Season filter.
    """
    df = get_matches().dropna(subset=["home_goal", "away_goal"])

    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
    if season:
        df = df[df["season"] == season]

    if df.empty:
        return "No matches found."

    total = len(df)
    total_goals = int(df["home_goal"].sum() + df["away_goal"].sum())
    avg_goals = total_goals / total if total else 0

    home_wins = int(((df["home_goal"] - df["away_goal"]) > 0).sum())
    draws = int(((df["home_goal"] - df["away_goal"]) == 0).sum())
    away_wins = int(((df["home_goal"] - df["away_goal"]) < 0).sum())

    seasons = sorted(df["season"].dropna().unique().astype(int).tolist())
    comps = df["competition"].dropna().unique().tolist()

    lines = ["Overall statistics:"]
    if competition:
        lines[0] += f" ({competition})"
    if season:
        lines[0] += f" [{season}]"
    lines += [
        f"  Total matches: {total}",
        f"  Total goals: {total_goals}",
        f"  Avg goals/match: {avg_goals:.2f}",
        f"  Home wins: {home_wins} ({100*home_wins/total:.1f}%)",
        f"  Draws: {draws} ({100*draws/total:.1f}%)",
        f"  Away wins: {away_wins} ({100*away_wins/total:.1f}%)",
        f"  Seasons covered: {seasons[0] if seasons else 'N/A'}–{seasons[-1] if seasons else 'N/A'}",
        f"  Competitions: {', '.join(sorted(set(comps)))}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_top_teams
# ---------------------------------------------------------------------------

@mcp.tool()
def get_top_teams(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    metric: str = "wins",
    limit: int = 10,
) -> str:
    """Rank teams by a metric (wins, goals, win_rate, away_wins).

    Args:
        competition: Competition filter.
        season: Season filter.
        metric: One of "wins", "goals", "win_rate", "away_wins".
        limit: Number of teams to show.
    """
    df = get_matches().dropna(subset=["home_goal", "away_goal"])

    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
    if season:
        df = df[df["season"] == season]

    if df.empty:
        return "No matches found."

    stats: dict[str, dict] = {}

    def _rec(t: str) -> dict:
        if t not in stats:
            stats[t] = dict(played=0, wins=0, draws=0, losses=0, goals=0, away_wins=0)
        return stats[t]

    for _, r in df.iterrows():
        hn, an = r["home_norm"], r["away_norm"]
        hg, ag = int(r["home_goal"]), int(r["away_goal"])
        h = _rec(hn)
        a = _rec(an)
        h["played"] += 1; h["goals"] += hg
        a["played"] += 1; a["goals"] += ag
        if hg > ag:
            h["wins"] += 1; a["losses"] += 1
        elif hg == ag:
            h["draws"] += 1; a["draws"] += 1
        else:
            a["wins"] += 1; a["away_wins"] += 1; h["losses"] += 1

    if metric == "win_rate":
        ranked = sorted(
            [(t, v) for t, v in stats.items() if v["played"] >= 5],
            key=lambda x: -x[1]["wins"] / max(x[1]["played"], 1),
        )
    elif metric == "away_wins":
        ranked = sorted(stats.items(), key=lambda x: -x[1]["away_wins"])
    elif metric == "goals":
        ranked = sorted(stats.items(), key=lambda x: -x[1]["goals"])
    else:  # wins
        ranked = sorted(stats.items(), key=lambda x: -x[1]["wins"])

    lines = [f"Top {min(limit, len(ranked))} teams by {metric}:"]
    for i, (team, v) in enumerate(ranked[:limit], 1):
        wr = f"{100*v['wins']/max(v['played'],1):.1f}%"
        lines.append(
            f"  {i:>2}. {team:<30} W:{v['wins']} D:{v['draws']} L:{v['losses']} "
            f"P:{v['played']} Goals:{v['goals']} WR:{wr}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: list_competitions
# ---------------------------------------------------------------------------

@mcp.tool()
def list_competitions() -> str:
    """List all competitions and seasons available in the dataset."""
    df = get_matches()
    grouped = df.groupby("competition")["season"].agg(
        lambda x: sorted(x.dropna().unique().astype(int).tolist())
    )
    lines = ["Available competitions and seasons:", ""]
    for comp, seasons in grouped.items():
        season_str = f"{seasons[0]}–{seasons[-1]}" if len(seasons) > 1 else str(seasons[0]) if seasons else "?"
        lines.append(f"  {comp}: {season_str} ({len(seasons)} seasons)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
