/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  src/queries/players.ts
 * Purpose: Player-centric queries over the FIFA dataset: search by name,
 *          filter by nationality / club / position, sort by rating, and
 *          summarize Brazilian players grouped by club.
 * Inputs:  A loaded `Dataset` and filter criteria.
 * Outputs: Filtered/sorted `Player[]` and club summaries.
 * Notes:   Club matching uses the same team-name normalization as matches so a
 *          query for "Flamengo" finds "Flamengo" / "CR Flamengo" club strings.
 * ============================================================================
 */

import type { Dataset } from "../data/loader.js";
import type { Player } from "../data/types.js";
import { normalizeTeam, stripAccents, teamsMatch } from "../data/normalize.js";

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  sortBy?: "overall" | "potential" | "age" | "name";
  limit?: number;
}

function ci(s: string): string {
  return stripAccents(s).toLowerCase().trim();
}

/** Search/filter players. Defaults to sorting by overall rating descending. */
export function findPlayers(ds: Dataset, filter: PlayerFilter): Player[] {
  const nameQ = filter.name ? ci(filter.name) : null;
  const natQ = filter.nationality ? ci(filter.nationality) : null;
  const clubKey = filter.club ? normalizeTeam(filter.club) : null;
  const posQ = filter.position ? ci(filter.position) : null;

  let result = ds.players.filter((p) => {
    if (nameQ && !ci(p.name).includes(nameQ)) return false;
    if (natQ && ci(p.nationality) !== natQ && !ci(p.nationality).includes(natQ))
      return false;
    if (clubKey && !teamsMatch(p.clubKey, clubKey)) return false;
    if (posQ && ci(p.position) !== posQ) return false;
    if (filter.minOverall != null && (p.overall ?? 0) < filter.minOverall)
      return false;
    return true;
  });

  const sortBy = filter.sortBy ?? "overall";
  result.sort((a, b) => {
    switch (sortBy) {
      case "name":
        return a.name.localeCompare(b.name);
      case "age":
        return (a.age ?? 999) - (b.age ?? 999);
      case "potential":
        return (b.potential ?? 0) - (a.potential ?? 0);
      case "overall":
      default:
        return (b.overall ?? 0) - (a.overall ?? 0);
    }
  });

  if (filter.limit != null && filter.limit > 0) {
    result = result.slice(0, filter.limit);
  }
  return result;
}

export interface ClubSummary {
  club: string;
  count: number;
  avgOverall: number;
}

/**
 * Summarize players (optionally filtered by nationality) grouped by club,
 * sorted by squad size then average rating. Useful for "Brazilian players at
 * Brazilian clubs" style answers.
 */
export function playersByClub(
  ds: Dataset,
  opts: { nationality?: string; limit?: number } = {},
): ClubSummary[] {
  const natQ = opts.nationality ? ci(opts.nationality) : null;
  const groups = new Map<string, { club: string; sum: number; n: number }>();

  for (const p of ds.players) {
    if (!p.club) continue;
    if (natQ && ci(p.nationality) !== natQ) continue;
    const g = groups.get(p.clubKey) ?? { club: p.club, sum: 0, n: 0 };
    g.sum += p.overall ?? 0;
    g.n += 1;
    groups.set(p.clubKey, g);
  }

  let summaries = [...groups.values()].map((g) => ({
    club: g.club,
    count: g.n,
    avgOverall: g.n === 0 ? 0 : Math.round(g.sum / g.n),
  }));
  summaries.sort((a, b) => b.count - a.count || b.avgOverall - a.avgOverall);
  if (opts.limit != null && opts.limit > 0)
    summaries = summaries.slice(0, opts.limit);
  return summaries;
}
