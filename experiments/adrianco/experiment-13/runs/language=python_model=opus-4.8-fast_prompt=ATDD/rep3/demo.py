"""
Command-line demonstration of the Brazilian Soccer knowledge base.

Runs a batch of the sample questions from the specification against the same
``SoccerService`` the MCP server exposes, printing human-readable answers. This
is a convenience for eyeballing the data outside of an MCP client; the
authoritative interface is the MCP server in ``server.py``.

    python demo.py
"""

from soccer_service import SoccerService


def main() -> None:
    svc = SoccerService()

    print("== Flamengo vs Fluminense (Fla-Flu) ==")
    r = svc.find_matches(team="Flamengo", opponent="Fluminense", limit=3)
    for m in r["matches"]:
        print(f"  {m['date']}: {m['home_team']} {m['score']} {m['away_team']} "
              f"({m['competition']})")
    h = r["head_to_head"]
    print(f"  Head-to-head ({r['count']} matches): Flamengo {h['team_a_wins']}W, "
          f"Fluminense {h['team_b_wins']}W, {h['draws']}D\n")

    print("== 2019 Brasileirão final standings (top 5) ==")
    s = svc.get_standings(season=2019)
    for row in s["table"][:5]:
        print(f"  {row['position']}. {row['team']} - {row['points']} pts "
              f"({row['wins']}W {row['draws']}D {row['losses']}L)")
    print(f"  Champion: {s['champion']}\n")

    print("== Corinthians 2019 record ==")
    rec = svc.get_team_record(team="Corinthians", season=2019)
    print(f"  {rec['matches']} matches: {rec['wins']}W {rec['draws']}D {rec['losses']}L, "
          f"GF {rec['goals_for']} GA {rec['goals_against']}, win rate {rec['win_rate']}%\n")

    print("== Top 5 Brazilian players ==")
    p = svc.search_players(nationality="Brazil", limit=5)
    for pl in p["players"]:
        print(f"  {pl['name']} - {pl['overall']} ({pl['position']}, {pl['club']})")
    print()

    print("== Brasileirão statistics ==")
    summary = svc.get_competition_summary(competition="Brasileirão")
    print(f"  Matches: {summary['matches']}, avg goals/match: "
          f"{summary['avg_goals_per_match']}, home win rate: {summary['home_win_rate']}%")
    big = summary["biggest_wins"][0]
    print(f"  Biggest win: {big['date']} {big['home_team']} {big['score']} {big['away_team']}")


if __name__ == "__main__":
    main()
