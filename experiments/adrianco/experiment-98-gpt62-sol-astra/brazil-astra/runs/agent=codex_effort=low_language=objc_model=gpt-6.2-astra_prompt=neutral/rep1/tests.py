"""Integration scenarios against the actual MCP stdio transport and bundled data."""
import json
import subprocess
import time
import unittest


class SoccerScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = subprocess.Popen(["./soccer-mcp"], stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, text=True)
        reply = cls.request("initialize", {"protocolVersion": "2025-03-26"})
        assert reply["result"]["protocolVersion"] == "2025-03-26"
        cls.server.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        assert cls.request("tools/list", {})["result"]["tools"][0]["name"] == "query_soccer"

    @classmethod
    def tearDownClass(cls):
        cls.server.stdin.close()
        assert cls.server.wait(timeout=5) == 0
        cls.server.stdout.close()

    @classmethod
    def request(cls, method, params):
        cls.server.stdin.write(json.dumps(dict(jsonrpc="2.0", id=1, method=method, params=params)) + "\n")
        cls.server.stdin.flush()
        return json.loads(cls.server.stdout.readline())

    def call(self, sql):
        return self.request("tools/call", {"name": "query_soccer", "arguments": {"sql": sql}})["result"]

    def rows(self, sql):
        start = time.monotonic()
        reply = self.call(sql)
        self.assertLess(time.monotonic() - start, 2)
        self.assertFalse(reply.get("isError"), reply)
        return json.loads(reply["content"][0]["text"])["rows"]

    def test_sources_and_coverage(self):
        self.assertEqual(sorted(r["n"] for r in self.rows(
            "select source,count(*) n from raw_matches group by source")),
            [1255, 1337, 4180, 6886, 10296])
        self.assertEqual(self.rows("select count(*) n from players"), [{"n": 18207}])

    def test_derby_history_and_records(self):
        rows = self.rows("""select date,home_goal,away_goal,competition from matches where
            (home='flamengo' and away='fluminense') or (away='flamengo' and home='fluminense')
            order by date desc""")
        self.assertGreater(len(rows), 30)
        self.assertTrue(rows[0]["date"].startswith("2023"))
        table = self.rows("select * from standings where competition='Serie A' and season=2019 order by points desc")
        self.assertEqual(len(table), 20)
        self.assertEqual((table[0]["team"], table[0]["points"], table[0]["played"]), ("flamengo", 90, 38))
        record = self.rows("""select count(*) n,sum(gf>ga) wins,sum(gf=ga) draws,sum(gf<ga) losses
            from team_results where team=club_key('Sport Club Corinthians Paulista') and
            season=2022 and venue='home' and competition='Serie A'""")[0]
        self.assertEqual(record["n"], 19)
        self.assertEqual(record["wins"] + record["losses"] + record["draws"], 19)

    def test_player_attributes_and_relationships(self):
        best = self.rows("select name,overall,json_extract(attributes,'$.Dribbling') skill from players where nationality='Brazil' order by overall desc limit 1")[0]
        self.assertIn("Neymar", best["name"])
        self.assertGreater(int(best["skill"]), 90)
        self.assertTrue(self.rows("""select distinct p.name from players p join team_results t on
            t.team=p.club where t.competition='Serie A' and t.season=2018 limit 5"""))

    def test_sample_questions(self):
        # Each query is the tool argument an LLM can supply for the named question.
        cases = {
            "When did Flamengo last face Corinthians?": "select max(date) d from team_results where team='flamengo' and opponent='corinthians'",
            "Which matches did Palmeiras play in 2023?": "select * from matches where season=2023 and 'palmeiras' in(home,away)",
            "Which matches took place in March 2003?": "select * from matches where date between '2003-03-01' and '2003-03-31'",
            "What were the cup finals?": "select * from matches where competition='Copa do Brasil' and stage='final'",
            "Which competitions feature Palmeiras?": "select distinct competition from team_results where team='palmeiras'",
            "What was the 2018 Libertadores bracket?": "select stage,home,away,date from matches where season=2018 and competition='Libertadores' and stage!='group stage' order by date",
            "Which sides finished bottom four in 2020?": "select team from standings where season=2020 and competition='Serie A' order by points,wins,gd,goals_for limit 4",
            "Who scored most in Serie A in 2023?": "select team,goals_for from standings where season=2023 and competition='Serie A' order by goals_for desc limit 1",
            "What are the largest wins?": "select * from matches order by abs(home_goal-away_goal) desc limit 10",
            "Average league goals per match?": "select avg(home_goal+away_goal) avg_goals from matches where competition='Serie A'",
            "How often did home sides win?": "select avg(home_goal>away_goal) rate from matches",
            "Best away win rate over at least 20 fixtures?": "select team,avg(gf>ga) rate from team_results where venue='away' group by team having count(*)>=20 order by rate desc limit 1",
            "How did the 2018 and 2019 seasons compare?": "select season,avg(home_goal+away_goal) avg_goals from matches where competition='Serie A' and season in(2018,2019) group by season",
            "How did Santos fare against Palmeiras?": "select sum(gf>ga) wins,sum(gf=ga) draws,sum(gf<ga) losses from team_results where team='santos' and opponent='palmeiras'",
            "What derbies were played in 2023?": "select m.date,m.home,m.away from matches m join rivals r on r.first in(m.home,m.away) and r.second in(m.home,m.away) where season=2023",
            "Which Brazilian forwards are in FIFA?": "select name from players where nationality='Brazil' and position in('ST','CF','LW','RW')",
            "Who is Messi?": "select name,nationality,club from players where name like '%Messi%'",
            "Highest-rated players at Santos?": "select name,overall from players where club='santos' order by overall desc",
            "Who played at the Maracana?": "select home,away from raw_matches where json_extract(attributes,'$.Arena') like 'Maracan%'",
            "How many corners did Flamengo earn at home?": "select sum(json_extract(attributes,'$.home_corner')) corners from raw_matches where home='flamengo' and source='BR-Football-Dataset'",
        }
        for question, sql in cases.items():
            with self.subTest(question=question):
                rows = self.rows(sql)
                self.assertTrue(rows)
                self.assertTrue(any(v is not None for v in rows[0].values()))

    def test_missing_scores_aliases_and_paging(self):
        self.assertTrue(self.rows("select * from matches where home_goal is null"))
        result = self.rows("select club_key('São Paulo - SP') a,club_key('Atlético-MG') b,club_key('Atlético-GO') c")[0]
        self.assertEqual(result, {"a": "sao paulo", "b": "atletico mg", "c": "atletico go"})
        page = json.loads(self.call("select id from players order by id")["content"][0]["text"])
        self.assertTrue(page["hasMore"])
        self.assertEqual(len(page["rows"]), 100)
        self.assertTrue(self.call("delete from matches")["isError"])
        self.assertEqual(self.request("missing", {})["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
