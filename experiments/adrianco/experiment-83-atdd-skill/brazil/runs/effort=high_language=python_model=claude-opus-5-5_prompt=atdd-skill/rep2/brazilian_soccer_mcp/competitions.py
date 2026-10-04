"""
Competitions and knockout stages, named consistently across datasets.

Each dataset names competitions differently ("Serie A" in the extended
statistics, implied by the file for the others); questions name them
differently again ("Brasileirão", "the cup", "Libertadores"). Everything is
mapped to one canonical name.
"""
from .text import plain

SERIE_A = "Brasileirão Série A"
SERIE_B = "Brasileirão Série B"
SERIE_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

ALL = (SERIE_A, SERIE_B, SERIE_C, COPA_DO_BRASIL, LIBERTADORES)
LEAGUES = (SERIE_A, SERIE_B, SERIE_C)
CUPS = (COPA_DO_BRASIL, LIBERTADORES)

_NAMES = [
    (("libertadores", "copa libertadores", "conmebol libertadores"), LIBERTADORES),
    (("copa do brasil", "brazilian cup", "brazil cup", "cup", "copa"), COPA_DO_BRASIL),
    (("serie b", "brasileirao serie b", "b"), SERIE_B),
    (("serie c", "brasileirao serie c", "c"), SERIE_C),
    (("serie a", "brasileirao", "brasileirao serie a", "brasileiro", "campeonato brasileiro", "a", "league",
      "brazilian league", "brasileirao a"), SERIE_A),
]

# Names specific enough to recognise inside a longer phrase ("Copa Libertadores da América")
_DISTINCTIVE = {"libertadores", "copa do brasil", "brazilian cup", "serie a", "serie b", "serie c", "brasileirao",
                "brasileiro"}

KNOCKOUT_STAGES = ("round of 16", "quarterfinals", "semifinals", "final")
_STAGE_NAMES = {
    "final": "final", "finals": "final", "semifinal": "semifinals", "semifinals": "semifinals",
    "semi final": "semifinals", "semi finals": "semifinals", "semis": "semifinals",
    "quarterfinal": "quarterfinals", "quarterfinals": "quarterfinals", "quarter final": "quarterfinals",
    "quarter finals": "quarterfinals", "round of 16": "round of 16", "last 16": "round of 16",
    "group stage": "group stage", "group": "group stage", "groups": "group stage",
}


class UnknownCompetition(LookupError):
    pass


def resolve(question):
    """'Brasileirão' -> 'Brasileirão Série A', 'copa do brasil' -> 'Copa do Brasil', ..."""
    wanted = plain(question)
    for canonical in ALL:
        if wanted == plain(canonical):
            return canonical
    for names, canonical in _NAMES:
        if wanted in names:
            return canonical
    for names, canonical in _NAMES:
        if any(name in wanted for name in names if name in _DISTINCTIVE):
            return canonical
    raise UnknownCompetition(f"Unknown competition {question!r}. Known competitions: {', '.join(ALL)}.")


def stage_name(question):
    wanted = plain(question)
    if wanted in _STAGE_NAMES:
        return _STAGE_NAMES[wanted]
    if wanted.startswith("round "):
        return wanted.capitalize()
    return wanted
