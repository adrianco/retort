"""Rendering of query results as readable text.

Context
-------
Every MCP tool returns two things: ``structuredContent`` (the raw dict from
:mod:`brazilian_soccer.queries`, for programmatic use) and a text block.  The
text block is what an LLM actually reads, so it is formatted to look like the
answer shapes in the specification -- match lists with dates and scores,
win/loss records, league tables with points, and so on.

Each ``format_*`` function takes the dict produced by the query function of the
same name and returns a plain-string answer.  Nothing here touches the graph.
"""

from __future__ import annotations

from typing import Any, Sequence

__all__ = ["FORMATTERS", "render"]


def _score_line(match: dict[str, Any]) -> str:
    """``2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)``"""
    date = match.get("date") or "date unknown"
    home, away = match["home_team"], match["away_team"]
    if match["home_goals"] is None or match["away_goals"] is None:
        score = "not played"
        core = f"{home} vs {away} ({score})"
    else:
        core = f"{home} {match['home_goals']}-{match['away_goals']} {away}"
    context = []
    comp = _competition_label(match.get("competition"))
    if comp:
        context.append(comp)
    if match.get("season"):
        context.append(str(match["season"]))
    if match.get("stage"):
        context.append(str(match["stage"]))
    elif match.get("round"):
        context.append(f"Round {match['round']}")
    suffix = f" ({', '.join(context)})" if context else ""
    return f"{date}: {core}{suffix}"


_COMPETITION_LABELS = {
    "serie-a": "Brasileirão",
    "serie-b": "Série B",
    "serie-c": "Série C",
    "copa-do-brasil": "Copa do Brasil",
    "libertadores": "Libertadores",
}


def _competition_label(slug: str | None) -> str:
    if not slug:
        return ""
    return _COMPETITION_LABELS.get(slug, slug)


def _notes(result: dict[str, Any]) -> str:
    notes = result.get("notes") or []
    if not notes:
        return ""
    return "\n\nNotes:\n" + "\n".join(f"- {note}" for note in notes)


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    """Render a fixed-width text table (Markdown pipe tables are noisier).

    Column alignment is decided from the data -- numeric columns are right
    aligned, including their header -- so league tables line up the way a
    reader expects.
    """
    widths = [len(str(h)) for h in headers]
    numeric = [True] * len(headers)
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(str(cell)))
            if not _looks_numeric(cell):
                numeric[index] = False

    def line(cells: Sequence[Any]) -> str:
        return "  ".join(
            str(cell).rjust(widths[i]) if numeric[i] else str(cell).ljust(widths[i])
            for i, cell in enumerate(cells)
        ).rstrip()

    out = [line(headers), "  ".join("-" * w for w in widths)]
    out.extend(line(row) for row in rows)
    return "\n".join(out)


def _looks_numeric(value: Any) -> bool:
    """True for numbers and for numeric strings such as ``"+49"`` or ``"57.9%"``."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    text = str(value).strip().lstrip("+-").rstrip("%")
    return bool(text) and text.replace(".", "", 1).isdigit()


# ---------------------------------------------------------------------------
# formatters
# ---------------------------------------------------------------------------

def format_find_matches(result: dict[str, Any]) -> str:
    query = result["query"]
    title_bits = []
    if query["team"] and query["opponent"]:
        title_bits.append(f"{query['team']} vs {query['opponent']}")
    elif query["team"]:
        venue = {"home": " (home)", "away": " (away)", "any": ""}[query["venue"]]
        title_bits.append(f"{query['team']}{venue} matches")
    else:
        title_bits.append("Matches")
    if query["season"]:
        title_bits.append(f"in {query['season']}")
    if query["competition"] != "All competitions":
        title_bits.append(f"- {query['competition']}")
    header = " ".join(title_bits)

    if not result["matches"]:
        return f"{header}: no matches found.{_notes(result)}"

    lines = [f"{header}: {result['total_matches']} match(es) found"]
    if result["returned"] < result["total_matches"]:
        lines[0] += f" (showing {result['returned']})"
    lines.append("")
    lines.extend(f"- {_score_line(m)}" for m in result["matches"])
    return "\n".join(lines) + _notes(result)


def format_head_to_head(result: dict[str, Any]) -> str:
    a, b = result["team_a"], result["team_b"]
    header = f"{a} vs {b}"
    if result.get("derby_name"):
        header += f" ({result['derby_name']} derby)"
    if result["total_matches"] == 0:
        return f"{header}: no meetings in the datasets.{_notes(result)}"

    summary = result["summary"]
    lines = [f"{header}:", ""]
    for match in result["matches"]:
        lines.append(f"- {_score_line(match)}")
    if result["returned"] < result["total_matches"]:
        lines.append(f"- ... ({result['total_matches'] - result['returned']} "
                     "more matches in dataset)")
    lines.append("")
    lines.append(
        f"Head-to-head in dataset: {a} {summary['team_a_wins']} wins, "
        f"{b} {summary['team_b_wins']} wins, {summary['draws']} draws")
    lines.append(f"Goals: {a} {summary['team_a_goals']} - "
                 f"{summary['team_b_goals']} {b}")
    if result["by_competition"]:
        breakdown = ", ".join(f"{c['competition']} {c['matches']}"
                              for c in result["by_competition"])
        lines.append(f"By competition: {breakdown}")
    if result.get("last_meeting"):
        lines.append(f"Most recent meeting: {_score_line(result['last_meeting'])}")
    return "\n".join(lines) + _notes(result)


def _record_block(title: str, record: dict[str, Any]) -> list[str]:
    return [
        f"{title}:",
        f"- Matches: {record['played']}",
        f"- Wins: {record['wins']}, Draws: {record['draws']}, "
        f"Losses: {record['losses']}",
        f"- Goals For: {record['goals_for']}, Goals Against: "
        f"{record['goals_against']} (GD {record['goal_difference']:+d})",
        f"- Win rate: {record['win_rate']}%  |  Points per game: "
        f"{record['points_per_game']}",
    ]


def format_team_stats(result: dict[str, Any]) -> str:
    scope = []
    if result["season"]:
        scope.append(str(result["season"]))
    if result["competition"] != "All competitions":
        scope.append(result["competition"])
    label = f" ({', '.join(scope)})" if scope else ""
    venue_word = {"home": " home", "away": " away", "all": ""}[result["venue"]]

    lines = _record_block(f"{result['team']}{venue_word} record{label}",
                          result["overall"])
    if result["venue"] == "all" and result["overall"]["played"]:
        lines.append("")
        lines.append(
            f"Home: {result['home']['wins']}W {result['home']['draws']}D "
            f"{result['home']['losses']}L "
            f"({result['home']['goals_for']}:{result['home']['goals_against']})"
        )
        lines.append(
            f"Away: {result['away']['wins']}W {result['away']['draws']}D "
            f"{result['away']['losses']}L "
            f"({result['away']['goals_for']}:{result['away']['goals_against']})"
        )
    biggest = result["overall"].get("biggest_win")
    if biggest:
        lines.append(f"Biggest win: {_score_line(biggest)}")
    if len(result.get("by_competition", [])) > 1:
        lines.append("")
        lines.append("By competition:")
        for row in result["by_competition"]:
            lines.append(f"- {row['competition']}: {row['played']} played, "
                         f"{row['wins']}W {row['draws']}D {row['losses']}L "
                         f"({row['win_rate']}% wins)")
    return "\n".join(lines) + _notes(result)


def format_team_profile(result: dict[str, Any]) -> str:
    lines = [f"{result['team']}"
             + (f" ({result['state']})" if result.get("state") else ""), ""]
    record = result["record"]
    lines.append(f"{result['total_matches']} matches in the datasets: "
                 f"{record['wins']}W {record['draws']}D {record['losses']}L, "
                 f"{record['goals_for']} scored / {record['goals_against']} conceded")
    lines.append("")
    lines.append("Competitions played:")
    for comp in result["competitions"]:
        lines.append(f"- {comp['competition']} ({comp['seasons']}): "
                     f"{comp['matches']} matches, {comp['win_rate']}% won")
    if result["most_played_opponents"]:
        lines.append("")
        lines.append("Most frequent opponents:")
        for opponent in result["most_played_opponents"][:5]:
            derby = f" [{opponent['derby']}]" if opponent.get("derby") else ""
            lines.append(f"- {opponent['opponent']}: {opponent['matches']} "
                         f"matches{derby}")
    if result["stadiums"]:
        venues = ", ".join(f"{v['venue']} ({v['matches']})" for v in result["stadiums"])
        lines.append("")
        lines.append(f"Stadiums in the data: {venues}")
    if result["fifa_squad_size"]:
        lines.append("")
        lines.append(f"FIFA 19 squad: {result['fifa_squad_size']} players")
        for player in result["fifa_squad_top_rated"]:
            lines.append(f"- {player['name']} - Overall: {player['overall']}, "
                         f"Position: {player['position']}")
    if result.get("spellings_in_data"):
        lines.append("")
        lines.append("Spellings in source data: "
                     + ", ".join(result["spellings_in_data"]))
    return "\n".join(lines) + _notes(result)


def format_standings(result: dict[str, Any]) -> str:
    header = f"{result['season']} {result['competition']} standings " \
             f"(calculated from {result['matches_played']} matches)"
    rows = []
    for row in result["table"]:
        marker = ""
        if result.get("champion") == row["team"]:
            marker = " - Champion"
        elif row["team"] in (result.get("relegated") or []):
            marker = " - Relegated"
        rows.append([
            row["position"], row["team"] + marker, row["played"], row["wins"],
            row["draws"], row["losses"], row["goals_for"], row["goals_against"],
            f"{row['goal_difference']:+d}", row["points"],
        ])
    table = _table(["#", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"], rows)
    return f"{header}\n\n{table}" + _notes(result)


def format_team_rankings(result: dict[str, Any]) -> str:
    scope = [result["competition"]]
    if result["season"]:
        scope.append(str(result["season"]))
    venue = {"home": "home", "away": "away", "all": "overall"}[result["venue"]]
    header = (f"Teams ranked by {result['metric'].replace('_', ' ')} "
              f"({venue}) - {', '.join(scope)}")
    rows = [[
        row["rank"], row["team"], row["matches"], row["wins"], row["draws"],
        row["losses"], row["goals_for"], row["goals_against"], row["points"],
        row["points_per_game"], f"{row['win_rate']}%",
    ] for row in result["rankings"]]
    if not rows:
        return f"{header}: no teams met the minimum of " \
               f"{result['min_matches']} matches.{_notes(result)}"
    table = _table(["#", "Team", "P", "W", "D", "L", "GF", "GA", "Pts", "PPG", "Win%"],
                   rows)
    return f"{header}\n\n{table}" + _notes(result)


def format_competition_stats(result: dict[str, Any]) -> str:
    scope = result["competition"]
    if result["season"]:
        scope += f" {result['season']}"
    elif result.get("seasons"):
        scope += f" {result['seasons']}"
    lines = [
        f"{scope} - aggregate statistics",
        "",
        f"Matches: {result['matches']}",
        f"Goals: {result['goals']} (home {result['home_goals']} / "
        f"away {result['away_goals']})",
        f"Average goals per match: {result['goals_per_match']}",
        f"Home win rate: {result['home_win_rate']}%  |  "
        f"Draws: {result['draw_rate']}%  |  Away wins: {result['away_win_rate']}%",
    ]
    if result["most_common_scorelines"]:
        common = ", ".join(f"{s['score']} ({s['count']})"
                           for s in result["most_common_scorelines"])
        lines.append(f"Most common scorelines: {common}")
    if result["top_scoring_teams"]:
        lines.append("")
        lines.append("Top scoring teams:")
        for index, team in enumerate(result["top_scoring_teams"], start=1):
            lines.append(f"{index}. {team['team']} - {team['goals']} goals")
    if len(result["by_season"]) > 1:
        lines.append("")
        lines.append("By season:")
        table = _table(
            ["Season", "Matches", "Goals", "G/match", "Home win %"],
            [[s["season"], s["matches"], s["goals"], s["goals_per_match"],
              s["home_win_rate"]] for s in result["by_season"]],
        )
        lines.append(table)
    return "\n".join(lines) + _notes(result)


def format_biggest_wins(result: dict[str, Any]) -> str:
    scope = result["competition"]
    if result["season"]:
        scope += f" {result['season']}"
    if result["team"]:
        header = f"Biggest wins by {result['team']} ({scope})"
    else:
        header = f"Biggest victories in {scope}"
    if not result["results"]:
        return f"{header}: nothing found.{_notes(result)}"
    lines = [header, ""]
    for index, match in enumerate(result["results"], start=1):
        lines.append(f"{index}. {_score_line(match)} - margin {match['margin']}")
    return "\n".join(lines) + _notes(result)


def format_compare_seasons(result: dict[str, Any]) -> str:
    title = f"{result['competition']} season comparison"
    if result.get("team"):
        title += f" - {result['team']}"
    lines = [title, ""]
    for row in result["comparison"]:
        if not row.get("matches"):
            lines.append(f"{row['season']}: no data")
            continue
        lines.append(f"{row['season']}: {row['matches']} matches, "
                     f"{row['goals']} goals ({row['goals_per_match']}/match), "
                     f"home wins {row['home_win_rate']}%, draws {row['draw_rate']}%")
        if row.get("champion"):
            lines.append(f"    Champion: {row['champion']} "
                         f"(top three: {', '.join(row['top_three'])})")
        if row.get("team_record"):
            record = row["team_record"]
            lines.append(f"    {result['team']}: {record['wins']}W "
                         f"{record['draws']}D {record['losses']}L, "
                         f"{record['points']} pts, {record['win_rate']}% wins")
    return "\n".join(lines) + _notes(result)


def format_find_derbies(result: dict[str, Any]) -> str:
    scope = result["competition"]
    if result["season"]:
        scope += f" {result['season']}"
    if result["total_matches"] == 0:
        return (f"No classic derbies found in {scope}."
                f"\nKnown rivalries: {', '.join(result['known_rivalries'])}"
                + _notes(result))
    lines = [f"Derbies in {scope}: {result['total_matches']} match(es)", ""]
    for row in result["derbies"]:
        lines.append(f"- {row['derby']}: {row['matches']}")
    lines.append("")
    for match in result["matches"]:
        lines.append(f"- [{match['derby']}] {_score_line(match)}")
    return "\n".join(lines) + _notes(result)


def format_search_players(result: dict[str, Any]) -> str:
    query = result["query"]
    bits = []
    if query["nationality"]:
        bits.append(query["nationality"])
    if query["position"]:
        bits.append(query["position"])
    bits.append("players")
    if query["club"]:
        bits.append(f"at {query['club']}")
    if query["name"]:
        bits.append(f"matching {query['name']!r}")
    if query.get("min_overall"):
        bits.append(f"rated {query['min_overall']}+")
    header = " ".join(bits)
    header = header[:1].upper() + header[1:]

    if not result["players"]:
        return f"{header}: no players found.{_notes(result)}"
    lines = [f"{header} - {result['total_players']} found"
             + (f" (showing {result['returned']})"
                if result["returned"] < result["total_players"] else ""), ""]
    for index, player in enumerate(result["players"], start=1):
        club = player["club"] or "no club"
        lines.append(f"{index}. {player['name']} - Overall: {player['overall']}, "
                     f"Position: {player['position'] or 'n/a'}, Club: {club}"
                     + (f", Age: {player['age']}" if player.get("age") else ""))
    return "\n".join(lines) + _notes(result)


def format_player_profile(result: dict[str, Any]) -> str:
    player = result["player"]
    lines = [
        f"{player['name']}",
        "",
        f"- Nationality: {player['nationality']}   Age: {player['age']}",
        f"- Club: {player['club'] or 'none'}   Position: "
        f"{player['position'] or 'n/a'}   Shirt: {player['jersey_number'] or 'n/a'}",
        f"- Overall: {player['overall']}   Potential: {player['potential']}",
        f"- Value: {player['value']}   Wage: {player['wage']}",
        f"- Height: {player['height']}   Weight: {player['weight']}   "
        f"Preferred foot: {player['preferred_foot']}",
    ]
    if player.get("best_skills"):
        skills = ", ".join(f"{s['attribute']} {s['rating']}"
                           for s in player["best_skills"])
        lines.append(f"- Best attributes: {skills}")
    if player.get("club_in_match_data"):
        lines.append(f"- This club appears in the match datasets with "
                     f"{player['club_matches_in_dataset']} fixtures.")
    if result["other_matches"]:
        others = ", ".join(f"{p['name']} ({p['club'] or 'no club'})"
                           for p in result["other_matches"])
        lines.append(f"- Other players matching that name: {others}")
    return "\n".join(lines) + _notes(result)


def format_club_squad(result: dict[str, Any]) -> str:
    header = f"{result['club']} - FIFA 19 squad"
    if not result["players"]:
        return f"{header}: no players in the dataset.{_notes(result)}"
    lines = [
        f"{header} ({result['squad_size']} players, "
        f"average rating {result['average_overall']}, "
        f"average age {result['average_age']})",
        "",
    ]
    for index, player in enumerate(result["players"], start=1):
        lines.append(f"{index}. {player['name']} - Overall: {player['overall']}, "
                     f"Potential: {player['potential']}, Position: "
                     f"{player['position'] or 'n/a'}, Age: {player['age']}")
    groups = ", ".join(f"{g['group']} {g['players']}"
                       for g in result["by_position_group"])
    lines.append("")
    lines.append(f"By position: {groups}")
    lines.append(f"Brazilian players in squad: {result['brazilian_players']}")
    return "\n".join(lines) + _notes(result)


def format_brazilian_players_by_club(result: dict[str, Any]) -> str:
    lines = [f"Brazilian players in the FIFA dataset: "
             f"{result['total_brazilian_players']} across {result['clubs']} clubs",
             "",
             "Top-rated Brazilian players:"]
    for index, player in enumerate(result["top_rated"], start=1):
        lines.append(f"{index}. {player['name']} - Overall: {player['overall']}, "
                     f"Position: {player['position']}, Club: {player['club']}")
    lines.append("")
    lines.append("Brazilian players at clubs that also appear in the match data:")
    for row in result["at_clubs_present_in_match_data"]:
        lines.append(f"- {row['club']}: {row['players']} players "
                     f"(avg rating: {row['average_overall']})")
    return "\n".join(lines) + _notes(result)


def format_resolve_team(result: dict[str, Any]) -> str:
    if not result["matched"]:
        text = f"{result['query']!r}: {result['message']}"
        if result["suggestions"]:
            text += "\nClosest clubs: " + ", ".join(result["suggestions"])
        return text
    team = result["team"]
    lines = [
        f"{result['query']!r} resolves to {team['name']}"
        + (f" ({team['state']})" if team["state"] else ""),
        f"- Canonical id: {team['slug']}",
        f"- Matches in data: {result['matches_in_data']} ({result['seasons']})",
        f"- Competitions: {', '.join(result['competitions'])}",
        f"- Spellings seen in source files: {', '.join(team['aliases'])}",
    ]
    if result["fifa_squad_size"]:
        lines.append(f"- FIFA 19 squad size: {result['fifa_squad_size']}")
    if result["other_clubs_with_similar_names"]:
        lines.append("- Careful, similar names: "
                     + ", ".join(result["other_clubs_with_similar_names"]))
    return "\n".join(lines)


def format_dataset_summary(result: dict[str, Any]) -> str:
    lines = ["Brazilian Soccer knowledge graph", ""]
    lines.append("Source files:")
    for entry in result["files"]:
        lines.append(f"- {entry['file']}: {entry['rows']} rows - "
                     f"{entry['description']}")
    matches = result["matches"]
    lines.append("")
    lines.append(f"{matches['source_rows']} match rows merged into "
                 f"{matches['unique']} unique fixtures "
                 f"({matches['merged_duplicates']} duplicates folded in).")
    lines.append("")
    lines.append("Competitions:")
    for comp in result["competitions"]:
        lines.append(f"- {comp['name']}: {comp['matches']} matches, "
                     f"{comp['seasons']}, {comp['teams']} clubs")
    lines.append("")
    lines.append(f"Clubs: {result['teams']} ({result['curated_teams']} curated)")
    lines.append(f"Players: {result['players']} "
                 f"({result['brazilian_players']} Brazilian)")
    lines.append(f"Graph built in {result['build_seconds']}s")
    return "\n".join(lines) + _notes(result)


#: Tool name -> formatter, consumed by :mod:`brazilian_soccer.tools`.
FORMATTERS = {
    "find_matches": format_find_matches,
    "head_to_head": format_head_to_head,
    "team_stats": format_team_stats,
    "team_profile": format_team_profile,
    "standings": format_standings,
    "team_rankings": format_team_rankings,
    "competition_stats": format_competition_stats,
    "biggest_wins": format_biggest_wins,
    "compare_seasons": format_compare_seasons,
    "find_derbies": format_find_derbies,
    "search_players": format_search_players,
    "player_profile": format_player_profile,
    "club_squad": format_club_squad,
    "brazilian_players_by_club": format_brazilian_players_by_club,
    "resolve_team": format_resolve_team,
    "dataset_summary": format_dataset_summary,
}


def render(tool_name: str, result: dict[str, Any]) -> str:
    """Render *result* for *tool_name*, falling back to a generic dump."""
    formatter = FORMATTERS.get(tool_name)
    if formatter is None:  # pragma: no cover - every tool has a formatter
        import json
        return json.dumps(result, indent=2, ensure_ascii=False, default=str)
    return formatter(result)
