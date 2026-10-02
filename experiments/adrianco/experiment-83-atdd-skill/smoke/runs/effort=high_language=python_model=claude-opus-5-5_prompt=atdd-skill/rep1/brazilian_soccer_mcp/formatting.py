"""
Human-readable answers: renders each query result as concise text that an
LLM can quote or summarise directly (the structured data travels with it
as MCP `structuredContent`).
"""

from .data import SERIE_A


def match_line(m):
    where = m["competition"]
    if m.get("round") and m["competition"] in (SERIE_A, "Brasileirão Série B", "Brasileirão Série C"):
        where += f" Round {m['round']}"
    elif m.get("round"):
        where += f" round {m['round']}"
    if m.get("stage"):
        where += f" {m['stage']}"
    line = f"{m['date'] or 'date unknown'}: {m['home']} {m['home_goals']}-{m['away_goals']} {m['away']} ({where})"
    stats = m.get("stats") or {}
    extras = [f"{label} {stats[f'home_{key}']}-{stats[f'away_{key}']}"
              for key, label in (("corners", "corners"), ("shots", "shots"), ("attacks", "attacks"))
              if f"home_{key}" in stats]
    if extras:
        line += " [" + ", ".join(extras) + "]"
    return line


def _more(total, shown):
    return [f"... ({total - shown} more matches in dataset)"] if total > shown else []


def find_matches(r):
    criteria = ", ".join(f"{k}={v}" for k, v in r["criteria"].items()) or "all matches"
    if "head_to_head" in r:
        h = r["head_to_head"]
        title = f"{h['team_a']} vs {h['team_b']}"
    else:
        title = f"Matches ({criteria})"
    lines = [f"{title}: {r['total']} match{'es' if r['total'] != 1 else ''} found"]
    lines += [f"- {match_line(m)}" for m in r["matches"]]
    lines += _more(r["total"], len(r["matches"]))
    if "head_to_head" in r:
        lines += ["", head_to_head_line(r["head_to_head"])]
    return "\n".join(lines)


def head_to_head_line(h):
    return (f"Head-to-head in dataset: {h['team_a']} {h['team_a_wins']} wins, {h['team_b']} {h['team_b_wins']} "
            f"wins, {h['draws']} draws (goals {h['team_a_goals']}-{h['team_b_goals']}, {h['matches']} matches)")


def head_to_head(r):
    lines = [f"{r['team_a']} vs {r['team_b']} head-to-head:", head_to_head_line(r), "", "Most recent meetings:"]
    lines += [f"- {match_line(m)}" for m in r["recent"]] or ["- none"]
    return "\n".join(lines)


def record_lines(r):
    return [
        f"- Matches: {r['matches']}",
        f"- Wins: {r['wins']}, Draws: {r['draws']}, Losses: {r['losses']}",
        f"- Goals For: {r['goals_for']}, Goals Against: {r['goals_against']} (difference {r['goal_difference']:+d})",
        f"- Points: {r['points']}",
        f"- Win rate: {r['win_rate']:.1f}%",
    ]


def team_record(r):
    scope = [s for s in (r["competition"], str(r["season"]) if r["season"] else None) if s]
    venue = {"home": "home record", "away": "away record"}.get(r["venue"], "record")
    title = f"{r['team']} {venue}" + (f" ({' '.join(scope[::-1])})" if scope else " (all competitions in dataset)")
    return "\n".join([title + ":"] + record_lines(r))


def team_competitions(r):
    lines = [f"Competitions {r['team']} has played in (provided data):"]
    for c in r["competitions"]:
        lines.append(f"- {c['competition']}: {c['matches']} matches in seasons {_seasons(c['seasons'])} "
                     f"({c['wins']}W {c['draws']}D {c['losses']}L)")
    return "\n".join(lines)


def team_profile(r):
    lines = [f"{r['team']} — profile from match and player data", "", "Overall record (all competitions):"]
    lines += record_lines(r["record"])
    lines += [f"Home: {r['home_record']['wins']}W {r['home_record']['draws']}D {r['home_record']['losses']}L, "
              f"Away: {r['away_record']['wins']}W {r['away_record']['draws']}D {r['away_record']['losses']}L", "",
              "Competitions:"]
    lines += [f"- {c['competition']}: {c['matches']} matches ({_seasons(c['seasons'])})" for c in r["competitions"]]
    lines += ["", "Recent matches:"] + [f"- {match_line(m)}" for m in r["recent_matches"]]
    lines += ["", f"FIFA squad ({r['squad_size']} players in player data):"]
    lines += [f"- {player_line(p)}" for p in r["squad"]] or ["- no players for this club in the FIFA data"]
    return "\n".join(lines)


def standings(r):
    status = "" if r["complete"] else " — partial season in data"
    lines = [f"{r['season']} {r['competition']} Final Standings (calculated from {r['matches']} matches{status}):"]
    for row in r["table"]:
        line = (f"{row['position']}. {row['team']} - {row['points']} pts ({row['wins']}W, {row['draws']}D, "
                f"{row['losses']}L, GF {row['goals_for']}, GA {row['goals_against']}, GD {row['goal_difference']:+d})")
        if row["position"] == 1:
            line += " - Champion"
        if row["team"] in r["relegated"]:
            line += " - Relegation zone"
        lines.append(line)
    if r["relegated"]:
        lines += ["", f"Relegated (bottom four): {', '.join(r['relegated'])}"]
    lines.append("Note: points are calculated from results; any sporting-court deductions are not reflected.")
    return "\n".join(lines)


def tie_lines(t, indent="  "):
    result = f"winner {t['winner']} ({t['decided_by']})" if t["winner"] else t["decided_by"]
    lines = [f"{t['teams'][0]} vs {t['teams'][1]}: aggregate {t['aggregate']}, {result}"]
    lines += [f"{indent}- {match_line(m)}" for m in t["legs"]]
    return lines


def cup_finals(r):
    lines = [f"{r['competition']} finals (provided data):"]
    for f in r["finals"]:
        lines.append(f"{f['season']}: " + tie_lines(f)[0])
        lines += tie_lines(f)[1:]
    if not r["finals"]:
        lines.append("- none found")
    return "\n".join(lines)


def knockout_bracket(r):
    lines = [f"{r['season']} {r['competition']} knockout bracket:"]
    for stage in r["stages"]:
        lines += ["", f"{stage['stage'].title()}:"]
        for tie in stage["ties"]:
            first, *legs = tie_lines(tie, indent="    ")
            lines += [f"- {first}"] + legs
    return "\n".join(lines)


def find_derbies(r):
    lines = [f"Derbies found: {r['total']}"]
    lines += [f"- {name}: {count} matches" for name, count in sorted(r["by_derby"].items(), key=lambda kv: -kv[1])]
    lines += [""] + [f"- {m['derby']}: {match_line(m)}" for m in r["matches"]]
    lines += _more(r["total"], len(r["matches"]))
    return "\n".join(lines)


def summary_lines(r):
    return [
        f"- Matches: {r['matches']}, Goals: {r['goals']}",
        f"- Average goals per match: {r['average_goals']:.2f}",
        f"- Home win rate: {r['home_win_rate']:.1f}%, Draw rate: {r['draw_rate']:.1f}%, "
        f"Away win rate: {r['away_win_rate']:.1f}%",
    ]


def competition_stats(r):
    scope = " ".join(str(s) for s in (r["season"], r["competition"]) if s)
    who = f" — {r['team']}'s matches" if r["team"] else ""
    return "\n".join([f"{scope} statistics{who}:"] + summary_lines(r))


def biggest_wins(r):
    lines = ["Biggest victories (provided data):"]
    lines += [f"{i}. {match_line(m)} — {m['winner']} by {m['margin']}" for i, m in enumerate(r["matches"], 1)]
    return "\n".join(lines)


def rank_teams(r):
    venue = {"home": "home ", "away": "away "}.get(r["venue"], "")
    scope = " ".join(str(s) for s in (r["season"], r["competition"]) if s)
    lines = [f"Teams ranked by {venue}{r['metric_label'].lower()} — {scope} (min {r['min_matches']} matches):"]
    for row in r["ranking"]:
        value = f"{row['value']:.1f}%" if r["metric"] == "win_rate" else row["value"]
        lines.append(f"{row['rank']}. {row['team']} - {r['metric_label']}: {value} "
                     f"({row['matches']} matches, {row['wins']}W {row['draws']}D {row['losses']}L, "
                     f"GF {row['goals_for']}, GA {row['goals_against']})")
    return "\n".join(lines)


def compare_seasons(r):
    lines = [f"{r['competition']} season comparison:"]
    for s in r["seasons"]:
        lines += ["", f"{s['season']}:"]
        if not s["matches"]:
            lines.append("- no matches in the data")
            continue
        lines += summary_lines(s)
        if "champion" in s:
            lines.append(f"- Champion: {s['champion']} ({s['champion_points']} pts)")
        if s.get("relegated"):
            lines.append(f"- Relegated: {', '.join(s['relegated'])}")
        lines.append(f"- Top-scoring team: {s['top_scoring_team']['team']} ({s['top_scoring_team']['goals']} goals)")
    return "\n".join(lines)


def player_line(p):
    return (f"{p['name']} - Overall: {p['overall']}, Position: {p['position'] or '?'}, "
            f"Club: {p['club'] or 'no club'}, Nationality: {p['nationality']}, Age: {p['age']}")


def search_players(r):
    lines = [f"Players found: {r['total']}"]
    lines += [f"{i}. {player_line(p)}" for i, p in enumerate(r["players"], 1)]
    if r["total"] > len(r["players"]):
        lines.append(f"... ({r['total'] - len(r['players'])} more players)")
    return "\n".join(lines)


def player_profile(r):
    p = r["player"]
    lines = [
        f"{p['name']}",
        f"- Club: {p['club'] or 'no club'}, Position: {p['position']}, Jersey: {p['jersey_number']}",
        f"- Nationality: {p['nationality']}, Age: {p['age']}",
        f"- Overall: {p['overall']}, Potential: {p['potential']}",
        f"- Height: {p['height']}, Weight: {p['weight']}, Preferred foot: {p['preferred_foot']}",
        f"- Value: {p['value']}, Wage: {p['wage']}",
    ]
    skills = p.get("skills") or {}
    top = sorted(skills.items(), key=lambda kv: -kv[1])[:6]
    if top:
        lines.append("- Best attributes: " + ", ".join(f"{k} {v}" for k, v in top))
    if r["other_matches"]:
        lines.append(f"Other players matching: {', '.join(r['other_matches'])}")
    return "\n".join(lines)


def brazilian_club_players(r):
    who = f"{r['nationality'].title()} players" if r["nationality"] else "Players"
    lines = [f"{who} at Brazilian clubs (clubs that appear in Brazilian match data): {r['total_players']}"]
    for c in r["clubs"]:
        lines.append(f"- {c['club']}: {c['players']} players (avg rating: {c['average_overall']:.0f}), "
                     f"top: {c['top_player']['name']} ({c['top_player']['overall']}, {c['top_player']['position']})")
    if not r["clubs"]:
        lines.append("- none found")
    return "\n".join(lines)


def dataset_info(r):
    lines = [f"Data directory: {r['data_dir']}", "Files:"]
    for f in r["files"]:
        status = f"{f['rows']} rows" if f["loaded"] else f"NOT LOADED ({f['error']})"
        extra = []
        if f["duplicates_merged"]:
            extra.append(f"{f['duplicates_merged']} overlapping matches merged")
        if f["skipped"]:
            extra.append(f"{f['skipped']} unusable rows skipped")
        lines.append(f"- {f['file']}: {status}" + (f" ({'; '.join(extra)})" if extra else ""))
    lines += [f"Distinct matches: {r['matches']}, players: {r['players']}, teams: {r['teams']}", "Competitions:"]
    lines += [f"- {c['competition']}: {c['matches']} matches, seasons {c['seasons']}" for c in r["competitions"]]
    return "\n".join(lines)


def _seasons(seasons):
    if len(seasons) > 3 and seasons == list(range(seasons[0], seasons[-1] + 1)):
        return f"{seasons[0]}-{seasons[-1]}"
    return ", ".join(str(s) for s in seasons)
