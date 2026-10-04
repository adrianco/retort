"""
DSL (layer 2): the vocabulary specs use to describe Brazilian football.

SoccerDsl is the single entry point a spec receives. It groups the language
by domain area:

  soccer.given         - what the datasets record (matches, players, seasons)
  soccer.matches       - finding matches and meetings
  soccer.teams         - team records, head-to-heads, club profiles
  soccer.competitions  - league tables, champions, relegation, brackets
  soccer.stats         - aggregate statistics
  soccer.players       - player search and rankings
"""
from .given import Given
from .queries import Competitions, Matches, Players, Statistics, Teams


class SoccerDsl:
    def __init__(self, server, datasets=None):
        self._server = server
        self.given = Given(datasets) if datasets else None
        self.matches = Matches(server)
        self.teams = Teams(server)
        self.competitions = Competitions(server)
        self.stats = Statistics(server)
        self.players = Players(server)

    def confirm_datasets_loaded(self, row_counts):
        self._server.confirm_datasets_loaded(row_counts)

    def confirm_answered(self, question, ask, within_seconds):
        self._server.confirm_answered(question, lambda: ask(self), within_seconds)
