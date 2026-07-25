"""Team registry: raw dataset names -> canonical clubs, and user queries -> clubs.

Resolution happens in two passes because the correct id for a bare name depends
on what else exists in the data:

1. Every raw name found in the CSVs is *observed*; curated clubs
   (:mod:`brazilian_soccer.normalization`) claim the names they know.
2. :meth:`TeamRegistry.build` looks at the leftovers. When one slug appears with
   several states (``Santa Cruz`` in PE, RN and RS) the state is folded into the
   id; when it only ever appears with one state, the state-less and stated
   spellings are merged into a single club.

Lookups from natural language go through :meth:`TeamRegistry.resolve`, which
tries exact ids, curated aliases, observed spellings, substring matches and
finally fuzzy matching.
"""

from __future__ import annotations

import difflib
from collections import Counter, defaultdict

from .models import Team
from .normalization import (
    ParsedName,
    lookup_curated,
    parse_team_name,
    slugify,
    strip_accents,
)


#: Country of clubs that only appear in the FIFA player file.
UNKNOWN_COUNTRY = "Unknown"


def _prettiness(name: str) -> tuple[int, int, int]:
    """Rank raw spellings so the nicest one becomes the display name.

    Prefers accented, mixed-case, longer spellings — ``Grêmio`` over ``GREMIO``
    over ``Gremio-RS``.
    """
    has_accent = int(strip_accents(name) != name)
    not_shouty = int(not name.isupper())
    return (has_accent, not_shouty, len(name))


class TeamRegistry:
    """Maps every spelling of a club onto one :class:`~.models.Team`."""

    def __init__(self) -> None:
        self._observations: dict[str, ParsedName] = {}      # raw -> parsed
        self._counts: Counter[str] = Counter()              # raw -> occurrences
        self._brazilian: set[str] = set()                   # raws seen in match data
        self._raw_to_id: dict[str, str] = {}
        self._teams: dict[str, Team] = {}
        self._alias_index: dict[str, set[str]] = defaultdict(set)  # slug -> ids
        self._built = False

    # -- pass 1 ------------------------------------------------------------- #

    def observe(self, raw: str, brazilian: bool = True) -> None:
        """Record a raw team name seen in a dataset.

        ``brazilian`` marks names that come from the Brazilian match files; the
        FIFA player file also contributes European and Asian clubs, which should
        not be labelled as Brazilian in the club list.
        """
        if raw is None:
            return
        text = str(raw).strip()
        if not text or text.lower() == "nan":
            return
        self._counts[text] += 1
        if brazilian:
            self._brazilian.add(text)
        if text not in self._observations:
            self._observations[text] = parse_team_name(text)
        self._built = False

    # -- pass 2 ------------------------------------------------------------- #

    def build(self) -> None:
        """Resolve every observed name into a canonical team."""
        curated_hits: dict[str, list[str]] = defaultdict(list)   # team_id -> raws
        leftovers: list[str] = []

        for raw, parsed in self._observations.items():
            club = lookup_curated(parsed.slug, parsed.state)
            if club is not None:
                curated_hits[club.team_id].append(raw)
            else:
                leftovers.append(raw)

        # Which slugs are ambiguous (same name, different states)? Curated
        # observations count too: "Náutico-PE" is curated and "Nautico - RR"
        # is not, but the leftover must still keep its state in its id or it
        # would be handed the curated club's id and merged into Náutico.
        states_by_slug: dict[str, set[str]] = defaultdict(set)
        for parsed in self._observations.values():
            if parsed.state:
                states_by_slug[parsed.slug].add(parsed.state)

        curated_ids = {club.team_id for club in
                       (lookup_curated(p.slug, p.state)
                        for p in self._observations.values()) if club}

        groups: dict[str, list[str]] = defaultdict(list)
        for raw in leftovers:
            parsed = self._observations[raw]
            ambiguous = len(states_by_slug.get(parsed.slug, ())) > 1
            if ambiguous and parsed.state:
                team_id = f"{slugify(parsed.slug).replace(' ', '-')}-{parsed.state.lower()}"
            elif ambiguous:
                # A bare spelling of an ambiguous name: attach it to the most
                # frequently seen state variant.
                best_state = max(
                    states_by_slug[parsed.slug],
                    key=lambda st: sum(
                        self._counts[r]
                        for r in leftovers
                        if self._observations[r].slug == parsed.slug
                        and self._observations[r].state == st
                    ),
                )
                team_id = f"{slugify(parsed.slug).replace(' ', '-')}-{best_state.lower()}"
            else:
                team_id = slugify(parsed.slug).replace(" ", "-")
                if team_id in curated_ids:
                    # Belt and braces: never let a generic name land on a
                    # curated club's id and silently merge two clubs.
                    suffix = (parsed.state or parsed.country).lower()
                    team_id = f"{team_id}-{suffix}"
            groups[team_id].append(raw)

        for team_id, raws in curated_hits.items():
            groups[team_id].extend(raws)

        self._teams.clear()
        self._raw_to_id.clear()
        self._alias_index.clear()

        curated_by_id = {}
        for raw, parsed in self._observations.items():
            club = lookup_curated(parsed.slug, parsed.state)
            if club is not None:
                curated_by_id[club.team_id] = club

        for team_id, raws in groups.items():
            parsed_names = [self._observations[r] for r in raws]
            club = curated_by_id.get(team_id)
            if club is not None:
                name, state, country = club.display, club.state, club.country
            else:
                name = max(raws, key=_prettiness)
                # Display the identifying part without the state suffix.
                pretty = max(
                    (p for p in parsed_names if p.raw == name), key=lambda p: len(p.raw)
                )
                name = _display_from_raw(pretty)
                state = next((p.state for p in parsed_names if p.state), None)
                country = next(
                    (p.country for p in parsed_names if p.country != "Brazil"),
                    "Brazil" if any(r in self._brazilian for r in raws) else UNKNOWN_COUNTRY,
                )
            aliases = {slugify(r) for r in raws} | {p.slug for p in parsed_names}
            aliases.add(slugify(name))
            team = Team(
                team_id=team_id,
                name=name,
                state=state,
                country=country,
                aliases=frozenset(aliases),
            )
            self._teams[team_id] = team
            for raw in raws:
                self._raw_to_id[raw] = team_id
            for alias in aliases:
                self._alias_index[alias].add(team_id)
        self._built = True

    # -- lookups ------------------------------------------------------------ #

    @property
    def teams(self) -> dict[str, Team]:
        self._ensure_built()
        return self._teams

    def _ensure_built(self) -> None:
        if not self._built:
            self.build()

    def team_id_for_raw(self, raw: str) -> str | None:
        """Canonical id for a raw dataset spelling."""
        self._ensure_built()
        return self._raw_to_id.get(str(raw).strip())

    def get(self, team_id: str) -> Team | None:
        self._ensure_built()
        return self._teams.get(team_id)

    def name_of(self, team_id: str) -> str:
        team = self.get(team_id)
        return team.name if team else team_id

    def resolve(self, query: str, limit: int = 5) -> list[Team]:
        """Best-effort resolution of a free-text club name.

        Returns candidates ordered best-first; empty when nothing looks close.
        """
        self._ensure_built()
        if query is None:
            return []
        text = str(query).strip()
        if not text:
            return []

        if text in self._teams:                       # already a canonical id
            return [self._teams[text]]

        parsed = parse_team_name(text)
        plain = slugify(text)

        for key in (parsed.slug, plain):
            club = lookup_curated(key, parsed.state)
            if club is not None and club.team_id in self._teams:
                return [self._teams[club.team_id]]

        for key in (parsed.slug, plain, plain.replace(" ", "-")):
            ids = self._alias_index.get(key)
            if ids:
                found = [self._teams[i] for i in sorted(ids)]
                if parsed.state:
                    stated = [t for t in found if t.state == parsed.state]
                    if stated:
                        return stated
                return self._rank(found, parsed.slug)[:limit]

        needle = parsed.slug or plain
        if len(needle) >= 3:
            partial = [
                team
                for team in self._teams.values()
                if any(needle == alias or _starts_word(alias, needle) for alias in team.aliases)
            ]
            if partial:
                return self._rank(partial, needle)[:limit]

        close = difflib.get_close_matches(needle, list(self._alias_index), n=limit, cutoff=0.82)
        found = []
        for alias in close:
            for team_id in sorted(self._alias_index[alias]):
                if self._teams[team_id] not in found:
                    found.append(self._teams[team_id])
        return found[:limit]

    def resolve_one(self, query: str) -> Team | None:
        """Resolve to a single team, or ``None`` when nothing matches."""
        matches = self.resolve(query)
        return matches[0] if matches else None

    def search(self, query: str = "", limit: int | None = 25) -> list[Team]:
        """List teams whose name contains ``query`` (all teams when empty).

        ``limit=None`` returns every match, so callers can report a true total.
        """
        self._ensure_built()
        needle = slugify(query)
        teams = [
            team
            for team in self._teams.values()
            if not needle or any(needle in alias for alias in team.aliases)
        ]
        found = sorted(teams, key=lambda t: t.name)
        return found if limit is None else found[:max(limit, 0)]

    def _rank(self, teams: list[Team], needle: str) -> list[Team]:
        """Prefer exact slug matches, then the most-seen clubs."""
        def key(team: Team) -> tuple:
            exact = 0 if slugify(team.name) == needle else 1
            seen = -sum(
                self._counts[raw]
                for raw, tid in self._raw_to_id.items()
                if tid == team.team_id
            )
            return (exact, seen, team.name)

        return sorted(teams, key=key)


def _starts_word(alias: str, needle: str) -> bool:
    """True when ``needle`` matches the start of ``alias`` on a word boundary."""
    return alias.startswith(needle) and (
        len(alias) == len(needle) or alias[len(needle)] == " "
    )


def _display_from_raw(parsed: ParsedName) -> str:
    """Human-friendly club name from a raw spelling, dropping the state code."""
    text = parsed.raw
    if parsed.state:
        for suffix in (
            f" - {parsed.state}", f"-{parsed.state}", f" {parsed.state}",
            f" ({parsed.state})",
        ):
            if text.endswith(suffix):
                text = text[: -len(suffix)]
                break
    return text.strip(" -") or parsed.raw
