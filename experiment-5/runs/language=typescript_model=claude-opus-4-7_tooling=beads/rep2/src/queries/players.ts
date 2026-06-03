import type { Player } from "../types.js";
import { normalizeTeam, stripDiacritics } from "../normalize.js";

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxOverall?: number;
  minAge?: number;
  maxAge?: number;
  sortBy?: "overall" | "potential" | "age" | "name";
  sortDir?: "asc" | "desc";
  limit?: number;
}

function ci(haystack: string, needle: string): boolean {
  return stripDiacritics(haystack).toLowerCase().includes(stripDiacritics(needle).toLowerCase());
}

export function findPlayers(players: Player[], filter: PlayerFilter): Player[] {
  const clubN = filter.club ? normalizeTeam(filter.club) : undefined;

  let res = players.filter((p) => {
    if (filter.name && !ci(p.name, filter.name)) return false;
    if (filter.nationality && !ci(p.nationality, filter.nationality)) return false;
    if (clubN && p.clubNormalized !== clubN && !ci(p.club, filter.club!)) return false;
    if (filter.position && !ci(p.position ?? "", filter.position)) return false;
    if (filter.minOverall !== undefined && (p.overall ?? 0) < filter.minOverall) return false;
    if (filter.maxOverall !== undefined && (p.overall ?? 0) > filter.maxOverall) return false;
    if (filter.minAge !== undefined && (p.age ?? 0) < filter.minAge) return false;
    if (filter.maxAge !== undefined && (p.age ?? 0) > filter.maxAge) return false;
    return true;
  });

  const sortBy = filter.sortBy ?? "overall";
  const dir = filter.sortDir ?? "desc";
  const factor = dir === "desc" ? -1 : 1;
  res.sort((a, b) => {
    if (sortBy === "name") return factor * a.name.localeCompare(b.name);
    const av = (a[sortBy as "overall" | "potential" | "age"] ?? 0) as number;
    const bv = (b[sortBy as "overall" | "potential" | "age"] ?? 0) as number;
    return factor * (av - bv);
  });

  if (filter.limit && filter.limit > 0) res = res.slice(0, filter.limit);
  return res;
}

export function playersByClub(players: Player[], club: string): Player[] {
  return findPlayers(players, { club, sortBy: "overall", sortDir: "desc" });
}

export function topBrazilianPlayers(players: Player[], limit = 10): Player[] {
  return findPlayers(players, {
    nationality: "Brazil",
    sortBy: "overall",
    sortDir: "desc",
    limit,
  });
}
