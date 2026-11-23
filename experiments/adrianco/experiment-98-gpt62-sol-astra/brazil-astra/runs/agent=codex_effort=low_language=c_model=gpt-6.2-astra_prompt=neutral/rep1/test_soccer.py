"""Behavior scenarios against the same stdio entry point an MCP client uses."""
import json
import subprocess
import time
import unittest


class SoccerScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = subprocess.Popen(["./soccer-mcp"], stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.server.stdin.close()
        cls.server.stdout.close()
        if cls.server.wait(timeout=5):
            raise RuntimeError("Server exited unsuccessfully")

    def rpc(self, method, **params):
        request = dict(jsonrpc="2.0", id="request", method=method, params=params)
        self.server.stdin.write(json.dumps(request) + "\n")
        self.server.stdin.flush()
        reply = json.loads(self.server.stdout.readline())
        self.assertEqual(reply["id"], "request")
        return reply

    def call(self, sql):
        return self.rpc("tools/call", name="query_soccer", arguments={"sql": sql})["result"]

    def rows(self, sql, seconds=2):
        start = time.monotonic()
        result = self.call(sql)
        self.assertFalse(result["isError"], result)
        self.assertLess(time.monotonic() - start, seconds)
        return json.loads(result["content"][0]["text"])["rows"]

    def test_client_discovers_graph(self):
        init = self.rpc("initialize", protocolVersion="2024-11-05")["result"]
        self.assertEqual(init["protocolVersion"], "2024-11-05")
        self.assertIn("tools", init["capabilities"])
        self.assertEqual(self.rpc("tools/list")["result"]["tools"][0]["name"], "query_soccer")

    def test_source_coverage(self):
        for table, count in dict(league=4180, cup=1337, libertadores=1255,
                                 historical=6886, extended=10296, players=18207).items():
            self.assertEqual(self.rows(f"select count(*) from {table}"), [[count]])
        self.assertEqual(self.rows("select min(date) from reports where source='historical'"),
                         [["2003-03-29"]])
        self.assertTrue(self.rows("select total_corners,home_shots from extended where total_corners>4"))

    def test_match_questions(self):
        pair = "from appearances where team='flamengo' and opponent='fluminense'"
        self.assertGreater(self.rows("select count(*) " + pair)[0][0], 20)
        self.assertGreaterEqual(self.rows("select max(date) " + pair)[0][0], "2023")
        self.assertTrue(self.rows("select home,away,date,home_goal,away_goal,competition from matches "
                                  "where home_key='flamengo' and away_key='corinthians' order by date desc limit 1"))
        self.assertTrue(self.rows("select date from appearances where team='palmeiras' and season=2023"))
        self.assertEqual(self.rows("select distinct season from matches where date between '2003-03-29' and '2003-04-01'"), [[2003]])
        self.assertEqual(self.rows("select count(*) from matches where competition='Copa do Brasil' and stage='final'"), [[18]])
        self.assertTrue(self.rows("select home,away from matches where competition='Libertadores' and season=2018 and stage='final'"))
        self.assertTrue(self.rows("select home,away from derbies where season=2023"))
        self.assertGreater(len(self.rows("select distinct competition from appearances where team='palmeiras'")), 2)

    def test_team_statistics(self):
        self.assertEqual(self.rows("select team,points,played,wins,draws,losses from standings "
                                   "where competition='Serie A' and season=2019 order by points desc limit 1", 5),
                         [["flamengo", 90, 38, 28, 6, 4]])
        self.assertEqual(len(self.rows("select team from standings where season=2020 and competition='Serie A' "
                                       "order by points,wins,gd,goals_for limit 4", 5)), 4)
        self.assertTrue(self.rows("select team,goals_for from standings where season=2023 and competition='Serie A' "
                                  "order by goals_for desc limit 1", 5))
        self.assertEqual(self.rows("select count(*) from appearances where venue='home' and season=2022 "
                                   "and competition='Serie A' and team=team_key('Sport Club Corinthians Paulista')"), [[19]])
        self.assertEqual(self.rows("select team_key('Grêmio - RS'),team_key('São Paulo-SP'),"
                                   "team_key('Atlético-MG')!=team_key('Atlético-PR')"), [["gremio","sao paulo",1]])
        self.assertTrue(self.rows("select team,avg(gf>ga) from appearances where venue='away' and gf>=0 and ga>=0 "
                                  "group by team having count(*)>=20 order by 2 desc limit 1", 5))
        self.assertGreater(self.rows("select max(abs(home_goal-away_goal)) from matches")[0][0], 6)
        self.assertEqual(len(self.rows("select season,avg(home_goal+away_goal) from matches where season in (2018,2019) "
                                       "and competition='Serie A' group by season", 5)), 2)

    def test_player_relationships(self):
        self.assertEqual(self.rows("select Name from players where Nationality='Brazil' order by Overall desc limit 1"),
                         [["Neymar Jr"]])
        self.assertTrue(self.rows("select Position,Finishing from players where Name like '%Neymar%'"))
        self.assertTrue(self.rows("select Name from players where team_key(Club)='santos' order by Overall desc"))
        self.assertTrue(self.rows("select Name from players where Position in ('ST','CF','LW','RW') and Nationality='Brazil'"))
        self.assertTrue(self.rows("select p.Name,s.points from players p join standings s on team_key(p.Club)=s.team "
                                  "where s.team='santos' and s.season=2019 and s.competition='Serie A' limit 1", 5))

    def test_error_recovery_and_pagination(self):
        self.assertTrue(self.call("delete from matches")["isError"])
        self.assertTrue(self.call("select 1; select 2")["isError"])
        self.assertTrue(self.call("select missing from matches")["isError"])
        self.assertEqual(self.rpc("missing")["error"]["code"], -32601)
        result = json.loads(self.call("select ID from players order by ID")["content"][0]["text"])
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["rows"]), 200)
        self.assertEqual(self.rows("select 42"), [[42]])


if __name__ == "__main__":
    unittest.main()
