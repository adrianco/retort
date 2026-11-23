"""End-to-end scenarios against the server over its MCP stdio transport."""
import json
import subprocess
import time
import unittest


class SoccerScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = subprocess.Popen(["./soccer-mcp"], stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, text=True)
        cls.request_id = 0
        init = cls.rpc("initialize", {"protocolVersion": "2025-06-18"})
        assert "tools" in init["result"]["capabilities"]
        cls.server.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')

    @classmethod
    def tearDownClass(cls):
        cls.server.stdin.close()
        assert cls.server.wait(timeout=5) == 0
        cls.server.stdout.close()

    @classmethod
    def rpc(cls, method, params):
        cls.request_id += 1
        request = dict(jsonrpc="2.0", id=cls.request_id, method=method, params=params)
        cls.server.stdin.write(json.dumps(request) + "\n")
        cls.server.stdin.flush()
        reply = json.loads(cls.server.stdout.readline())
        assert reply["id"] == cls.request_id
        return reply

    def call(self, sql):
        return self.rpc("tools/call", {"name": "query_soccer", "arguments": {"sql": sql}})["result"]

    def rows(self, sql, seconds=2):
        start = time.monotonic()
        reply = self.call(sql)
        self.assertFalse(reply.get("isError"), reply)
        self.assertLess(time.monotonic() - start, seconds)
        return json.loads(reply["content"][0]["text"])["rows"]

    def test_sources_and_discovery(self):
        tool, = self.rpc("tools/list", {})["result"]["tools"]
        self.assertEqual(tool["name"], "query_soccer")
        for source, count in dict(league=4180, cup=1337, libertadores=1255,
                                  historical=6886, extended=10296, players=18207).items():
            self.assertIn(source + "(", tool["description"])
            self.assertEqual(self.rows("select count(*) from " + source), [[count]])

    def test_question_examples(self):
        # Each query represents the tool call an LLM makes for a user question.
        examples = [
            ("Fla-Flu fixtures", "select date,home,away,home_goal,away_goal from derbies where home='flamengo' and away='fluminense'"),
            ("Palmeiras in 2023", "select * from performances where team='palmeiras' and season=2023"),
            ("Cup finals", "select * from matches where competition='Copa do Brasil' and stage='final'"),
            ("Corinthians home record", "select sum(gf>ga),sum(gf=ga),sum(gf<ga) from performances where team=team('Sport Club Corinthians Paulista') and venue='home' and season=2022"),
            ("Highest scoring team", "select team,goals_for from standings where competition='Serie A' and season=2023 order by goals_for desc limit 1"),
            ("Head-to-head", "select team,opponent,sum(gf>ga),sum(gf=ga),sum(gf<ga) from performances where team='palmeiras' and opponent='santos' group by team,opponent"),
            ("Brazilian players", "select Name from players where Nationality='Brazil'"),
            ("Santos forwards", "select Name from players where team(Club)='santos' and Position in ('ST','CF','LW','RW')"),
            ("Brazilian ratings", "select Name,Overall from players where Nationality='Brazil' order by Overall desc"),
            ("Player attributes", "select Name,Dribbling,Finishing from players where fold(Name) like '%neymar%'"),
            ("Libertadores bracket", "select stage,date,home,away from matches where season=2018 and competition='Libertadores' and stage!='group stage' order by date"),
            ("Bottom four", "select team from standings where competition='Serie A' and season=2020 order by points,wins,gd,goals_for limit 4"),
            ("Goals per game", "select avg(home_goal+away_goal) from matches where competition='Serie A'"),
            ("Best away record", "select team,avg(gf>ga) rate from performances where venue='away' group by team order by rate desc"),
            ("Biggest wins", "select * from matches order by abs(home_goal-away_goal) desc limit 10"),
            ("Latest meeting", "select date,gf,ga from performances where team='flamengo' and opponent='corinthians' order by date desc limit 1"),
            ("Derbies by year", "select * from derbies where season=2023"),
            ("Palmeiras competitions", "select distinct competition from performances where team='palmeiras'"),
            ("Season comparison", "select season,avg(home_goal+away_goal) from matches where season in (2018,2019) group by season"),
            ("Rated players on winning teams", "select p.Name,s.team from players p join standings s on team(p.Club)=s.team where s.competition='Serie A' and s.season=2019 and s.wins>s.losses limit 10"),
            ("Date range", "select date from matches where date between '2003-03-29' and '2003-03-30'"),
        ]
        for question, sql in examples:
            with self.subTest(question=question):
                self.assertTrue(self.rows(sql, 5))

    def test_known_answers(self):
        self.assertEqual(self.rows("select team,played,wins,draws,losses,points from standings where competition='Serie A' and season=2019 order by points desc limit 1"), [["flamengo",38,28,6,4,90]])
        self.assertEqual(self.rows("select Name,Overall from players where Nationality='Brazil' order by Overall desc limit 1"), [["Neymar Jr",92]])
        self.assertEqual(self.rows("select team('Grêmio - RS'),team('São Paulo FC'),team('Atlético-MG')=team('Atletico Mineiro'),team('Atlético-GO')=team('Atlético-MG')"), [["gremio","sao paulo",1,0]])
        self.assertEqual(self.rows("select count(*) from matches where competition='Serie A' and season=2019"), [[380]])
        self.assertEqual(self.rows("select home_goal,away_goal from matches where date='2003-03-29' and home='guarani'"), [[4,2]])
        self.assertEqual(self.rows("select count(*) from matches where competition='Copa do Brasil' and season=2012 and stage='final'"), [[2]])

        self.assertEqual(self.rows("select home,away,home_goal,away_goal from matches where competition='Copa do Brasil' and season=2023 and stage='final' order by date"), [["flamengo","sao paulo",0,1],["sao paulo","flamengo",1,1]])

    def test_errors_and_pagination(self):
        for sql in ["delete from matches", "select 1;select 2", "select nonexistent from matches"]:
            self.assertTrue(self.call(sql)["isError"])
        result = json.loads(self.call("select ID from players order by ID")["content"][0]["text"])
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["rows"]), 200)
        self.assertNotIn(self.rows("select ID from players order by ID limit 1 offset 200")[0], result["rows"])


if __name__ == "__main__":
    unittest.main()
