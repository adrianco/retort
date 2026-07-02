import { stripAccents } from "./normalize.js";
import type { Player } from "./types.js";

function foldCase(value: string): string {
  return stripAccents(value).toLowerCase();
}

function byOverallDesc(a: Player, b: Player): number {
  return (b.overall ?? 0) - (a.overall ?? 0);
}

export function searchPlayersByName(players: Player[], name: string): Player[] {
  const needle = foldCase(name);
  return players
    .filter((p) => foldCase(p.name).includes(needle))
    .sort(byOverallDesc);
}

export function findPlayersByClub(players: Player[], club: string): Player[] {
  const needle = foldCase(club);
  return players
    .filter((p) => foldCase(p.club).includes(needle))
    .sort(byOverallDesc);
}

export function findPlayersByNationality(players: Player[], nationality: string): Player[] {
  const needle = foldCase(nationality);
  return players
    .filter((p) => foldCase(p.nationality) === needle)
    .sort(byOverallDesc);
}

export interface TopRatedOptions {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  limit?: number;
}

export function topRatedPlayers(players: Player[], options: TopRatedOptions = {}): Player[] {
  const filtered = players.filter((p) => {
    if (options.name && !foldCase(p.name).includes(foldCase(options.name))) return false;
    if (options.nationality && foldCase(p.nationality) !== foldCase(options.nationality)) return false;
    if (options.club && !foldCase(p.club).includes(foldCase(options.club))) return false;
    if (options.position && foldCase(p.position ?? "") !== foldCase(options.position)) return false;
    return true;
  });

  const sorted = filtered.sort(byOverallDesc);
  return options.limit !== undefined ? sorted.slice(0, options.limit) : sorted;
}
