"""The MCP tools: what an AI assistant can ask, and how each question is answered."""
from dataclasses import dataclass

from brazilian_soccer_mcp import answers
from brazilian_soccer_mcp.knowledge import METRICS


def _string(description):
    return {"type": "string", "description": description}


def _integer(description, minimum=None):
    schema = {"type": "integer", "description": description}
    if minimum is not None:
        schema["minimum"] = minimum
    return schema


TEAM = _string("Club name in any common spelling, e.g. 'Flamengo', 'Palmeiras-SP', 'Sao Paulo', 'Atlético Mineiro'")
OPPONENT = _string("Second club, to restrict to matches between the two")
COMPETITION = _string("Brasileirão (Serie A), Série B, Série C, Copa do Brasil or Copa Libertadores")
SEASON = _integer("Season year, e.g. 2019")
VENUE = {"type": "string", "enum": ["any", "home", "away"], "description": "Only the team's home or away matches"}
LIMIT = _integer("Maximum number of results to list", minimum=1)


@dataclass
class Tool:
    name: str
    title: str
    description: str
    properties: dict
    required: tuple = ()

    @property
    def definition(self):
        return {"name": self.name, "title": self.title, "description": self.description,
                "inputSchema": {"type": "object", "properties": self.properties, "required": list(self.required)},
                "annotations": {"readOnlyHint": True, "openWorldHint": False}}

    def call(self, knowledge, arguments):
        arguments = {key: value for key, value in (arguments or {}).items()
                     if key in self.properties and value is not None and value != ""}
        answer = getattr(knowledge, self.name)(**arguments)
        return answer, getattr(answers, self.name)(answer, arguments)


TOOLS = [
    Tool("search_matches", "Find matches",
         "Find matches from every dataset (Brasileirão 2003-2023, Série B/C, Copa do Brasil, Copa Libertadores) "
         "by team, opponent, home/away, competition, season, date range or stage (e.g. 'final'). Most recent first. "
         "With two teams it also gives the head-to-head summary. Use for 'Show me all Flamengo vs Fluminense "
         "matches', 'When did Flamengo last play Corinthians?', 'Find all Copa do Brasil finals'.",
         {"team": TEAM, "opponent": OPPONENT, "venue": VENUE, "competition": COMPETITION, "season": SEASON,
          "date_from": _string("Earliest date, YYYY-MM-DD"), "date_to": _string("Latest date, YYYY-MM-DD"),
          "stage": _string("Knockout stage: final, semifinals, quarterfinals, round of 16, group stage"),
          "limit": LIMIT}),
    Tool("head_to_head", "Head-to-head record",
         "Compare two clubs head-to-head: wins for each side, draws, goals and recent meetings, naming the "
         "traditional derby (Fla-Flu, Grenal, Derby Paulista...) when there is one.",
         {"team": TEAM, "opponent": OPPONENT, "competition": COMPETITION, "season": SEASON, "limit": LIMIT},
         ("team", "opponent")),
    Tool("find_derbies", "Find derbies",
         "List traditional derby matches (Fla-Flu, Clássico dos Milhões, Derby Paulista, Choque-Rei, Majestoso, "
         "Grenal, Clássico Mineiro, Ba-Vi, Atletiba...) for a season, competition or club.",
         {"season": SEASON, "competition": COMPETITION, "team": TEAM, "limit": LIMIT}),
    Tool("team_record", "Team record",
         "A club's record (matches, wins, draws, losses, goals for and against, win rate), optionally for one "
         "season, competition, venue (home/away) or opponent. Use for 'What is Corinthians' home record in 2022?'.",
         {"team": TEAM, "season": SEASON, "competition": COMPETITION, "venue": VENUE, "opponent": OPPONENT},
         ("team",)),
    Tool("team_overview", "Team overview",
         "Everything about a club across the datasets: overall record, the competitions and seasons it played, "
         "derby rivals, recent matches and its players in the FIFA database.",
         {"team": TEAM}, ("team",)),
    Tool("standings", "League standings",
         "League table calculated from match results (3 points a win, ties broken by wins, goal difference, goals "
         "scored), with the champion and relegated clubs. Use for 'Who won the 2019 Brasileirão?' or 'Which teams "
         "were relegated in 2020?'.",
         {"season": SEASON, "competition": COMPETITION}, ("season",)),
    Tool("knockout_bracket", "Knockout bracket",
         "The knockout stages of a Copa do Brasil or Copa Libertadores season, with each tie's legs, aggregate "
         "score and winner.",
         {"competition": COMPETITION, "season": SEASON}, ("competition", "season")),
    Tool("competition_stats", "Competition statistics",
         "Goals per match and home win / away win / draw rates for a competition, season or club's matches. Use for "
         "'What's the average goals per match in the Brasileirão?'.",
         {"competition": COMPETITION, "season": SEASON, "team": TEAM}),
    Tool("compare_seasons", "Compare seasons",
         "Compare seasons of a competition side by side: matches, goals per match, home win and draw rates, "
         "champion and highest-scoring team.",
         {"seasons": {"type": "array", "items": {"type": "integer"}, "description": "Season years, e.g. [2018, 2019]"},
          "competition": COMPETITION}, ("seasons",)),
    Tool("biggest_wins", "Biggest wins",
         "The largest winning margins, optionally for a competition, season or club.",
         {"competition": COMPETITION, "season": SEASON, "team": TEAM, "limit": LIMIT}),
    Tool("rank_teams", "Rank teams",
         "Rank clubs by a measure (win_rate, points, wins, goals_scored, goals_conceded, goal_difference, losses), "
         "optionally home or away only, for a competition or season. Use for 'Which team has the best away "
         "record?' or 'Which team scored the most goals in Serie A 2023?'.",
         {"metric": {"type": "string", "enum": list(METRICS), "description": "What to rank by"}, "venue": VENUE,
          "competition": COMPETITION, "season": SEASON,
          "min_matches": _integer("Ignore clubs with fewer matches (default: a quarter of the most played)", 1),
          "limit": LIMIT}),
    Tool("search_players", "Find players",
         "Search the FIFA player database by name, nationality ('Brazil' or 'Brazilian'), club, position (a code "
         "like ST or a group: forward, midfielder, defender, goalkeeper) and minimum rating. Highest rated first.",
         {"name": _string("All or part of the player's name"), "nationality": _string("Country or nationality"),
          "club": _string("Club name in any common spelling"), "position": _string("Position code or group"),
          "min_overall": _integer("Minimum FIFA overall rating"), "limit": LIMIT}),
    Tool("get_player", "Player profile",
         "Full profile of one player from the FIFA database: club, position, ratings, physical details and best "
         "attributes. Use for 'Who is Gabriel Jesus?'.",
         {"name": _string("Player name; accents optional")}, ("name",)),
    Tool("club_squads", "Club squads",
         "Count and average rating of players per club, e.g. Brazilian players at Brazilian clubs (clubs that play "
         "in Brazilian competitions in the match data).",
         {"nationality": _string("Only players of this nationality"),
          "brazilian_clubs_only": {"type": "boolean", "description": "Only clubs that play in Brazilian competitions"},
          "club": _string("Only this club"), "limit": LIMIT}),
    Tool("dataset_summary", "Dataset summary",
         "Which datasets are loaded, how many records each holds, and the competitions and seasons covered.", {}),
]

TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}
