"""Rendering of query results as text for an LLM to read back to a user.

The MCP tools return these strings; the shapes follow the "example answer
format" blocks of the specification (match lists with dates and scores,
head-to-head tallies, standings tables with points and records).
"""

from __future__ import annotations

def _score_line(match: dict) -> str:
    """``2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A Round 22)``."""
    when = match.get("date") or "date unknown"
    home, away = match["home_team"], match["away_team"]
    if match.get("score"):
        core = f"{home} {match['home_goals']}-{match['away_goals']} {away}"
    else:
        core = f"{home} vs {away} (not played / no score in data)"
    context = [match["competition"]]
    if match.get("stage"):
        context.append(str(match["stage"]).title())
    elif match.get("round"):
        context.append(f"Round {match['round']}")
    if match.get("season"):
        context.append(str(match["season"]))
    return f"- {when}: {core} ({' '.join(context)})"


def format_matches(result: dict) -> str:
    query = result["query"]
    title_parts = []
    if query.get("team") and query.get("opponent"):
        title_parts.append(f"{query['team']} vs {query['opponent']}")
    elif query.get("team"):
        title_parts.append(f"{query['team']} matches")
    else:
        title_parts.append("Matches")
    if query.get("competition"):
        title_parts.append(f"in {query['competition']}")
    if query.get("season"):
        title_parts.append(f"({query['season']})")
    if query.get("venue") and query["venue"] != "any":
        title_parts.append(f"[{query['venue']} only]")

    header = " ".join(title_parts)
    if not result["matches"]:
        return f"{header}:\nNo matches found in the dataset for those filters."

    lines = [f"{header}: {result['total']} match(es) found, showing "
             f"{result['returned']}", ""]
    lines += [_score_line(m) for m in result["matches"]]
    if result["total"] > result["returned"]:
        lines.append(f"- ... ({result['total'] - result['returned']} more in dataset)")
    return "\n".join(lines)


def format_head_to_head(result: dict) -> str:
    a, b = result["team_a"], result["team_b"]
    if result["total_matches"] == 0:
        return f"No {a} vs {b} matches in the dataset."
    lines = [f"{a} vs {b}: {result['total_matches']} meetings in the dataset"]
    if result.get("competition"):
        lines[0] += f" ({result['competition']})"
    lines.append("")
    lines += [_score_line(m) for m in result["matches"]]
    remaining = result["total_matches"] - len(result["matches"])
    if remaining > 0:
        lines.append(f"- ... ({remaining} more meetings in dataset)")
    lines.append("")
    lines.append(
        f"Head-to-head: {a} {result['team_a_wins']} wins, "
        f"{b} {result['team_b_wins']} wins, {result['draws']} draws"
    )
    lines.append(f"Goals: {a} {result['team_a_goals']} - "
                 f"{result['team_b_goals']} {b}")
    if result.get("by_competition"):
        breakdown = ", ".join(f"{comp}: {count}"
                              for comp, count in result["by_competition"].items())
        lines.append(f"By competition: {breakdown}")
    return "\n".join(lines)


def format_team_stats(result: dict) -> str:
    scope = []
    if result.get("season"):
        scope.append(str(result["season"]))
    if result.get("competition"):
        scope.append(result["competition"])
    if result.get("venue") and result["venue"] != "any":
        scope.append(f"{result['venue']} matches")
    suffix = f" ({', '.join(scope)})" if scope else " (all data)"

    if result["matches"] == 0:
        return f"{result['team']} record{suffix}: no matches in the dataset."

    lines = [
        f"{result['team']} record{suffix}:",
        f"- Matches: {result['matches']}",
        f"- Wins: {result['wins']}, Draws: {result['draws']}, "
        f"Losses: {result['losses']}",
        f"- Goals For: {result['goals_for']}, Goals Against: "
        f"{result['goals_against']} (GD {result['goal_difference']:+d})",
        f"- Points: {result['points']} ({result['points_per_match']} per match)",
        f"- Win rate: {result['win_rate']}%",
    ]
    if result.get("biggest_win"):
        lines.append(f"- Biggest result: {_score_line(result['biggest_win'])[2:]}")
    if result.get("competitions"):
        lines.append(f"- Competitions: {', '.join(result['competitions'])}")
    return "\n".join(lines)


def format_team_profile(result: dict) -> str:
    lines = [
        f"{result['team']} ({result.get('state') or result['country']})",
        f"- Matches in dataset: {result['matches']} "
        f"({result['first_match']} to {result['last_match']})",
        f"- Overall: {result['overall']['wins']}W {result['overall']['draws']}D "
        f"{result['overall']['losses']}L, "
        f"{result['overall']['goals_for']}-{result['overall']['goals_against']} goals",
        "",
        "By competition:",
    ]
    for competition, row in result["competitions"].items():
        seasons = row["seasons"]
        span = f"{seasons[0]}-{seasons[-1]}" if seasons else "n/a"
        lines.append(
            f"- {competition} ({span}): {row['matches']} matches, "
            f"{row['wins']}W {row['draws']}D {row['losses']}L, "
            f"{row['points']} pts"
        )
    if result["most_played_opponents"]:
        lines.append("")
        lines.append("Most played opponents: " + ", ".join(
            f"{row['team']} ({row['matches']})"
            for row in result["most_played_opponents"]
        ))
    if result["squad_size_in_fifa_data"]:
        top = result["top_rated_player"]
        lines.append(
            f"FIFA squad data: {result['squad_size_in_fifa_data']} players"
            + (f", best {top['name']} ({top['overall']})" if top else "")
        )
    return "\n".join(lines)


def format_standings(result: dict) -> str:
    if not result["table"]:
        return (f"No match data for {result['competition']} {result['season']}, "
                f"so no table can be calculated.")
    status = "Final" if result["complete"] else "Partial"
    caveat = ""
    if result.get("missing_matches"):
        caveat = (f"; {result['missing_matches']} of "
                  f"{result['expected_matches']} fixtures missing from the "
                  f"data, so no champion is declared")
    lines = [
        f"{result['season']} {result['competition']} {status} Standings "
        f"(calculated from {result['matches']} matches in the dataset{caveat}):",
        "",
    ]
    for row in result["table"]:
        note = f" - {row['note']}" if row.get("note") else ""
        lines.append(
            f"{row['position']:>2}. {row['team']} - {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L) "
            f"GF {row['goals_for']} GA {row['goals_against']} "
            f"GD {row['goal_difference']:+d}{note}"
        )
    if result.get("relegated"):
        lines.append("")
        lines.append(f"Relegated: {', '.join(result['relegated'])}")
    if result.get("excluded_teams"):
        lines.append("")
        lines.append("Excluded as mislabelled in the source data: "
                     + ", ".join(result["excluded_teams"]))
    return "\n".join(lines)


def format_players(result: dict) -> str:
    query = {k: v for k, v in result["query"].items() if v}
    scope = ", ".join(f"{k}={v}" for k, v in query.items() if k != "sort_by")
    header = f"Players ({scope})" if scope else "Players"
    if not result["players"]:
        return f"{header}: no players in the FIFA dataset match that search."
    lines = [f"{header}: {result['total']} found, showing {result['returned']}", ""]
    for index, player in enumerate(result["players"], start=1):
        lines.append(
            f"{index}. {player['name']} - Overall: {player['overall']}, "
            f"Position: {player['position']}, Club: {player['club']}, "
            f"Age: {player['age']}, Nationality: {player['nationality']}"
        )
    return "\n".join(lines)


def format_player_profile(result: dict) -> str:
    if not result["found"]:
        message = (f"No player named '{result['query']}' in the FIFA dataset "
                   f"(it is a single-season snapshot and omits many players).")
        if result.get("alternatives"):
            message += "\nSimilar names: " + ", ".join(result["alternatives"])
        return message
    player = result["player"]
    lines = [
        f"{player['name']} - {player['nationality']}, age {player['age']}",
        f"- Club: {player['club'] or 'unknown'}"
        + (f" (#{player['jersey_number']})" if player["jersey_number"] else ""),
        f"- Position: {player['position']}, Overall: {player['overall']}, "
        f"Potential: {player['potential']}",
        f"- Physical: {player['height'] or '?'} / {player['weight'] or '?'}, "
        f"preferred foot {player['preferred_foot'] or '?'}",
        f"- Value: {player['value'] or 'n/a'}, Wage: {player['wage'] or 'n/a'}",
    ]
    skills = result.get("player", {}).get("skills") or {}
    if skills:
        best = list(skills.items())[:6]
        lines.append("- Top attributes: "
                     + ", ".join(f"{name} {value}" for name, value in best))
    context = result.get("club_context")
    if context:
        lines += [
            "",
            f"Club in match data - {context['team']}: {context['matches']} matches, "
            f"{context['wins']}W {context['draws']}D {context['losses']}L "
            f"across {', '.join(context['competitions'])}",
            f"Most recent: {_score_line(context['last_match'])[2:]}",
        ]
    if result.get("alternatives"):
        lines.append("")
        lines.append("Other name matches: " + ", ".join(result["alternatives"]))
    return "\n".join(lines)


def format_club_squad(result: dict) -> str:
    if not result["players"]:
        return (f"No FIFA player records for '{result['club']}' "
                f"(the FIFA dataset does not license every Brazilian club).")
    lines = [
        f"{result['club']} squad in FIFA data: {result['squad_size']} players, "
        f"average rating {result['average_overall']}",
        "",
    ]
    for index, player in enumerate(result["players"], start=1):
        lines.append(
            f"{index}. {player['name']} - Overall: {player['overall']}, "
            f"Position: {player['position']}, Age: {player['age']}, "
            f"{player['nationality']}"
        )
    return "\n".join(lines)


def format_players_by_club(result: dict) -> str:
    lines = [
        f"{result['nationality']} players by club "
        f"({result['total_players']} players across {result['clubs']} clubs "
        f"that also appear in the match data):",
        "",
    ]
    for row in result["rows"]:
        lines.append(
            f"- {row['club']}: {row['players']} players "
            f"(avg rating: {row['average_overall']}), best: {row['best_player']}"
        )
    return "\n".join(lines)


def format_competition_summary(result: dict) -> str:
    scope = f" {result['season']}" if result.get("season") else ""
    seasons = result["seasons"]
    span = f"{seasons[0]}-{seasons[-1]}" if seasons else "n/a"
    lines = [
        f"{result['competition']}{scope}:",
        f"- Matches: {result['matches']} ({result['played']} with scores), "
        f"seasons {span}",
        f"- Teams: {result['teams']}",
        f"- Goals: {result['goals']} ({result['goals_per_match']} per match)",
        f"- Home wins: {result['home_win_rate']}%, draws: {result['draw_rate']}%, "
        f"away wins: {result['away_win_rate']}%",
    ]
    if result["top_scoring_teams"]:
        lines.append("- Top scoring teams: " + ", ".join(
            f"{row['team']} ({row['goals']})" for row in result["top_scoring_teams"]
        ))
    return "\n".join(lines)


def format_rankings(result: dict) -> str:
    scope = []
    if result.get("competition"):
        scope.append(result["competition"])
    if result.get("season"):
        scope.append(str(result["season"]))
    if result["venue"] != "any":
        scope.append(f"{result['venue']} matches only")
    header = (f"Teams ranked by {result['metric'].replace('_', ' ')}"
              + (f" ({', '.join(scope)})" if scope else " (all data)")
              + f", minimum {result['min_matches']} matches:")
    if not result["rows"]:
        return header + "\n(no clubs meet that filter)"
    metric_key = result["metric"]
    lines = [header, ""]
    for index, row in enumerate(result["rows"], start=1):
        value = row.get(metric_key)
        suffix = "%" if metric_key == "win_rate" else ""
        lines.append(
            f"{index}. {row['team']} - {metric_key.replace('_', ' ')}: "
            f"{value}{suffix} | {row['points']} pts from {row['matches']} "
            f"matches ({row['wins']}W {row['draws']}D {row['losses']}L), "
            f"GF {row['goals_for']} GA {row['goals_against']}"
        )
    return "\n".join(lines)


def format_biggest_wins(result: dict) -> str:
    scope = []
    if result.get("team"):
        scope.append(result["team"])
    if result.get("competition"):
        scope.append(result["competition"])
    if result.get("season"):
        scope.append(str(result["season"]))
    header = "Biggest victories" + (f" ({', '.join(scope)})" if scope else "") + ":"
    if not result["matches"]:
        return header + "\n(no matches in the dataset for those filters)"
    lines = [header, ""]
    for index, match in enumerate(result["matches"], start=1):
        lines.append(f"{index}. {_score_line(match)[2:]} [margin {match['margin']}]")
    return "\n".join(lines)


def format_derbies(result: dict) -> str:
    if not result["matches"]:
        return "No derby matches found for those filters."
    scope = []
    if result.get("season"):
        scope.append(str(result["season"]))
    if result.get("competition"):
        scope.append(result["competition"])
    lines = [f"Derbies{' (' + ', '.join(scope) + ')' if scope else ''}: "
             f"{result['total']} matches", ""]
    for match in result["matches"]:
        lines.append(f"{_score_line(match)} [{match['derby']}]")
    return "\n".join(lines)


def format_home_away(result: dict) -> str:
    home, away = result["home"], result["away"]
    scope = []
    if result.get("season"):
        scope.append(str(result["season"]))
    if result.get("competition"):
        scope.append(result["competition"])
    lines = [f"{result['team']} home vs away"
             f"{' (' + ', '.join(scope) + ')' if scope else ''}:", ""]
    for label, row in (("Home", home), ("Away", away)):
        lines.append(
            f"{label}: {row['matches']} matches, {row['wins']}W {row['draws']}D "
            f"{row['losses']}L, {row['goals_for']}-{row['goals_against']} goals, "
            f"win rate {row['win_rate']}%"
        )
    return "\n".join(lines)


#: Group stages run to dozens of matches; long lists are trimmed per stage.
MATCHES_PER_STAGE = 12


def format_bracket(result: dict) -> str:
    if not result["stages"]:
        return (f"No {result['competition']} matches for {result['season']} "
                f"in the dataset.")
    lines = [f"{result['season']} {result['competition']} "
             f"({result['matches']} matches):", ""]
    for stage, matches in result["stages"].items():
        lines.append(f"{stage.title()} ({len(matches)} matches):")
        lines += [_score_line(m) for m in matches[:MATCHES_PER_STAGE]]
        if len(matches) > MATCHES_PER_STAGE:
            lines.append(f"- ... ({len(matches) - MATCHES_PER_STAGE} more)")
        lines.append("")
    return "\n".join(lines).strip()


def format_competitions(result: dict) -> str:
    summary = result["summary"]
    lines = [
        f"Knowledge graph: {summary['teams']} teams, {summary['matches']} matches, "
        f"{summary['players']} players "
        f"({summary['nodes']} nodes / {summary['edges']} edges), "
        f"{summary['first_match']} to {summary['last_match']}",
        "",
        "Competitions:",
    ]
    for row in result["competitions"]:
        lines.append(
            f"- {row['competition']}: {row['matches']} matches, seasons "
            f"{row['first_season']}-{row['last_season']}"
        )
    lines.append("")
    lines.append("Source files: " + ", ".join(
        f"{name} ({count} rows)" for name, count in summary["sources"].items()
    ))
    return "\n".join(lines)


def format_overall_statistics(result: dict) -> str:
    return "\n".join([
        "Dataset-wide statistics:",
        f"- Matches with scores: {result['played_matches']} of {result['matches']}",
        f"- Total goals: {result['total_goals']}",
        f"- Average goals per match: {result['goals_per_match']}",
        f"- Home win rate: {result['home_win_rate']}%, draws {result['draw_rate']}%",
        f"- Teams: {result['teams']}, players: {result['players']}",
        f"- Coverage: {result['coverage']['first_match']} to "
        f"{result['coverage']['last_match']}",
        f"- Competitions: {', '.join(result['competitions'])}",
    ])


def format_last_meeting(result: dict) -> str:
    if not result["found"]:
        return (f"No completed {result['team_a']} vs {result['team_b']} match "
                f"in the dataset.")
    match = result["match"]
    return "\n".join([
        f"{result['team_a']} last played {result['team_b']} on {match['date']}:",
        _score_line(match),
        f"Total meetings in dataset: {result['total_meetings']}",
    ])


def format_compare_teams(result: dict) -> str:
    return "\n\n".join([
        format_team_stats(result["team_a"]),
        format_team_stats(result["team_b"]),
        format_head_to_head(result["head_to_head"]),
    ])


def format_compare_seasons(result: dict) -> str:
    if not result["seasons"]:
        return f"{result['competition']}: no seasons given to compare."
    lines = [f"{result['competition']} season comparison:", ""]
    for row in result["seasons"]:
        lines.append(
            f"- {row['season']}: {row['played']} matches, {row['goals']} goals "
            f"({row['goals_per_match']}/match), home wins {row['home_win_rate']}%, "
            f"top scorers {row['top_scoring_teams'][0]['team'] if row['top_scoring_teams'] else 'n/a'}"
        )
    return "\n".join(lines)


def format_teams(result: dict) -> str:
    if not result["teams"]:
        return f"No clubs matching '{result['query']}'."
    lines = [f"Clubs matching '{result['query'] or 'all'}': {result['total']}", ""]
    for team in result["teams"]:
        location = team["state"] or team["country"]
        if location == "Unknown":
            location = "FIFA player data only"
        lines.append(f"- {team['name']} ({location}) - {team['matches']} matches "
                     f"[id: {team['team_id']}]")
    return "\n".join(lines)
