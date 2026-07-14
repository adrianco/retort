/**
 * services/matches.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   Match-query service: the foundational filtering layer used directly for
 *   "Match Queries" and re-used by the team, competition and statistics
 *   services. Everything that needs "the set of matches matching some criteria"
 *   goes through `findMatches`.
 *
 *   All team comparisons run through `teamMatches` (data/normalize.ts) so that
 *   naming variants resolve correctly. Competition matching is accent- and
 *   case-insensitive and accepts common aliases ("serie a" -> Brasileirão).
 *
 *   `headToHead` aggregates a directional win/draw tally between two clubs and
 *   is the primitive behind both match-level and team-level rivalry queries.
 * -----------------------------------------------------------------------------
 */

import type { Dataset, Match } from "../types.js";
import { stripAccents, teamMatches } from "../data/normalize.js";

export type Venue = "home" | "away" | "any";

export interface MatchQuery {
  /** Match if this team played (respecting `venue`). */
  team?: string;
  /** Restrict `team` matches to a specific opponent. */
  opponent?: string;
  /** Two-team query (order-independent) — overrides team/opponent. */
  teamA?: string;
  teamB?: string;
  /** Competition label or alias. */
  competition?: string;
  /** Season year. */
  season?: number;
  /** Inclusive ISO date lower bound (YYYY-MM-DD). */
  dateFrom?: string;
  /** Inclusive ISO date upper bound (YYYY-MM-DD). */
  dateTo?: string;
  /** Whether `team` must have played at home, away, or either. */
  venue?: Venue;
  /** Maximum number of results (most recent first). 0/undefined = no limit. */
  limit?: number;
}

/** Normalise a competition label for comparison, resolving common aliases. */
function competitionKey(c: string): string {
  const k = stripAccents(c).toLowerCase().trim();
  // NB: BR-Football labels the top flight "Serie A". We deliberately keep that
  // distinct from the canonical "Brasileirão" sources during de-duplication, so
  // "serie a" is NOT aliased to "brasileirao" here.
  if (k === "brasileirao" || k === "campeonato brasileiro" || k === "brasileiro")
    return "brasileirao";
  if (k === "brazilian cup") return "copa do brasil";
  if (k === "copa libertadores") return "libertadores";
  return k;
}

function competitionMatches(query: string, record: string): boolean {
  const q = competitionKey(query);
  const r = competitionKey(record);
  return r === q || r.includes(q) || q.includes(r);
}

/** Sort key for a match: ISO date string, falling back to empty (sorts last). */
function dateSortKey(m: Match): string {
  return m.date ?? "";
}

/** Find all matches satisfying the query, most-recent first. */
export function findMatches(ds: Dataset, query: MatchQuery): Match[] {
  const venue: Venue = query.venue ?? "any";

  let results = ds.matches.filter((m) => {
    if (query.season !== undefined && m.season !== query.season) return false;
    if (query.competition && !competitionMatches(query.competition, m.competition))
      return false;
    if (query.dateFrom && (m.date === null || m.date < query.dateFrom)) return false;
    if (query.dateTo && (m.date === null || m.date > query.dateTo)) return false;

    // Two-team (order independent) query.
    if (query.teamA && query.teamB) {
      const aHome = teamMatches(query.teamA, m.homeTeam);
      const aAway = teamMatches(query.teamA, m.awayTeam);
      const bHome = teamMatches(query.teamB, m.homeTeam);
      const bAway = teamMatches(query.teamB, m.awayTeam);
      return (aHome && bAway) || (aAway && bHome);
    }

    // Single team query, optionally vs an opponent.
    if (query.team) {
      const playedHome = teamMatches(query.team, m.homeTeam);
      const playedAway = teamMatches(query.team, m.awayTeam);
      let played: boolean;
      if (venue === "home") played = playedHome;
      else if (venue === "away") played = playedAway;
      else played = playedHome || playedAway;
      if (!played) return false;

      if (query.opponent) {
        const oppHome = teamMatches(query.opponent, m.homeTeam);
        const oppAway = teamMatches(query.opponent, m.awayTeam);
        if (!(oppHome || oppAway)) return false;
        // Ensure the two teams are on opposite sides.
        if (playedHome && !oppAway) return false;
        if (playedAway && !oppHome) return false;
      }
      return true;
    }

    return true;
  });

  results = results.sort((a, b) => dateSortKey(b).localeCompare(dateSortKey(a)));

  if (query.limit && query.limit > 0) results = results.slice(0, query.limit);
  return results;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  totalMatches: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
  matches: Match[];
}

/** Compute a directional head-to-head summary between two clubs. */
export function headToHead(
  ds: Dataset,
  teamA: string,
  teamB: string,
  query: Omit<MatchQuery, "teamA" | "teamB" | "team" | "opponent"> = {},
): HeadToHead {
  const matches = findMatches(ds, { ...query, teamA, teamB });
  let teamAWins = 0;
  let teamBWins = 0;
  let draws = 0;
  let teamAGoals = 0;
  let teamBGoals = 0;

  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    const aIsHome = teamMatches(teamA, m.homeTeam);
    const aGoals = aIsHome ? m.homeGoals : m.awayGoals;
    const bGoals = aIsHome ? m.awayGoals : m.homeGoals;
    teamAGoals += aGoals;
    teamBGoals += bGoals;
    if (aGoals > bGoals) teamAWins++;
    else if (aGoals < bGoals) teamBWins++;
    else draws++;
  }

  return {
    teamA,
    teamB,
    totalMatches: matches.length,
    teamAWins,
    teamBWins,
    draws,
    teamAGoals,
    teamBGoals,
    matches,
  };
}
