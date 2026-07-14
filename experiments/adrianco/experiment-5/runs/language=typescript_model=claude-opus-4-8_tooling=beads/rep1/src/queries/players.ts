/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  src/queries/players.ts
 * Purpose: Player-centric queries over the FIFA dataset — search by name,
 *          filter by nationality / club / position, and rank by overall rating.
 *
 * Backs the MCP tools `search_players` and `club_squad`. Name search is
 * accent-insensitive and substring-based; club matching reuses the same
 * normalized-key logic as the match data so "Flamengo" finds the right squad.
 * ============================================================================
 */

import type { Dataset, Player } from "../data/types.js";
import { stripAccents, teamMatches } from "../data/normalize.js";

export interface PlayerFilter {
  /** Substring match against player name (accent-insensitive). */
  name?: string;
  /** Nationality, e.g. "Brazil" (accent-insensitive, exact-ish). */
  nationality?: string;
  /** Club name (normalized-key matching). */
  club?: string;
  /** Position code, e.g. "ST", "GK", "LW" (case-insensitive). */
  position?: string;
  /** Minimum overall rating. */
  minOverall?: number;
}

export interface PlayerSearchResult {
  count: number;
  players: Player[];
  text: string;
}

function ciIncludes(haystack: string, needle: string): boolean {
  return stripAccents(haystack).toLowerCase().includes(
    stripAccents(needle).toLowerCase()
  );
}

/** Filter and rank players, highest overall first. */
export function searchPlayers(
  ds: Dataset,
  filter: PlayerFilter,
  limit = 25
): PlayerSearchResult {
  let players = ds.players;

  if (filter.name) players = players.filter((p) => ciIncludes(p.name, filter.name!));
  if (filter.nationality)
    players = players.filter((p) => ciIncludes(p.nationality, filter.nationality!));
  if (filter.club) players = players.filter((p) => p.clubKey && teamMatches(filter.club!, p.clubKey));
  if (filter.position)
    players = players.filter(
      (p) => p.position.toUpperCase() === filter.position!.toUpperCase()
    );
  if (filter.minOverall != null)
    players = players.filter((p) => (p.overall ?? 0) >= filter.minOverall!);

  const ranked = [...players].sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  const shown = ranked.slice(0, limit);

  const header = describe(filter, ranked.length);
  const lines = shown.map(
    (p, i) =>
      `${i + 1}. ${p.name} — Overall ${p.overall ?? "?"}, ${p.position || "?"}, ` +
      `${p.club || "Free agent"} (${p.nationality})`
  );
  let text = `${header}\n${lines.join("\n")}`;
  if (ranked.length > shown.length)
    text += `\n... (${ranked.length - shown.length} more not shown)`;
  if (ranked.length === 0) text = `${header}\n(no players found)`;

  return { count: ranked.length, players: shown, text };
}

function describe(f: PlayerFilter, total: number): string {
  const parts: string[] = [];
  if (f.name) parts.push(`name~"${f.name}"`);
  if (f.nationality) parts.push(`nationality "${f.nationality}"`);
  if (f.club) parts.push(`club "${f.club}"`);
  if (f.position) parts.push(`position ${f.position}`);
  if (f.minOverall != null) parts.push(`overall ≥ ${f.minOverall}`);
  const scope = parts.length ? parts.join(", ") : "all players";
  return `Found ${total} player(s) for ${scope}:`;
}

export interface ClubSquad {
  club: string;
  count: number;
  avgOverall: number;
  players: Player[];
  text: string;
}

/** Return the squad (players) for a given club, ranked by overall. */
export function clubSquad(ds: Dataset, club: string, limit = 30): ClubSquad {
  const squad = ds.players
    .filter((p) => p.clubKey && teamMatches(club, p.clubKey))
    .sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));

  const rated = squad.filter((p) => p.overall != null);
  const avg =
    rated.length > 0
      ? rated.reduce((s, p) => s + (p.overall ?? 0), 0) / rated.length
      : 0;

  const clubName = squad[0]?.club ?? club;
  const shown = squad.slice(0, limit);
  const lines = shown.map(
    (p, i) => `${i + 1}. ${p.name} — ${p.overall ?? "?"} (${p.position || "?"})`
  );
  const text =
    `${clubName}: ${squad.length} players, avg overall ${avg.toFixed(1)}\n` +
    (lines.length ? lines.join("\n") : "(no players found for this club)");

  return {
    club: clubName,
    count: squad.length,
    avgOverall: avg,
    players: shown,
    text,
  };
}
