"""Rendering of query results as text for an LLM or a terminal.

Context
-------
MCP tools return text, so every dictionary produced by
:mod:`brazilian_soccer.queries` gets a formatter here.  The layouts deliberately
follow the answer formats in the specification -- a match list reads

    - 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)

and a table repeats the "1. Flamengo - 90 pts (28W, 6D, 4L) - Champion" shape --
so a model can quote the output back to the user with no further massaging.

Formatters never raise on partial data: missing scores render as ``vs``, missing
rounds are dropped, and an ``{"error": ...}`` payload becomes a short message
plus the suggestions that came with it.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

__all__ = [
    "format_result",
    "format_matches",
    "format_head_to_head",
    "format_team_stats",
    "format_team_profile",
    "format_rankings",
    "format_players",
    "format_player_profile",
    "format_team_squad",
    "format_standings",
    "format_bracket",
    "format_competition_stats",
    "format_biggest_wins",
    "format_derbies",
    "format_compare_seasons",
    "format_search_teams",
    "format_overview",
]


def _error(result: Mapping[str, Any]) -> str | None:
    if "error" not in result:
        return None
    lines = [str(result["error"])]
    suggestions = result.get("suggestions") or []
    if suggestions:
        lines.append("Did you mean: " + ", ".join(str(item) for item in suggestions[:10]) + "?")
    return "\n".join(lines)


def _score(match: Mapping[str, Any]) -> str:
    if match.get("home_goals") is None or match.get("away_goals") is None:
        return f"{match['home_team']} vs {match['away_team']} (no score in dataset)"
    return (
        f"{match['home_team']} {match['home_goals']}-{match['away_goals']} {match['away_team']}"
    )


def _context(match: Mapping[str, Any]) -> str:
    bits = [str(match.get("competition") or "")]
    if match.get("season"):
        bits[0] = f"{bits[0]} {match['season']}"
    if match.get("stage"):
        bits.append(str(match["stage"]))
    elif match.get("round") is not None:
        bits.append(f"Round {match['round']}")
    if match.get("venue"):
        bits.append(str(match["venue"]))
    return ", ".join(bit for bit in bits if bit)


def match_line(match: Mapping[str, Any], prefix: str = "- ") -> str:
    """``- 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A 2023, Round 22)``"""
    when = match.get("date") or "date unknown"
    context = _context(match)
    return f"{prefix}{when}: {_score(match)}" + (f" ({context})" if context else "")


def _record_line(record: Mapping[str, Any]) -> str:
    return (
        f"{record['played']} matches, {record['wins']}W {record['draws']}D {record['losses']}L, "
        f"{record['goals_for']} scored / {record['goals_against']} conceded "
        f"(GD {record['goal_difference']:+d}), {record['points']} pts, "
        f"win rate {record['win_rate']}%"
    )


def _bullets(items: Sequence[str]) -> str:
    return "\n".join(items)


# --------------------------------------------------------------------------
# Matches
# --------------------------------------------------------------------------


def format_matches(result: Mapping[str, Any]) -> str:
    error = _error(result)
    if error:
        return error

    title_bits = []
    if result.get("team") and result.get("opponent"):
        title_bits.append(f"{result['team']} vs {result['opponent']}")
    elif result.get("team"):
        title_bits.append(f"{result['team']} matches")
    else:
        title_bits.append("Matches")
    if result.get("competition"):
        title_bits.append(str(result["competition"]))
    if result.get("season"):
        title_bits.append(str(result["season"]))
    if result.get("home_away") in {"home", "away"}:
        title_bits.append(f"({result['home_away']} only)")
    title = " - ".join(title_bits)
    if result.get("derby"):
        title += f" [{result['derby']} derby]"

    lines = [f"{title}:"]
    matches = result.get("matches") or []
    if not matches:
        lines.append("No matches found for those filters.")
        return "\n".join(lines)

    lines.extend(match_line(match) for match in matches)
    total, returned = result.get("total", len(matches)), len(matches)
    if total > returned:
        lines.append(f"... {total - returned} more matches in the dataset (showing {returned}).")

    head_to_head = result.get("head_to_head")
    if head_to_head:
        lines.append(
            f"\nHead-to-head in dataset: {head_to_head['team_a']} {head_to_head['team_a_wins']} wins, "
            f"{head_to_head['team_b']} {head_to_head['team_b_wins']} wins, "
            f"{head_to_head['draws']} draws "
            f"(goals {head_to_head['team_a_goals']}-{head_to_head['team_b_goals']})."
        )
    elif result.get("record"):
        lines.append(f"\nRecord in this selection: {_record_line(result['record'])}.")
    return "\n".join(lines)


def format_head_to_head(result: Mapping[str, Any]) -> str:
    error = _error(result)
    if error:
        return error

    summary = result["summary"]
    header = f"{summary['team_a']} vs {summary['team_b']}"
    if result.get("derby"):
        header += f" ({result['derby']})"
    if result.get("competition"):
        header += f" - {result['competition']}"
    if result.get("season"):
        header += f" {result['season']}"

    lines = [
        f"{header}:",
        f"- Matches played: {summary['matches']}",
        f"- {summary['team_a']} wins: {summary['team_a_wins']}",
        f"- {summary['team_b']} wins: {summary['team_b_wins']}",
        f"- Draws: {summary['draws']}",
        f"- Goals: {summary['team_a_goals']}-{summary['team_b_goals']}",
    ]

    by_competition = result.get("by_competition") or {}
    if len(by_competition) > 1:
        lines.append("\nBy competition:")
        for name, record in by_competition.items():
            lines.append(
                f"- {name}: {record['played']} matches, {record['wins']}W {record['draws']}D "
                f"{record['losses']}L"
            )

    if result.get("last_meeting"):
        lines.append("\nMost recent meeting:")
        lines.append(match_line(result["last_meeting"]))
    if result.get("first_meeting"):
        lines.append("Earliest meeting in dataset:")
        lines.append(match_line(result["first_meeting"]))
    if result.get("biggest_win_team_a"):
        lines.append(f"\nBiggest {summary['team_a']} win:")
        lines.append(match_line(result["biggest_win_team_a"]))
    if result.get("biggest_win_team_b"):
        lines.append(f"Biggest {summary['team_b']} win:")
        lines.append(match_line(result["biggest_win_team_b"]))

    recent = result.get("recent_matches") or []
    if recent:
        lines.append("\nRecent meetings:")
        lines.extend(match_line(match) for match in recent)
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Teams
# --------------------------------------------------------------------------


def format_team_stats(result: Mapping[str, Any]) -> str:
    error = _error(result)
    if error:
        return error

    scope = []
    if result.get("season"):
        scope.append(str(result["season"]))
    if result.get("competition"):
        scope.append(str(result["competition"]))
    if result.get("home_away") in {"home", "away"}:
        scope.append(f"{result['home_away']} matches")
    title = f"{result['team']} record"
    if scope:
        title += " (" + ", ".join(scope) + ")"

    record = result["record"]
    lines = [
        f"{title}:",
        f"- Matches: {record['played']}",
        f"- Wins: {record['wins']}, Draws: {record['draws']}, Losses: {record['losses']}",
        f"- Goals For: {record['goals_for']}, Goals Against: {record['goals_against']} "
        f"(GD {record['goal_difference']:+d})",
        f"- Goals per match: {result.get('goals_per_match', 0)} scored, "
        f"{result.get('conceded_per_match', 0)} conceded",
        f"- Points: {record['points']}, win rate: {record['win_rate']}%",
        f"- Clean sheets: {result.get('clean_sheets', 0)}, "
        f"failed to score: {result.get('failed_to_score', 0)}",
    ]

    if result.get("home_away") not in {"home", "away"}:
        home, away = result.get("home", {}), result.get("away", {})
        if home.get("played") or away.get("played"):
            lines.append(
                f"- Home: {home.get('played', 0)} matches, {home.get('wins', 0)}W "
                f"{home.get('draws', 0)}D {home.get('losses', 0)}L "
                f"({home.get('win_rate', 0)}% wins)"
            )
            lines.append(
                f"- Away: {away.get('played', 0)} matches, {away.get('wins', 0)}W "
                f"{away.get('draws', 0)}D {away.get('losses', 0)}L "
                f"({away.get('win_rate', 0)}% wins)"
            )

    by_competition = result.get("by_competition") or {}
    if len(by_competition) > 1:
        lines.append("\nBy competition:")
        for name, value in by_competition.items():
            lines.append(
                f"- {name}: {value['played']} matches, {value['wins']}W {value['draws']}D "
                f"{value['losses']}L, {value['points']} pts"
            )

    if result.get("biggest_win"):
        lines.append("\nBiggest win: " + match_line(result["biggest_win"], prefix=""))
    if result.get("heaviest_defeat"):
        lines.append("Heaviest defeat: " + match_line(result["heaviest_defeat"], prefix=""))

    form = result.get("form") or []
    if form:
        lines.append("\nMost recent matches:")
        for match in form:
            lines.append(match_line(match, prefix=f"- [{match.get('outcome') or '?'}] "))
    return "\n".join(lines)


def format_team_profile(result: Mapping[str, Any]) -> str:
    error = _error(result)
    if error:
        return error

    record = result["record"]
    lines = [
        f"{result['team']} ({result.get('state') or result.get('country')}):",
        f"- Matches in dataset: {result['matches']} "
        f"({result.get('first_match')} to {result.get('last_match')})",
        f"- Overall: {_record_line(record)}",
        f"- Competitions: {', '.join(result.get('competitions') or []) or 'none'}",
    ]
    seasons = result.get("seasons") or []
    if seasons:
        lines.append(f"- Seasons: {seasons[0]}-{seasons[-1]} ({len(seasons)} seasons)")
    titles = result.get("serie_a_titles") or []
    if titles:
        lines.append(
            f"- Série A titles in dataset: {len(titles)} ({', '.join(str(y) for y in titles)})"
        )

    by_competition = result.get("by_competition") or {}
    if by_competition:
        lines.append("\nBy competition:")
        for name, value in by_competition.items():
            lines.append(
                f"- {name}: {value['played']} matches, {value['wins']}W {value['draws']}D "
                f"{value['losses']}L, {value['goals_for']}-{value['goals_against']} goals"
            )

    opponents = result.get("most_played_opponents") or []
    if opponents:
        lines.append(
            "\nMost frequent opponents: "
            + ", ".join(f"{item['team']} ({item['matches']})" for item in opponents)
        )

    variants = result.get("name_variants") or []
    if len(variants) > 1:
        lines.append("Name spellings unified: " + ", ".join(variants))

    squad = result.get("fifa_squad_top") or []
    if squad:
        lines.append(f"\nFIFA squad ({result.get('fifa_squad_size')} players), top rated:")
        for player in squad:
            lines.append(
                f"- {player['name']} - Overall: {player['overall']}, "
                f"Position: {player['position'] or 'n/a'}, Age: {player['age']}"
            )
    return "\n".join(lines)


def format_rankings(result: Mapping[str, Any]) -> str:
    error = _error(result)
    if error:
        return error

    scope = [str(result.get("competition") or "all competitions")]
    if result.get("season"):
        scope.append(str(result["season"]))
    if result.get("home_away") in {"home", "away"}:
        scope.append(f"{result['home_away']} matches only")
    lines = [
        f"Teams ranked by {result['metric']} ({', '.join(scope)}; "
        f"minimum {result['min_matches']} matches):"
    ]
    for row in result.get("ranking") or []:
        lines.append(
            f"{row['rank']}. {row['team']} - {row['value']} "
            f"({row['played']} matches, {row['wins']}W {row['draws']}D {row['losses']}L, "
            f"{row['goals_for']}-{row['goals_against']} goals)"
        )
    if not result.get("ranking"):
        lines.append("No teams matched those filters.")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Players
# --------------------------------------------------------------------------


def _player_line(player: Mapping[str, Any], index: int | None = None) -> str:
    prefix = f"{index}. " if index is not None else "- "
    bits = [f"Overall: {player.get('overall')}"]
    if player.get("position"):
        bits.append(f"Position: {player['position']}")
    if player.get("club"):
        bits.append(f"Club: {player['club']}")
    if player.get("nationality"):
        bits.append(f"Nationality: {player['nationality']}")
    if player.get("age"):
        bits.append(f"Age: {player['age']}")
    return f"{prefix}{player['name']} - " + ", ".join(bits)


def format_players(result: Mapping[str, Any]) -> str:
    error = _error(result)
    if error:
        return error

    filters = {key: value for key, value in (result.get("filters") or {}).items() if value}
    described = ", ".join(f"{key}={value}" for key, value in filters.items()) or "no filters"
    lines = [f"Players ({described}) - {result['total']} match(es):"]
    players = result.get("players") or []
    if not players:
        lines.append("No players matched.")
    for index, player in enumerate(players, start=1):
        lines.append(_player_line(player, index))
    if result.get("total", 0) > len(players):
        lines.append(f"... {result['total'] - len(players)} more (showing {len(players)}).")
    for note in result.get("notes") or []:
        lines.append(note)
    return "\n".join(lines)


def format_player_profile(result: Mapping[str, Any]) -> str:
    error = _error(result)
    if error:
        return error

    player = result["player"]
    lines = [
        f"{player['name']}:",
        f"- Overall: {player['overall']} (potential {player.get('potential')})",
        f"- Position: {player.get('position') or 'n/a'}, "
        f"shirt {player.get('jersey_number') or 'n/a'}",
        f"- Club: {player.get('club') or 'free agent'}",
        f"- Nationality: {player.get('nationality')}, age {player.get('age')}",
        f"- Value: {player.get('value') or 'n/a'}, wage: {player.get('wage') or 'n/a'}",
        f"- Physical: {player.get('height') or '?'} / {player.get('weight') or '?'}, "
        f"{player.get('preferred_foot') or '?'} footed",
    ]
    if player.get("club_in_match_data"):
        lines.append(f"- Club also appears in the match data as: {player['club_in_match_data']}")
    skills = player.get("top_skills") or []
    if skills:
        lines.append(
            "- Best attributes: "
            + ", ".join(f"{item['skill']} {item['rating']}" for item in skills)
        )
    others = result.get("other_matches") or []
    if others:
        lines.append(
            "\nOther players matching that name: "
            + ", ".join(f"{item['name']} ({item.get('club') or 'no club'})" for item in others)
        )
    return "\n".join(lines)


def format_team_squad(result: Mapping[str, Any]) -> str:
    error = _error(result)
    if error:
        return error

    lines = [f"{result['team']} - FIFA squad:"]
    if not result.get("players"):
        lines.append(result.get("note", "No players in fifa_data.csv for this club."))
        clubs = result.get("clubs_with_players") or []
        if clubs:
            lines.append("Brazilian clubs that do have FIFA players: " + ", ".join(clubs))
        return "\n".join(lines)

    lines.append(
        f"- Squad size: {result['squad_size']}, average rating: {result.get('average_overall')}, "
        f"average age: {result.get('average_age')}"
    )
    record = result.get("match_record")
    if record:
        lines.append(f"- Match record in dataset: {_record_line(record)}")
    lines.append("")
    for index, player in enumerate(result.get("players") or [], start=1):
        lines.append(_player_line(player, index))
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Competitions
# --------------------------------------------------------------------------


def format_standings(result: Mapping[str, Any]) -> str:
    error = _error(result)
    if error:
        return error

    lines = [
        f"{result['season']} {result['competition']} standings "
        f"(calculated from {result['matches']} matches):"
    ]
    champion = result.get("champion")
    relegated = set(result.get("relegated") or [])
    for row in result.get("table") or []:
        suffix = ""
        if champion and row["team"] == champion:
            suffix = " - Champion"
        elif row["team"] in relegated:
            suffix = " - Relegated"
        lines.append(
            f"{row['position']}. {row['team']} - {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L) "
            f"{row['goals_for']}:{row['goals_against']} GD {row['goal_difference']:+d}{suffix}"
        )
    for note in result.get("notes") or []:
        lines.append(f"\nNote: {note}")
    return "\n".join(lines)


def format_bracket(result: Mapping[str, Any]) -> str:
    error = _error(result)
    if error:
        return error

    lines = [f"{result['season']} {result['competition']} ({result['matches']} matches):"]
    for stage in result.get("stages") or []:
        lines.append(f"\n{stage['stage']} ({stage['matches']} matches):")
        if stage["stage"] == "Group stage":
            for match in stage.get("sample") or []:
                lines.append(match_line(match))
            if stage["matches"] > len(stage.get("sample") or []):
                lines.append(f"... {stage['matches']} group matches in total.")
            continue
        for tie in stage.get("ties") or []:
            aggregate = " / ".join(f"{team} {goals}" for team, goals in tie["aggregate"].items())
            winner = tie.get("winner")
            lines.append(
                f"- {' vs '.join(tie['teams'])}: aggregate {aggregate}"
                + (f" -> {winner} advance" if winner else f" -> {tie.get('note')}")
            )
            for leg in tie.get("legs") or []:
                lines.append(match_line(leg, prefix="    "))
    if result.get("champion"):
        lines.append(f"\nWinner: {result['champion']}")
    for note in result.get("notes") or []:
        lines.append(f"Note: {note}")
    return "\n".join(lines)


def format_competition_stats(result: Mapping[str, Any]) -> str:
    error = _error(result)
    if error:
        return error

    scope = result["competition"] + (f" {result['season']}" if result.get("season") else "")
    lines = [
        f"{scope} - aggregate statistics:",
        f"- Matches: {result['matches']}, goals: {result['goals']}",
        f"- Average goals per match: {result['goals_per_match']}",
        f"- Home win rate: {result['home_win_rate']}%, draws: {result['draw_rate']}%, "
        f"away wins: {result['away_win_rate']}%",
        f"- Goals by home teams: {result['home_goals']}, by away teams: {result['away_goals']}",
        f"- Goalless matches: {result['goalless_matches']}",
    ]
    scorelines = result.get("common_scorelines") or []
    if scorelines:
        lines.append(
            "- Most common scorelines: "
            + ", ".join(f"{item['score']} ({item['count']})" for item in scorelines)
        )
    top = result.get("top_scoring_teams") or []
    if top:
        lines.append("\nHighest scoring teams:")
        for row in top:
            lines.append(
                f"{row['rank']}. {row['team']} - {row['goals_for']} goals in {row['played']} matches"
            )
    biggest = result.get("biggest_wins") or []
    if biggest:
        lines.append("\nBiggest victories:")
        lines.extend(match_line(match) for match in biggest)
    for note in result.get("notes") or []:
        lines.append(f"\nNote: {note}")
    return "\n".join(lines)


def format_biggest_wins(result: Mapping[str, Any]) -> str:
    error = _error(result)
    if error:
        return error

    scope = result.get("competition") or "all competitions"
    if result.get("season"):
        scope += f" {result['season']}"
    if result.get("team"):
        scope = f"{result['team']} in {scope}"
    lines = [f"Biggest victories ({scope}):"]
    for index, match in enumerate(result.get("matches") or [], start=1):
        margin = abs((match["home_goals"] or 0) - (match["away_goals"] or 0))
        lines.append(match_line(match, prefix=f"{index}. ") + f" [margin {margin}]")
    if not result.get("matches"):
        lines.append("No matches found.")
    return "\n".join(lines)


def format_derbies(result: Mapping[str, Any]) -> str:
    error = _error(result)
    if error:
        return error

    scope = []
    if result.get("season"):
        scope.append(str(result["season"]))
    if result.get("competition"):
        scope.append(str(result["competition"]))
    if result.get("team"):
        scope.append(str(result["team"]))
    lines = [
        f"Traditional rivalries{' - ' + ', '.join(scope) if scope else ''}: "
        f"{result['total']} match(es)"
    ]
    for item in result.get("by_derby") or []:
        lines.append(f"- {item['derby']}: {item['matches']}")
    matches = result.get("matches") or []
    if matches:
        lines.append("")
        for match in matches:
            lines.append(match_line(match, prefix=f"- [{match['derby']}] "))
    return "\n".join(lines)


def format_compare_seasons(result: Mapping[str, Any]) -> str:
    error = _error(result)
    if error:
        return error

    lines = [f"{result['competition']} - season comparison:"]
    for entry in result.get("comparison") or []:
        lines.append(f"\n{entry['season']}:")
        lines.append(f"- Matches: {entry['matches']}, goals: {entry['goals']} "
                     f"({entry['goals_per_match']} per match)")
        lines.append(
            f"- Home wins {entry['home_win_rate']}%, draws {entry['draw_rate']}%, "
            f"away wins {entry['away_win_rate']}%"
        )
        if entry.get("champion"):
            lines.append(f"- Champion: {entry['champion']} ({entry['champion_points']} pts)")
        elif entry.get("leader"):
            lines.append(
                f"- Top of the table: {entry['leader']} ({entry['leader_points']} pts) "
                "- season incomplete in the dataset, so not a confirmed champion"
            )
        if entry.get("top_scorer_team"):
            lines.append(f"- Highest scoring team: {entry['top_scorer_team']}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------


def format_search_teams(result: Mapping[str, Any]) -> str:
    error = _error(result)
    if error:
        return error

    lines = [f"Team search for {result['query']!r}:"]
    resolved = result.get("resolved")
    if resolved:
        lines.append(
            f"- Resolved to: {resolved['name']} "
            f"({resolved.get('state_name') or resolved.get('country')}), "
            f"{resolved['matches']} matches, id={resolved['team_id']}"
        )
        spellings = resolved.get("known_spellings") or []
        if spellings:
            lines.append("- Spellings unified: " + ", ".join(spellings))
        competitions = resolved.get("competitions") or []
        if competitions:
            lines.append("- Competitions: " + ", ".join(competitions))
        seasons = resolved.get("seasons") or []
        if seasons:
            lines.append(f"- Seasons: {seasons[0]}-{seasons[-1]}")
    else:
        lines.append("- No exact match.")
    candidates = [item for item in (result.get("candidates") or [])
                  if not resolved or item["team_id"] != resolved["team_id"]]
    if candidates:
        lines.append("- Other candidates: " + ", ".join(
            f"{item['name']} ({item['matches']} matches)" for item in candidates[:8]
        ))
    return "\n".join(lines)


def format_overview(result: Mapping[str, Any]) -> str:
    error = _error(result)
    if error:
        return error

    summary = result["summary"]
    date_range = summary.get("date_range") or ["?", "?"]
    lines = [
        "Brazilian soccer knowledge graph:",
        f"- Matches: {summary['matches']} (from {date_range[0]} to {date_range[-1]})",
        f"- Teams: {summary['teams']}, players: {summary['players']}, "
        f"venues: {summary['venues']}",
        f"- Goals: {summary['goals']} ({summary['goals_per_match']} per match); "
        f"home win rate {summary['home_win_rate']}%, draws {summary['draw_rate']}%",
        "",
        "Competitions:",
    ]
    for competition in result.get("competitions") or []:
        lines.append(
            f"- {competition['competition']}: {competition['matches']} matches, "
            f"seasons {competition['seasons']}"
        )
    nationalities = result.get("top_nationalities") or []
    if nationalities:
        lines.append(
            "\nPlayer nationalities (top 5): "
            + ", ".join(f"{item['nationality']} {item['players']}" for item in nationalities)
        )
    clubs = result.get("linked_fifa_clubs") or []
    if clubs:
        lines.append(f"\nClubs linked between player and match data ({len(clubs)}): "
                     + ", ".join(clubs))
    for note in result.get("notes") or []:
        lines.append(f"\nNote: {note}")
    return "\n".join(lines)


_FORMATTERS = {
    "matches": format_matches,
    "head_to_head": format_head_to_head,
    "team_stats": format_team_stats,
    "team_profile": format_team_profile,
    "rankings": format_rankings,
    "players": format_players,
    "player_profile": format_player_profile,
    "team_squad": format_team_squad,
    "standings": format_standings,
    "bracket": format_bracket,
    "competition_stats": format_competition_stats,
    "biggest_wins": format_biggest_wins,
    "derbies": format_derbies,
    "compare_seasons": format_compare_seasons,
    "search_teams": format_search_teams,
    "overview": format_overview,
}


def format_result(kind: str, result: Mapping[str, Any]) -> str:
    """Render *result* using the formatter registered for *kind*."""
    formatter = _FORMATTERS.get(kind)
    if formatter is None:  # pragma: no cover - guarded by tests
        raise KeyError(f"No formatter for {kind!r}")
    return formatter(result)
