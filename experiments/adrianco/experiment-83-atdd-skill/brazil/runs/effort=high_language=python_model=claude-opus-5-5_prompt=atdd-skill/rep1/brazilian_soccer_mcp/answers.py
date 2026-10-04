"""Readable text versions of the structured answers, laid out like the examples in the specification."""
from brazilian_soccer_mcp.names import LEAGUES

TEXT_LINES = 25


def match_line(match):
    detail = ""
    if match.get("round") and match["competition"] in LEAGUES:
        detail = f" Round {match['round']}"
    elif match.get("stage"):
        detail = f" {match['stage']}"
    line = (f"{match['date'] or 'date unknown'}: {match['home']} {match['home_goals']}-{match['away_goals']} "
            f"{match['away']} ({match['competition']}{detail})")
    statistics = match.get("statistics") or {}
    extras = [f"{label} {statistics[f'home_{key}']}-{statistics[f'away_{key}']}"
              for key, label in (("corners", "corners"), ("shots", "shots"), ("attacks", "attacks"))
              if f"home_{key}" in statistics and f"away_{key}" in statistics]
    if extras:
        line += " [" + ", ".join(extras) + "]"
    return line


def _scope(competition=None, season=None, venue=None, stage=None, date_from=None, date_to=None, **_):
    parts = [str(season) if season else None, competition, stage, f"{venue} matches" if venue not in (None, "any")
             else None, f"from {date_from}" if date_from else None, f"to {date_to}" if date_to else None]
    return ", ".join(part for part in parts if part)


def _match_list(matches, total, header):
    if not total:
        return f"No matches found ({header})"
    lines = [header + ":"] + [f"- {match_line(match)}" for match in matches[:TEXT_LINES]]
    if total > min(len(matches), TEXT_LINES):
        lines.append(f"... ({total - min(len(matches), TEXT_LINES)} more matches in dataset)")
    return "\n".join(lines)


def _percent(value):
    return f"{value:.1f}%"


def search_matches(answer, arguments):
    scope = _scope(**arguments)
    if answer["team"] and answer["opponent"]:
        header = f"{answer['team']} vs {answer['opponent']}"
        if answer.get("derby"):
            header += f" ({answer['derby']} derby)"
    elif answer["team"]:
        header = f"Matches for {answer['team']}"
    else:
        header = "Matches"
    if scope:
        header += f" [{scope}]"
    text = _match_list(answer["matches"], answer["total"], header)
    summary = answer.get("head_to_head")
    if summary and summary["matches"]:
        text += (f"\n\nHead-to-head in dataset: {summary['team']['name']} {summary['team']['wins']} wins, "
                 f"{summary['opponent']['name']} {summary['opponent']['wins']} wins, {summary['draws']} draws")
    return text


def head_to_head(answer, arguments):
    team, opponent = answer["team"], answer["opponent"]
    title = f"{team['name']} vs {opponent['name']}"
    if answer.get("derby"):
        title += f" ({answer['derby']} derby)"
    scope = _scope(competition=answer.get("competition"), season=answer.get("season"))
    if scope:
        title += f" [{scope}]"
    if not answer["matches"]:
        return f"No matches found between {team['name']} and {opponent['name']}"
    lines = [f"{title}:",
             f"- Matches: {answer['matches']}",
             f"- {team['name']} wins: {team['wins']}, {opponent['name']} wins: {opponent['wins']}, "
             f"Draws: {answer['draws']}",
             f"- Goals: {team['name']} {team['goals']}, {opponent['name']} {opponent['goals']}",
             "", "Most recent meetings:"]
    lines += [f"- {match_line(match)}" for match in answer["recent_matches"][:10]]
    return "\n".join(lines)


def find_derbies(answer, arguments):
    header = "Derbies" + (f" [{_scope(**arguments)}]" if _scope(**arguments) else "")
    if not answer["total"]:
        return f"No derbies found ({header})"
    shown = answer["matches"][:TEXT_LINES]
    lines = [header + ":"] + [f"- {match_line(match)} - {match['derby']}" for match in shown]
    if answer["total"] > len(shown):
        lines.append(f"... ({answer['total'] - len(shown)} more derbies in dataset)")
    return "\n".join(lines)


def team_record(answer, arguments):
    venue = f"{answer['venue']} " if answer["venue"] != "any" else ""
    scope = " ".join(str(part) for part in (answer["season"], answer["competition"] or "all competitions") if part)
    against = f" against {answer['opponent']}" if answer.get("opponent") else ""
    if not answer["matches"]:
        return f"No matches found for {answer['team']}{against} ({venue}{scope})"
    return "\n".join([
        f"{answer['team']} {venue}record{against} ({scope}):",
        f"- Matches: {answer['matches']}",
        f"- Wins: {answer['wins']}, Draws: {answer['draws']}, Losses: {answer['losses']}",
        f"- Goals For: {answer['goals_for']}, Goals Against: {answer['goals_against']}",
        f"- Win rate: {_percent(answer['win_rate'])}",
    ])


def team_overview(answer, arguments):
    record = answer["record"]
    lines = [f"{answer['team']} overview:",
             f"- All matches in dataset: {record['matches']} (W{record['wins']} D{record['draws']} L{record['losses']}, "
             f"goals {record['goals_for']}-{record['goals_against']}, win rate {_percent(record['win_rate'])})",
             "", "Competitions played:"]
    for entry in answer["competitions"]:
        seasons = entry["seasons"]
        span = f"{seasons[0]}-{seasons[-1]}" if len(seasons) > 1 else (str(seasons[0]) if seasons else "")
        lines.append(f"- {entry['competition']}: {entry['matches']} matches ({span}), "
                     f"W{entry['wins']} D{entry['draws']} L{entry['losses']}")
    if answer["rivals"]:
        lines += ["", "Derby rivals met: " + ", ".join(answer["rivals"])]
    squad = answer["squad"]
    lines.append("")
    if squad["players"]:
        lines.append(f"Squad in FIFA dataset: {squad['count']} players (avg rating: {squad['average_overall']})")
        lines += [f"- {player['name']} - Overall: {player['overall']}, Position: {player['position']}, "
                  f"Nationality: {player['nationality']}" for player in squad["players"][:10]]
    else:
        lines.append("No players from this club in the FIFA dataset")
    if answer["recent_matches"]:
        lines += ["", "Most recent matches:"] + [f"- {match_line(match)}" for match in answer["recent_matches"]]
    return "\n".join(lines)


def standings(answer, arguments):
    lines = [f"{answer['season']} {answer['competition']} Final Standings (calculated from matches):"]
    for row in answer["table"]:
        status = {"champion": " - Champion", "relegated": " - Relegated"}.get(row["status"], "")
        lines.append(f"{row['position']}. {row['team']} - {row['points']} pts ({row['wins']}W, {row['draws']}D, "
                     f"{row['losses']}L, GD {row['goal_difference']:+d}){status}")
    if answer["relegated"]:
        lines += ["", "Relegated: " + ", ".join(answer["relegated"])]
    return "\n".join(lines)


def knockout_bracket(answer, arguments):
    lines = [f"{answer['season']} {answer['competition']} knockout bracket:"]
    for stage in answer["stages"]:
        lines += ["", stage["stage"].capitalize() + ":"]
        for tie in stage["ties"]:
            outcome = f"{tie['winner']} advance" if tie["winner"] else "level on aggregate (away goals or penalties decided it)"
            if stage["stage"] == "final" and tie["winner"]:
                outcome = f"{tie['winner']} win"
            legs = "; ".join(f"{leg['home']} {leg['home_goals']}-{leg['away_goals']} {leg['away']}"
                             for leg in tie["legs"])
            lines.append(f"- {tie['team']} {tie['team_goals']}-{tie['opponent_goals']} {tie['opponent']} on aggregate "
                         f"({legs}) - {outcome}")
    return "\n".join(lines)


def competition_stats(answer, arguments):
    scope = _scope(competition=answer["competition"] or "all competitions", season=answer["season"])
    if answer.get("team"):
        scope += f", {answer['team']} matches"
    if not answer["matches"]:
        return f"No matches found ({scope})"
    return "\n".join([
        f"Statistics ({scope}):",
        f"- Matches: {answer['matches']}, Goals: {answer['goals']}",
        f"- Average goals per match: {answer['average_goals']:.2f}",
        f"- Home win rate: {_percent(answer['home_win_rate'])}, Away win rate: {_percent(answer['away_win_rate'])}, "
        f"Draw rate: {_percent(answer['draw_rate'])}",
    ])


def compare_seasons(answer, arguments):
    lines = [f"{answer['competition']} season comparison:"]
    for entry in answer["seasons"]:
        line = (f"- {entry['season']}: {entry['matches']} matches, {entry['average_goals']:.2f} goals per match, "
                f"home wins {_percent(entry['home_win_rate'])}, draws {_percent(entry['draw_rate'])}")
        if entry.get("champion"):
            line += f", champion {entry['champion']}"
        if entry.get("top_scoring_team"):
            line += f", top scorers {entry['top_scoring_team']['team']} ({entry['top_scoring_team']['goals']} goals)"
        lines.append(line)
    return "\n".join(lines)


def biggest_wins(answer, arguments):
    scope = _scope(competition=answer["competition"], season=answer["season"]) or "all competitions"
    if not answer["matches"]:
        return f"No wins found ({scope})"
    lines = [f"Biggest victories ({scope}):"]
    lines += [f"{number}. {match_line(match)}" for number, match in enumerate(answer["matches"], start=1)]
    return "\n".join(lines)


def rank_teams(answer, arguments):
    from brazilian_soccer_mcp.knowledge import METRICS
    label = METRICS[answer["metric"]][0]
    venue = f"{answer['venue']} " if answer["venue"] != "any" else ""
    scope = _scope(competition=answer["competition"], season=answer["season"]) or "all competitions"
    lines = [f"Teams ranked by {venue}{label} ({scope}, at least {answer['min_matches']} matches):"]
    for number, row in enumerate(answer["rankings"], start=1):
        shown = _percent(row["value"]) if answer["metric"] == "win_rate" else row["value"]
        lines.append(f"{number}. {row['team']} - {label}: {shown} ({row['matches']} matches, {row['wins']}W "
                     f"{row['draws']}D {row['losses']}L, goals {row['goals_for']}-{row['goals_against']})")
    return "\n".join(lines)


def _player_line(player):
    return (f"{player['name']} - Overall: {player['overall']}, Position: {player['position'] or '?'}, "
            f"Club: {player['club'] or 'no club'}, Nationality: {player['nationality']}, Age: {player['age']}")


def search_players(answer, arguments):
    criteria = ", ".join(f"{key}: {value}" for key, value in arguments.items() if value and key != "limit")
    if not answer["total"]:
        return f"No players found ({criteria or 'no criteria'})"
    lines = [f"Players found ({criteria or 'all players'}) - {answer['total']} in dataset, highest rated first:"]
    lines += [f"{number}. {_player_line(player)}" for number, player in enumerate(answer["players"], start=1)]
    if answer["total"] > len(answer["players"]):
        lines.append(f"... ({answer['total'] - len(answer['players'])} more players)")
    return "\n".join(lines)


def get_player(answer, arguments):
    player = answer["player"]
    skills = player.get("skills") or {}
    top_skills = sorted(skills.items(), key=lambda item: -item[1])[:6]
    lines = [f"{player['name']}:",
             f"- Club: {player['club'] or 'no club'}, Position: {player['position']}, "
             f"Jersey number: {player['jersey_number']}",
             f"- Nationality: {player['nationality']}, Age: {player['age']}",
             f"- Overall: {player['overall']}, Potential: {player['potential']}",
             f"- Height: {player['height']}, Weight: {player['weight']}, Preferred foot: {player['preferred_foot']}",
             f"- Value: {player['value']}, Wage: {player['wage']}"]
    if top_skills:
        lines.append("- Best attributes: " + ", ".join(f"{name} {value}" for name, value in top_skills))
    if answer["other_matches"]:
        lines.append("Other players with similar names: " + ", ".join(answer["other_matches"]))
    return "\n".join(lines)


def club_squads(answer, arguments):
    who = f"{answer['nationality']} players" if answer["nationality"] else "Players"
    where = "Brazilian clubs" if answer["brazilian_clubs_only"] else "clubs"
    if not answer["clubs"]:
        return f"No {who.lower()} found at {where}"
    lines = [f"{who} at {where} (FIFA dataset):"]
    lines += [f"- {club['club']}: {club['players']} players (avg rating: {club['average_overall']:.0f}, "
              f"best: {club['best_player']} {club['best_overall']})" for club in answer["clubs"]]
    return "\n".join(lines)


def dataset_summary(answer, arguments):
    lines = ["Datasets loaded:"]
    lines += [f"- {entry['file']}: {entry['records']} records ({entry['description']})"
              + (f", {entry['skipped']} rows without a result skipped" if entry["skipped"] else "")
              for entry in answer["datasets"]]
    lines += ["", f"{answer['matches']} distinct matches between {answer['teams']} teams, "
                  f"{answer['players']} players", "", "Competitions:"]
    for entry in answer["competitions"]:
        seasons = entry["seasons"]
        lines.append(f"- {entry['competition']}: {entry['matches']} matches"
                     + (f" ({seasons[0]}-{seasons[-1]})" if seasons else ""))
    return "\n".join(lines)
