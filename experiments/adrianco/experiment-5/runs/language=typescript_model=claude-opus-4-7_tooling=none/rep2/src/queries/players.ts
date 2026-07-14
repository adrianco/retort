import { stripAccents } from "../normalize.js";
import type { Dataset, Player } from "../types.js";

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxOverall?: number;
  minAge?: number;
  maxAge?: number;
  limit?: number;
  sortBy?: "overall" | "potential" | "age" | "name";
  sortDir?: "asc" | "desc";
}

function ciIncludes(haystack: string, needle: string): boolean {
  return stripAccents(haystack.toLowerCase()).includes(stripAccents(needle.toLowerCase()));
}

export function findPlayers(dataset: Dataset, filter: PlayerFilter): Player[] {
  let result = dataset.players.filter((p) => {
    if (filter.name && !ciIncludes(p.name, filter.name)) return false;
    if (filter.nationality && !ciIncludes(p.nationality, filter.nationality)) return false;
    if (filter.club && !ciIncludes(p.club, filter.club)) return false;
    if (filter.position && p.position.toUpperCase() !== filter.position.toUpperCase()) return false;
    if (filter.minOverall !== undefined && (p.overall ?? -1) < filter.minOverall) return false;
    if (filter.maxOverall !== undefined && (p.overall ?? Infinity) > filter.maxOverall) return false;
    if (filter.minAge !== undefined && (p.age ?? -1) < filter.minAge) return false;
    if (filter.maxAge !== undefined && (p.age ?? Infinity) > filter.maxAge) return false;
    return true;
  });

  const sortBy = filter.sortBy ?? "overall";
  const dir = filter.sortDir ?? "desc";
  const cmp = (a: Player, b: Player) => {
    let av: number | string;
    let bv: number | string;
    switch (sortBy) {
      case "name":
        av = a.name;
        bv = b.name;
        break;
      case "age":
        av = a.age ?? Infinity;
        bv = b.age ?? Infinity;
        break;
      case "potential":
        av = a.potential ?? -Infinity;
        bv = b.potential ?? -Infinity;
        break;
      case "overall":
      default:
        av = a.overall ?? -Infinity;
        bv = b.overall ?? -Infinity;
    }
    const ord = typeof av === "string" && typeof bv === "string" ? av.localeCompare(bv) : av < bv ? -1 : av > bv ? 1 : 0;
    return dir === "asc" ? ord : -ord;
  };
  result = result.sort(cmp);

  if (filter.limit && filter.limit > 0) result = result.slice(0, filter.limit);
  return result;
}

export interface PlayerSummary {
  id: number;
  name: string;
  age: number | null;
  nationality: string;
  club: string;
  position: string;
  overall: number | null;
  potential: number | null;
}

export function summarizePlayer(p: Player): PlayerSummary {
  return {
    id: p.id,
    name: p.name,
    age: p.age,
    nationality: p.nationality,
    club: p.club,
    position: p.position,
    overall: p.overall,
    potential: p.potential,
  };
}

export interface ClubBreakdown {
  club: string;
  players: number;
  averageOverall: number;
  topPlayer: PlayerSummary | null;
}

export function brazilianPlayersByClub(dataset: Dataset): ClubBreakdown[] {
  const brazilians = findPlayers(dataset, { nationality: "Brazil", limit: 0 });
  const groups = new Map<string, Player[]>();
  for (const p of brazilians) {
    if (!p.club) continue;
    if (!groups.has(p.club)) groups.set(p.club, []);
    groups.get(p.club)!.push(p);
  }
  const rows: ClubBreakdown[] = [];
  for (const [club, ps] of groups) {
    const ratings = ps.map((p) => p.overall ?? 0).filter((n) => n > 0);
    const avg = ratings.length > 0 ? ratings.reduce((a, b) => a + b, 0) / ratings.length : 0;
    const top = [...ps].sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0))[0] ?? null;
    rows.push({
      club,
      players: ps.length,
      averageOverall: avg,
      topPlayer: top ? summarizePlayer(top) : null,
    });
  }
  rows.sort((a, b) => b.players - a.players);
  return rows;
}
