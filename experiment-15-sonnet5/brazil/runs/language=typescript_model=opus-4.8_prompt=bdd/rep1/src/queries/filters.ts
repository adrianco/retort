/**
 * Reusable match-filtering primitives shared by the higher-level query modules.
 */
import { teamMatches } from "../normalize.js";
import type { Match } from "../types.js";

export interface MatchFilter {
  /** Match a team on either side (home or away). */
  team?: string;
  /** Require this team to be the home side. */
  homeTeam?: string;
  /** Require this team to be the away side. */
  awayTeam?: string;
  /** Second team, for head-to-head style queries. */
  opponent?: string;
  /** Competition name (accent/case-insensitive substring match). */
  competition?: string;
  /** Season / year. */
  season?: number;
  /** Inclusive lower date bound (YYYY-MM-DD). */
  from?: string;
  /** Inclusive upper date bound (YYYY-MM-DD). */
  to?: string;
  /** Only matches that have a recorded score. */
  playedOnly?: boolean;
}

/** Apply a {@link MatchFilter} to a list of matches. */
export function filterMatches(matches: Match[], filter: MatchFilter): Match[] {
  const from = filter.from ? Date.parse(filter.from) : null;
  const to = filter.to ? Date.parse(filter.to) : null;

  return matches.filter((m) => {
    if (filter.season !== undefined && m.season !== filter.season) return false;

    if (filter.competition && !competitionMatches(m.competition, filter.competition)) {
      return false;
    }

    if (filter.homeTeam && !teamMatches(m.homeTeam, filter.homeTeam)) return false;
    if (filter.awayTeam && !teamMatches(m.awayTeam, filter.awayTeam)) return false;

    if (filter.team) {
      const onHome = teamMatches(m.homeTeam, filter.team);
      const onAway = teamMatches(m.awayTeam, filter.team);
      if (!onHome && !onAway) return false;
    }

    if (filter.opponent) {
      const onHome = teamMatches(m.homeTeam, filter.opponent);
      const onAway = teamMatches(m.awayTeam, filter.opponent);
      if (!onHome && !onAway) return false;
    }

    if (filter.playedOnly && (m.homeGoals === null || m.awayGoals === null)) return false;

    if (from !== null) {
      if (!m.date || m.date.getTime() < from) return false;
    }
    if (to !== null) {
      if (!m.date || m.date.getTime() > to) return false;
    }

    return true;
  });
}

/**
 * Competition matching is intentionally loose so users can type "Brasileirão",
 * "brasileirao", "Serie A", "Libertadores", etc. We compare accent-free,
 * lower-cased substrings in both directions.
 */
export function competitionMatches(actual: string, query: string): boolean {
  const a = normalizeCompetition(actual);
  const b = normalizeCompetition(query);
  if (!b) return true;
  return a.includes(b) || b.includes(a);
}

function normalizeCompetition(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

/** Sort matches chronologically; undated matches sort last. */
export function sortByDate(matches: Match[], direction: "asc" | "desc" = "asc"): Match[] {
  const factor = direction === "asc" ? 1 : -1;
  return [...matches].sort((a, b) => {
    const at = a.date ? a.date.getTime() : Number.POSITIVE_INFINITY;
    const bt = b.date ? b.date.getTime() : Number.POSITIVE_INFINITY;
    if (at === bt) return 0;
    return (at - bt) * factor;
  });
}
