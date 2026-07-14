/**
 * Player-centric queries over the FIFA dataset: search by name, filter by
 * nationality / club / position, and rank by rating.
 */
import { stripAccents } from "../normalize.js";
import type { Player } from "../types.js";

export interface PlayerFilter {
  /** Substring match on player name (accent/case-insensitive). */
  name?: string;
  /** Nationality (accent/case-insensitive, exact-ish). */
  nationality?: string;
  /** Club substring (accent/case-insensitive). */
  club?: string;
  /** Position code, e.g. "ST", "GK", or a group like "forward". */
  position?: string;
  /** Minimum overall rating. */
  minOverall?: number;
}

function norm(value: string): string {
  return stripAccents(value).toLowerCase().trim();
}

/** Position codes grouped by common role words users may type. */
const POSITION_GROUPS: Record<string, string[]> = {
  forward: ["ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"],
  striker: ["ST", "CF", "LS", "RS"],
  winger: ["LW", "RW", "LM", "RM"],
  midfielder: ["CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"],
  defender: ["CB", "LB", "RB", "LWB", "RWB", "LCB", "RCB"],
  goalkeeper: ["GK"],
};

function positionMatches(playerPosition: string, query: string): boolean {
  const p = norm(playerPosition);
  const q = norm(query);
  if (!q) return true;
  if (p === q) return true;
  const group = POSITION_GROUPS[q];
  if (group) return group.some((code) => norm(code) === p);
  return p.includes(q);
}

/** Filter players by the given criteria (all provided fields must match). */
export function filterPlayers(players: Player[], filter: PlayerFilter): Player[] {
  const name = filter.name ? norm(filter.name) : null;
  const nationality = filter.nationality ? norm(filter.nationality) : null;
  const club = filter.club ? norm(filter.club) : null;

  return players.filter((p) => {
    if (name && !norm(p.name).includes(name)) return false;
    if (nationality && norm(p.nationality) !== nationality && !norm(p.nationality).includes(nationality)) {
      return false;
    }
    if (club && !norm(p.club).includes(club)) return false;
    if (filter.position && !positionMatches(p.position, filter.position)) return false;
    if (filter.minOverall !== undefined && (p.overall ?? 0) < filter.minOverall) return false;
    return true;
  });
}

/** Rank players by overall rating (desc), then potential, then name. */
export function rankByOverall(players: Player[], limit?: number): Player[] {
  const sorted = [...players].sort((a, b) => {
    const ao = a.overall ?? 0;
    const bo = b.overall ?? 0;
    if (bo !== ao) return bo - ao;
    const ap = a.potential ?? 0;
    const bp = b.potential ?? 0;
    if (bp !== ap) return bp - ap;
    return a.name.localeCompare(b.name);
  });
  return limit ? sorted.slice(0, limit) : sorted;
}

/** Convenience: search players by name substring, ranked by rating. */
export function searchPlayersByName(players: Player[], name: string, limit?: number): Player[] {
  return rankByOverall(filterPlayers(players, { name }), limit);
}

export interface ClubSummary {
  club: string;
  playerCount: number;
  averageOverall: number;
  topPlayer: string;
}

/**
 * Group players (e.g. filtered to one nationality) by club, returning per-club
 * counts and average rating. Useful for "Brazilian players at Brazilian clubs".
 */
export function summarizeByClub(players: Player[], limit?: number): ClubSummary[] {
  const groups = new Map<string, Player[]>();
  for (const p of players) {
    if (!p.club) continue;
    const list = groups.get(p.club) ?? [];
    list.push(p);
    groups.set(p.club, list);
  }
  const summaries: ClubSummary[] = [...groups.entries()].map(([club, list]) => {
    const rated = list.filter((p) => p.overall !== null);
    const avg =
      rated.length > 0 ? rated.reduce((sum, p) => sum + (p.overall as number), 0) / rated.length : 0;
    const top = rankByOverall(list, 1)[0];
    return {
      club,
      playerCount: list.length,
      averageOverall: Math.round(avg * 10) / 10,
      topPlayer: top ? top.name : "",
    };
  });
  summaries.sort((a, b) => b.playerCount - a.playerCount || b.averageOverall - a.averageOverall);
  return limit ? summaries.slice(0, limit) : summaries;
}
