import { Player } from '../types.js';
import { stripAccents, normalizeTeam, keyMatches } from '../normalize.js';

export interface PlayerFilter {
  /** Substring of player name (case/diacritic-insensitive). */
  name?: string;
  /** Nationality, exact (case-insensitive, accent-insensitive). */
  nationality?: string;
  /** Club name; uses team normalization so "Flamengo" matches "CR Flamengo". */
  club?: string;
  /** Position code (e.g. "ST", "LW"). Case-insensitive substring. */
  position?: string;
  /** Minimum FIFA Overall rating. */
  minOverall?: number;
  /** Minimum age (inclusive). */
  minAge?: number;
  /** Maximum age (inclusive). */
  maxAge?: number;
  limit?: number;
}

function cmpInsensitive(a: string, b: string): boolean {
  return stripAccents(a.toLowerCase()) === stripAccents(b.toLowerCase());
}

function containsInsensitive(haystack: string, needle: string): boolean {
  return stripAccents(haystack.toLowerCase()).includes(
    stripAccents(needle.toLowerCase()),
  );
}

export function findPlayers(players: Player[], filter: PlayerFilter): Player[] {
  const clubKey = filter.club ? normalizeTeam(filter.club) : '';
  let out = players.filter((p) => {
    if (filter.name && !containsInsensitive(p.name, filter.name)) return false;
    if (
      filter.nationality &&
      !(p.nationality && cmpInsensitive(p.nationality, filter.nationality))
    )
      return false;
    if (clubKey) {
      if (!p.clubKey) return false;
      if (!keyMatches(p.clubKey, clubKey)) return false;
    }
    if (filter.position) {
      if (!p.position) return false;
      if (!containsInsensitive(p.position, filter.position)) return false;
    }
    if (filter.minOverall != null && (p.overall ?? 0) < filter.minOverall)
      return false;
    if (filter.minAge != null && (p.age ?? 0) < filter.minAge) return false;
    if (filter.maxAge != null && (p.age ?? 999) > filter.maxAge) return false;
    return true;
  });

  // Highest-rated first by default.
  out.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  if (filter.limit != null && filter.limit > 0) out = out.slice(0, filter.limit);
  return out;
}

export interface ClubSummary {
  club: string;
  count: number;
  averageOverall: number;
  topPlayer?: Player;
}

/**
 * Aggregate players by their club. Useful for "Brazilian players at Brazilian
 * clubs" style summaries.
 */
export function playersByClub(players: Player[]): ClubSummary[] {
  const byKey = new Map<string, { club: string; players: Player[] }>();
  for (const p of players) {
    if (!p.clubKey || !p.club) continue;
    const entry = byKey.get(p.clubKey) ?? { club: p.club, players: [] };
    entry.players.push(p);
    byKey.set(p.clubKey, entry);
  }
  const out: ClubSummary[] = [];
  for (const { club, players: ps } of byKey.values()) {
    const overall = ps
      .map((p) => p.overall ?? 0)
      .filter((n) => n > 0);
    const avg = overall.length
      ? overall.reduce((a, b) => a + b, 0) / overall.length
      : 0;
    const top = ps
      .slice()
      .sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0))[0];
    out.push({
      club,
      count: ps.length,
      averageOverall: avg,
      topPlayer: top,
    });
  }
  return out.sort((a, b) => b.averageOverall - a.averageOverall);
}
