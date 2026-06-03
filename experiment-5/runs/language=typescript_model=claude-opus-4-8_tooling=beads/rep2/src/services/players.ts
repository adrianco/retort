/**
 * services/players.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   Player-query service over the FIFA dataset (18,207 players). Supports the
 *   spec's "Player Queries": by name, nationality (esp. Brazilian), club (esp.
 *   Brazilian clubs), position, and minimum rating, with configurable sorting.
 *
 *   Name / nationality / club / position matching is accent- and case-
 *   insensitive substring matching so "sao paulo" finds "São Paulo" and "neymar"
 *   finds "Neymar Jr". Club matching additionally reuses `teamMatches` so a club
 *   query can be cross-referenced with match-data team names (player + match
 *   cross-file queries).
 *
 *   `clubBreakdown` powers the "Brazilian players at Brazilian clubs" summary:
 *   it groups players by club and reports count + average rating.
 * -----------------------------------------------------------------------------
 */

import type { Dataset, Player } from "../types.js";
import { stripAccents, teamMatches } from "../data/normalize.js";

function norm(s: string): string {
  return stripAccents(s).toLowerCase().trim();
}

export type PlayerSort = "overall" | "potential" | "age" | "name";

export interface PlayerQuery {
  name?: string;
  nationality?: string;
  /** Club substring or team-name match. */
  club?: string;
  position?: string;
  minOverall?: number;
  maxAge?: number;
  sortBy?: PlayerSort;
  /** Default descending for ratings, ascending for name/age. */
  ascending?: boolean;
  limit?: number;
}

function compare(a: Player, b: Player, sortBy: PlayerSort): number {
  switch (sortBy) {
    case "name":
      return a.name.localeCompare(b.name);
    case "age":
      return (a.age ?? Infinity) - (b.age ?? Infinity);
    case "potential":
      return (a.potential ?? -1) - (b.potential ?? -1);
    case "overall":
    default:
      return (a.overall ?? -1) - (b.overall ?? -1);
  }
}

/** Find players matching the query, sorted as requested. */
export function findPlayers(ds: Dataset, query: PlayerQuery): Player[] {
  const name = query.name ? norm(query.name) : null;
  const nationality = query.nationality ? norm(query.nationality) : null;
  const club = query.club ? norm(query.club) : null;
  const position = query.position ? norm(query.position) : null;

  let results = ds.players.filter((p) => {
    if (name && !norm(p.name).includes(name)) return false;
    if (nationality && !norm(p.nationality).includes(nationality)) return false;
    if (position && norm(p.position) !== position && !norm(p.position).includes(position))
      return false;
    if (query.minOverall !== undefined && (p.overall ?? 0) < query.minOverall)
      return false;
    if (query.maxAge !== undefined && (p.age ?? Infinity) > query.maxAge)
      return false;
    if (club) {
      const direct = norm(p.club).includes(club);
      const fuzzy = p.club !== "" && teamMatches(query.club!, p.club);
      if (!direct && !fuzzy) return false;
    }
    return true;
  });

  const sortBy = query.sortBy ?? "overall";
  const ascending =
    query.ascending ?? (sortBy === "name" || sortBy === "age");
  results = results.sort((a, b) => {
    const c = compare(a, b, sortBy);
    return ascending ? c : -c;
  });

  if (query.limit && query.limit > 0) results = results.slice(0, query.limit);
  return results;
}

export interface ClubBreakdownRow {
  club: string;
  count: number;
  averageOverall: number;
  topPlayer: string;
}

/** Group matching players by club with count + average rating. */
export function clubBreakdown(
  ds: Dataset,
  query: PlayerQuery,
  topN = 0,
): ClubBreakdownRow[] {
  const players = findPlayers(ds, { ...query, limit: 0 });
  const groups = new Map<string, Player[]>();
  for (const p of players) {
    if (!p.club) continue;
    const arr = groups.get(p.club) ?? [];
    arr.push(p);
    groups.set(p.club, arr);
  }

  const rows: ClubBreakdownRow[] = [];
  for (const [club, members] of groups) {
    const rated = members.filter((m) => m.overall !== null);
    const avg =
      rated.length > 0
        ? rated.reduce((s, m) => s + (m.overall ?? 0), 0) / rated.length
        : 0;
    const top = [...members].sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0))[0];
    rows.push({
      club,
      count: members.length,
      averageOverall: Math.round(avg * 10) / 10,
      topPlayer: top?.name ?? "",
    });
  }

  rows.sort((a, b) => b.count - a.count || b.averageOverall - a.averageOverall);
  return topN > 0 ? rows.slice(0, topN) : rows;
}
