"""The specification's sample questions, wired to the real MCP tools.

Context
-------
The specification asks for "at least 20 sample questions" to be answerable.
:data:`SAMPLE_QUESTIONS` lists 30 of them -- every example question in the spec
plus the whole "Sample Questions and Expected Behaviours" table -- as
``(question, tool, arguments)`` triples.

:func:`run_demo` answers them by calling the tools *through the MCP server*, so
what you see here is exactly what an LLM client receives; ``tests/test_demo.py``
uses the same list as an acceptance test.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import anyio

from .graph import KnowledgeGraph
from .server import build_server

__all__ = ["SampleQuestion", "SAMPLE_QUESTIONS", "run_demo", "answer_question"]


@dataclass(frozen=True, slots=True)
class SampleQuestion:
    """A natural language question and the tool call that answers it."""

    question: str
    tool: str
    arguments: dict[str, Any]


def _q(question: str, tool: str, **arguments: Any) -> SampleQuestion:
    return SampleQuestion(question=question, tool=tool, arguments=arguments)


SAMPLE_QUESTIONS: tuple[SampleQuestion, ...] = (
    # -- Match queries ---------------------------------------------------
    _q("Show me all Flamengo vs Fluminense matches",
       "find_matches", team="Flamengo", opponent="Fluminense", limit=8),
    _q("What matches did Palmeiras play in 2023?",
       "find_matches", team="Palmeiras", season=2023, limit=8),
    _q("Find all Copa do Brasil finals",
       "find_matches", competition="Copa do Brasil", stage="Final", limit=10),
    _q("When did Flamengo last play Corinthians, and what was the score?",
       "find_matches", team="Flamengo", opponent="Corinthians", limit=1),
    _q("Which Flamengo matches were played away in the 2022 Brasileirão?",
       "find_matches", team="Flamengo", season=2022, competition="Serie A",
       home_away="away", limit=5),
    _q("What happened in the Libertadores between March and May 2019?",
       "find_matches", competition="Libertadores", date_from="2019-03-01",
       date_to="2019-05-31", limit=5),
    # -- Team queries ----------------------------------------------------
    _q("What is Corinthians' home record in 2022?",
       "team_stats", team="Corinthians", season=2022, competition="Serie A", home_away="home"),
    _q("Which team scored the most goals in Série A 2023?",
       "team_rankings", metric="goals_for", competition="Serie A", season=2023, limit=5),
    _q("Compare Palmeiras and Santos head-to-head",
       "head_to_head", team_a="Palmeiras", team_b="Santos"),
    _q("Which team has the best home record in the Brasileirão?",
       "team_rankings", metric="win_rate", competition="Serie A", home_away="home", limit=5),
    _q("Which team has the best away record?",
       "team_rankings", metric="points_per_game", home_away="away", limit=5),
    _q("What competitions has Palmeiras played in?", "team_profile", team="Palmeiras"),
    _q("Tell me about Grêmio", "team_profile", team="Gremio"),
    _q("How did Vasco da Gama do in 2020?", "team_stats", team="Vasco", season=2020),
    # -- Player queries --------------------------------------------------
    _q("Find all Brazilian players in the dataset",
       "search_players", nationality="Brazil", limit=10),
    _q("Who is Gabriel Barbosa?", "player_profile", name="Gabriel Barbosa"),
    _q("Who are the highest-rated players at Grêmio?",
       "search_players", club="Grêmio", limit=5),
    _q("Show me all forwards from Cruzeiro",
       "search_players", club="Cruzeiro", position="ST,CF,LW,RW", limit=10),
    _q("Which players play for Flamengo?", "team_squad", team="Flamengo"),
    _q("Show me the Santos squad and how the club performed",
       "team_squad", team="Santos", limit=8),
    _q("Which Brazilian players are rated 85 or higher?",
       "search_players", nationality="Brazil", min_overall=85, limit=10),
    # -- Competition queries ---------------------------------------------
    _q("Who won the 2019 Brasileirão?", "standings", competition="Brasileirão", season=2019),
    _q("Which teams were relegated in 2020?", "standings", competition="Serie A", season=2020),
    _q("Show the 2018 Copa Libertadores bracket",
       "knockout_bracket", competition="Libertadores", season=2018),
    _q("Who won the 2019 Copa do Brasil?",
       "knockout_bracket", competition="Copa do Brasil", season=2019),
    _q("Compare the 2018 and 2019 seasons",
       "compare_seasons", competition="Serie A", seasons=[2018, 2019]),
    # -- Statistical analysis --------------------------------------------
    _q("What's the average goals per match in the Brasileirão?",
       "competition_stats", competition="Serie A"),
    _q("Show me the biggest wins in the dataset", "biggest_wins", limit=5),
    _q("Show me all derbies in 2023", "derbies", season=2023, limit=10),
    _q("What does this dataset cover?", "dataset_overview"),
    _q("Which club is 'Timão' and how is the name spelled in the files?",
       "search_teams", query="Timão"),
)


async def _answer(server: Any, question: SampleQuestion) -> str:
    result = await server.call_tool(question.tool, dict(question.arguments))
    return "\n".join(
        block.text for block in result.content if getattr(block, "text", None)
    )


def answer_question(
    question: SampleQuestion, graph: KnowledgeGraph | None = None, server: Any = None
) -> str:
    """Answer one sample question through the MCP tool layer."""
    instance = server or build_server(graph=graph)
    return anyio.run(_answer, instance, question)


def run_demo(
    graph: KnowledgeGraph | None = None,
    questions: Sequence[SampleQuestion] | None = None,
) -> list[tuple[SampleQuestion, str]]:
    """Answer every sample question, returning ``(question, answer)`` pairs."""
    selected = list(questions if questions is not None else SAMPLE_QUESTIONS)
    server = build_server(graph=graph)

    async def _run() -> list[tuple[SampleQuestion, str]]:
        return [(question, await _answer(server, question)) for question in selected]

    return anyio.run(_run)


def render_demo(pairs: Iterable[tuple[SampleQuestion, str]]) -> str:
    """Format demo output as a readable transcript."""
    blocks = []
    for index, (question, answer) in enumerate(pairs, start=1):
        arguments = ", ".join(f"{key}={value!r}" for key, value in question.arguments.items())
        blocks.append(
            f"{'=' * 78}\nQ{index}. {question.question}\n"
            f"     -> {question.tool}({arguments})\n{'-' * 78}\n{answer}"
        )
    return "\n".join(blocks)


if __name__ == "__main__":  # pragma: no cover
    print(render_demo(run_demo()))
