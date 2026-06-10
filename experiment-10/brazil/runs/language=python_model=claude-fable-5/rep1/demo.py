"""Demo: answers 20+ sample questions from the specification using the
query engine that backs the MCP tools.

Run:
    python demo.py
"""

import queries


def show(question: str, answer) -> None:
    print(f"\nQ: {question}")
    print(f"A: {answer}")


def fmt_match(m: dict) -> str:
    return f"{m['date']}: {m['home_team']} {m['score']} {m['away_team']} ({m['competition']})"


def main() -> None:
    # --- Match queries ---------------------------------------------------
    h2h = queries.head_to_head("Flamengo", "Fluminense")
    show("Show me all Flamengo vs Fluminense matches",
         f"{h2h['total_matches']} matches. Latest: {fmt_match(h2h['matches'][0])}. "
         f"{h2h['summary']}")

    r = queries.search_matches(team="Palmeiras", season=2023, limit=3)
    show("What matches did Palmeiras play in 2023?",
         f"{r['total_matches']} matches, e.g. " +
         "; ".join(fmt_match(m) for m in r["matches"]))

    r = queries.search_matches(team="Flamengo", opponent="Corinthians", limit=1)
    show("When did Flamengo last play Corinthians?", fmt_match(r["matches"][0]))

    last = r["matches"][0]
    show("What was the score?", f"{last['home_team']} {last['score']} {last['away_team']}")

    r = queries.search_matches(team="Santos", competition="libertadores", limit=2)
    show("Find Santos matches in the Copa Libertadores",
         f"{r['total_matches']} matches, e.g. " +
         "; ".join(fmt_match(m) for m in r["matches"]))

    r = queries.search_matches(team="Gremio", date_from="2015-01-01",
                               date_to="2015-06-30", limit=2)
    show("What did Grêmio play in the first half of 2015?",
         f"{r['total_matches']} matches, e.g. " +
         "; ".join(fmt_match(m) for m in r["matches"]))

    # --- Team queries ----------------------------------------------------
    s = queries.team_stats("Corinthians", season=2022,
                           competition="brasileirao", venue="home")
    show("What is Corinthians' home record in 2022?",
         f"{s['matches']} matches: {s['wins']}W {s['draws']}D {s['losses']}L, "
         f"goals {s['goals_for']}-{s['goals_against']}, win rate {s['win_rate']}%")

    h2h = queries.head_to_head("Palmeiras", "Santos")
    show("Compare Palmeiras and Santos head-to-head", h2h["summary"])

    tc = queries.team_competitions("Palmeiras")
    show("What competitions has Palmeiras played in?",
         ", ".join(tc["competitions"]))

    table = queries.standings(2023)
    scorers = max(table["standings"], key=lambda r: r["goals_for"])
    show("Which team scored the most goals in Serie A 2023?",
         f"{scorers['team']} with {scorers['goals_for']} goals")

    # --- Competition queries ----------------------------------------------
    t = queries.standings(2019)
    top = t["standings"][0]
    show("Who won the 2019 Brasileirão?",
         f"{t['champion']} - {top['points']} pts ({top['wins']}W {top['draws']}D "
         f"{top['losses']}L)")

    show("Which teams were relegated in 2019?", ", ".join(t["relegated"]))

    t2008 = queries.standings(2008)
    show("Who won the 2008 Brasileirão?", t2008["champion"])

    t15 = queries.standings(2015)
    show("Show the top 3 of the 2015 season",
         "; ".join(f"{r['position']}. {r['team']} {r['points']} pts"
                   for r in t15["standings"][:3]))

    # --- Statistical analysis ---------------------------------------------
    cs = queries.competition_stats(competition="serie-a")
    show("What's the average goals per match in the Brasileirão?",
         f"{cs['avg_goals_per_match']} goals/match over {cs['matches']} matches; "
         f"home win rate {cs['home_win_rate']}%")

    br = queries.best_records(venue="away", min_matches=100, limit=3)
    best = br["teams"][0]
    show("Which team has the best away record?",
         f"{best['team']} ({best['win_rate']}% wins in {best['matches']} away matches)")

    bw = queries.biggest_wins(limit=3)
    show("Show me the biggest wins in the dataset",
         "; ".join(f"{m['date']}: {m['home_team']} {m['score']} {m['away_team']}"
                   for m in bw["matches"]))

    s18 = queries.competition_stats(competition="serie-a", season=2018)
    s19 = queries.competition_stats(competition="serie-a", season=2019)
    show("Compare the 2018 and 2019 seasons",
         f"2018: {s18['avg_goals_per_match']} goals/match; "
         f"2019: {s19['avg_goals_per_match']} goals/match")

    cup = queries.competition_stats(competition="copa do brasil")
    show("How many Copa do Brasil matches are in the dataset?",
         f"{cup['matches']} matches, {cup['avg_goals_per_match']} goals/match")

    # --- Player queries ----------------------------------------------------
    p = queries.search_players(nationality="Brazil", limit=3)
    show("Find all Brazilian players in the dataset",
         f"{p['total_players']} Brazilian players. Top: " +
         ", ".join(f"{x['name']} ({x['overall']})" for x in p["players"]))

    top_br = queries.top_players(nationality="Brazil", limit=3)
    show("Who are the top Brazilian players?",
         ", ".join(f"{x['name']} - Overall {x['overall']}, {x['position']}, {x['club']}"
                   for x in top_br["players"]))

    gj = queries.get_player("Gabriel Jesus")
    show("Who is Gabriel Jesus?",
         f"{gj['name']}, {gj['age']}, {gj['nationality']}, {gj['position']} at "
         f"{gj['club']}, overall {gj['overall']}")

    rm = queries.search_players(club="Real Madrid", limit=3)
    show("Who are the highest-rated players at Real Madrid?",
         ", ".join(f"{x['name']} ({x['overall']})" for x in rm["players"]))

    fw = queries.search_players(nationality="Brazil", position="forward", limit=3)
    show("Show me the best Brazilian forwards",
         ", ".join(f"{x['name']} ({x['position']}, {x['overall']})"
                   for x in fw["players"]))

    gk = queries.search_players(nationality="Brazil", position="goalkeeper",
                                limit=2)
    show("Who is the best Brazilian goalkeeper?",
         f"{gk['players'][0]['name']} (overall {gk['players'][0]['overall']})")

    print(f"\n{'-' * 60}\nAnswered 25 sample questions.")


if __name__ == "__main__":
    main()
