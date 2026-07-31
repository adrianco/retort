"""Competition registry.

Context
-------
The datasets label competitions inconsistently (``"Serie A"`` in the
BR-Football file, nothing at all in the Brasileirão/Copa/Libertadores files
which are implicitly single-competition) and users will type anything from
``"brasileirao"`` to ``"Campeonato Brasileiro Série A"``.  This module owns the
canonical slugs used everywhere else plus the alias table for user input.
"""

from __future__ import annotations

from dataclasses import dataclass

from .normalization import normalize_text

__all__ = ["Competition", "COMPETITIONS", "resolve_competition", "competition_name"]


@dataclass(frozen=True)
class Competition:
    slug: str
    name: str
    short_name: str
    kind: str  # "league" or "cup"
    aliases: tuple[str, ...] = ()


COMPETITIONS: tuple[Competition, ...] = (
    Competition(
        "serie-a", "Campeonato Brasileiro Série A", "Brasileirão", "league",
        ("serie a", "série a", "brasileirao", "brasileirão", "campeonato brasileiro",
         "campeonato brasileiro serie a", "brazilian league", "brasileirao serie a",
         "brasileirao a", "first division", "primeira divisao"),
    ),
    Competition(
        "serie-b", "Campeonato Brasileiro Série B", "Série B", "league",
        ("serie b", "série b", "brasileirao serie b", "second division",
         "segunda divisao", "brasileirao b"),
    ),
    Competition(
        "serie-c", "Campeonato Brasileiro Série C", "Série C", "league",
        ("serie c", "série c", "brasileirao serie c", "third division",
         "terceira divisao", "brasileirao c"),
    ),
    Competition(
        "copa-do-brasil", "Copa do Brasil", "Copa do Brasil", "cup",
        ("copa do brasil", "brazilian cup", "copa brasil", "cup"),
    ),
    Competition(
        "libertadores", "Copa Libertadores", "Libertadores", "cup",
        ("libertadores", "copa libertadores", "conmebol libertadores",
         "copa libertadores da america", "south american cup"),
    ),
)

_BY_SLUG = {c.slug: c for c in COMPETITIONS}

_ALIAS_INDEX: dict[str, str] = {}
for _c in COMPETITIONS:
    for _alias in (_c.slug, _c.name, _c.short_name, *_c.aliases):
        _ALIAS_INDEX.setdefault(normalize_text(_alias), _c.slug)


def resolve_competition(value: str | None) -> str | None:
    """Map a user-supplied competition name to its canonical slug.

    Returns ``None`` for empty input (meaning "all competitions").  Raises
    :class:`ValueError` for an unrecognised name so the MCP layer can report a
    helpful message instead of silently returning an empty result set.
    """
    if value is None:
        return None
    text = normalize_text(value)
    if not text or text in {"all", "any"}:
        return None
    if text in _ALIAS_INDEX:
        return _ALIAS_INDEX[text]
    # Tolerate "brasileirao 2019" style input.
    stripped = " ".join(tok for tok in text.split() if not tok.isdigit())
    if stripped in _ALIAS_INDEX:
        return _ALIAS_INDEX[stripped]
    known = ", ".join(sorted(_BY_SLUG))
    raise ValueError(f"Unknown competition {value!r}. Known competitions: {known}")


def competition_name(slug: str | None) -> str:
    """Return the display name for a competition slug."""
    if slug is None:
        return "All competitions"
    comp = _BY_SLUG.get(slug)
    return comp.name if comp else slug


def competition(slug: str) -> Competition | None:
    return _BY_SLUG.get(slug)
