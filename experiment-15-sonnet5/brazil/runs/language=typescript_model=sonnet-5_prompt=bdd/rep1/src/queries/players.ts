import type { SoccerDataStore } from "../data/store.js";
import { normalizeTeamName } from "../data/normalize.js";
import type { Player } from "../types.js";

export interface PlayerSearchOptions {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  sortBy?: "overall" | "potential" | "age" | "name";
  limit?: number;
}

/** Searches FIFA player data by name/nationality/club/position (Player Queries §3). */
export function searchPlayers(store: SoccerDataStore, options: PlayerSearchOptions = {}): Player[] {
  let results = store.players;

  if (options.name) {
    const needle = options.name.toLowerCase();
    results = results.filter((p) => p.name.toLowerCase().includes(needle));
  }
  if (options.nationality) {
    const needle = options.nationality.toLowerCase();
    results = results.filter((p) => p.nationality.toLowerCase() === needle);
  }
  if (options.club) {
    const clubKey = normalizeTeamName(options.club).teamKey;
    results = results.filter((p) => p.clubKey === clubKey);
  }
  if (options.position) {
    const needle = options.position.toLowerCase();
    results = results.filter((p) => (p.position ?? "").toLowerCase() === needle);
  }
  if (options.minOverall !== undefined) {
    const min = options.minOverall;
    results = results.filter((p) => p.overall !== null && p.overall >= min);
  }

  const sortBy = options.sortBy ?? "overall";
  const sorted = [...results].sort((a, b) => {
    if (sortBy === "name") return a.name.localeCompare(b.name);
    if (sortBy === "age") return (a.age ?? 0) - (b.age ?? 0);
    if (sortBy === "potential") return (b.potential ?? 0) - (a.potential ?? 0);
    return (b.overall ?? 0) - (a.overall ?? 0);
  });

  return options.limit ? sorted.slice(0, options.limit) : sorted;
}

export interface ClubPlayerSummary {
  club: string;
  playerCount: number;
  averageOverall: number;
}

/**
 * Groups Brazilian players by the Brazilian clubs they play for, matching
 * the "Brazilian players at Brazilian clubs" example in the spec.
 * "Brazilian club" is derived from every team key that appears in the
 * Brasileirão match data, rather than a hardcoded list.
 */
export function brazilianPlayersAtBrazilianClubs(store: SoccerDataStore): ClubPlayerSummary[] {
  const brazilianClubKeys = new Set<string>();
  for (const match of store.matches) {
    if (match.competition === "Brasileirao") {
      brazilianClubKeys.add(match.homeTeamKey);
      brazilianClubKeys.add(match.awayTeamKey);
    }
  }

  const grouped = new Map<string, Player[]>();
  for (const player of store.players) {
    if (player.nationality.toLowerCase() !== "brazil") continue;
    if (!brazilianClubKeys.has(player.clubKey)) continue;
    const list = grouped.get(player.clubKey);
    if (list) list.push(player);
    else grouped.set(player.clubKey, [player]);
  }

  const summaries: ClubPlayerSummary[] = [];
  for (const [clubKey, players] of grouped) {
    const totalOverall = players.reduce((sum, p) => sum + (p.overall ?? 0), 0);
    summaries.push({
      club: store.displayNameFor(clubKey),
      playerCount: players.length,
      averageOverall: Math.round((totalOverall / players.length) * 10) / 10,
    });
  }
  summaries.sort((a, b) => b.playerCount - a.playerCount);
  return summaries;
}

/** Finds Brazilian players in the dataset, ranked by FIFA overall rating. */
export function topBrazilianPlayers(store: SoccerDataStore, limit = 10): Player[] {
  return searchPlayers(store, { nationality: "Brazil", sortBy: "overall", limit });
}
