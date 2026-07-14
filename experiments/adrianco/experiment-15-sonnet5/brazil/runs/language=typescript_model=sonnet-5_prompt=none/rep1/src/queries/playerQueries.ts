import { normalizeKey } from "../normalize.js";
import type { Dataset, Player } from "../types.js";

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  limit?: number;
}

export interface PlayerQueryResult {
  total: number;
  players: Player[];
}

/** Matches a club filter against a player's club: prefers an exact
 * (normalized) match when one exists among the candidates, otherwise falls
 * back to substring matching so "Santos" doesn't also drag in "Santos
 * Laguna" while a plain query without an exact hit still resolves. */
function filterByClub(players: Player[], clubQuery: string): Player[] {
  const key = normalizeKey(clubQuery);
  const exact = players.filter((p) => normalizeKey(p.club) === key);
  if (exact.length > 0) return exact;
  return players.filter((p) => normalizeKey(p.club).includes(key));
}

/** Searches the FIFA player dataset by name (substring), nationality, club
 * (exact match preferred, substring fallback) and/or position (exact),
 * sorted by Overall rating descending. */
export function searchPlayers(dataset: Dataset, filter: PlayerFilter = {}): PlayerQueryResult {
  let results = dataset.players;

  if (filter.name) {
    const key = normalizeKey(filter.name);
    results = results.filter((p) => normalizeKey(p.name).includes(key));
  }
  if (filter.nationality) {
    const key = normalizeKey(filter.nationality);
    results = results.filter((p) => normalizeKey(p.nationality) === key);
  }
  if (filter.club) {
    results = filterByClub(results, filter.club);
  }
  if (filter.position) {
    const key = normalizeKey(filter.position);
    results = results.filter((p) => normalizeKey(p.position) === key);
  }

  const sorted = [...results].sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  const limit = filter.limit ?? 25;
  return { total: sorted.length, players: sorted.slice(0, limit) };
}

export interface ClubPlayerSummary {
  club: string;
  playerCount: number;
  averageOverall: number;
  topPlayers: Player[];
}

/** Summary of players at a given club: count, average Overall rating, and
 * top-rated players (used for e.g. "highest-rated players at Flamengo"). */
export function playersByClub(dataset: Dataset, club: string, opts: { limit?: number } = {}): ClubPlayerSummary {
  const players = filterByClub(dataset.players, club);
  const sorted = [...players].sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  const averageOverall =
    players.length > 0 ? players.reduce((sum, p) => sum + (p.overall ?? 0), 0) / players.length : 0;
  const limit = opts.limit ?? 10;
  return { club, playerCount: players.length, averageOverall, topPlayers: sorted.slice(0, limit) };
}

export interface BrazilianClubBreakdownRow {
  club: string;
  playerCount: number;
  averageOverall: number;
}

/** Groups Brazilian (nationality) players by club, for questions like
 * "Brazilian players at Brazilian clubs". Only clubs matching one of the
 * given name fragments are included (case/accent-insensitive substring). */
export function brazilianPlayersByClub(dataset: Dataset, clubNameFragments: string[]): BrazilianClubBreakdownRow[] {
  const fragments = clubNameFragments.map(normalizeKey);
  const brazilians = dataset.players.filter((p) => normalizeKey(p.nationality) === "brazil");

  const byClub = new Map<string, Player[]>();
  for (const p of brazilians) {
    const clubKey = normalizeKey(p.club);
    if (!fragments.some((f) => clubKey.includes(f))) continue;
    const list = byClub.get(p.club) ?? [];
    list.push(p);
    byClub.set(p.club, list);
  }

  return [...byClub.entries()]
    .map(([club, players]) => ({
      club,
      playerCount: players.length,
      averageOverall: players.reduce((sum, p) => sum + (p.overall ?? 0), 0) / players.length,
    }))
    .sort((a, b) => b.playerCount - a.playerCount);
}
