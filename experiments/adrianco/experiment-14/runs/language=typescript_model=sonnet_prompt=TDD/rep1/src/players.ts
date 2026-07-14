import type { DataLoader } from './loader.js';
import type { FifaPlayer } from './types.js';

export interface SearchPlayersParams {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxOverall?: number;
  limit?: number;
}

export function searchPlayers(
  loader: DataLoader,
  params: SearchPlayersParams,
): FifaPlayer[] {
  let players = loader.getPlayers();

  if (params.name) {
    const q = params.name.toLowerCase();
    players = players.filter((p) => p.name.toLowerCase().includes(q));
  }

  if (params.nationality) {
    const q = params.nationality.toLowerCase();
    players = players.filter((p) => p.nationality.toLowerCase() === q);
  }

  if (params.club) {
    const q = params.club.toLowerCase();
    players = players.filter((p) => p.club.toLowerCase().includes(q));
  }

  if (params.position) {
    const q = params.position.toLowerCase();
    players = players.filter((p) => p.position.toLowerCase() === q);
  }

  if (params.minOverall !== undefined) {
    players = players.filter((p) => p.overall >= params.minOverall!);
  }

  if (params.maxOverall !== undefined) {
    players = players.filter((p) => p.overall <= params.maxOverall!);
  }

  players = players.sort((a, b) => b.overall - a.overall);

  if (params.limit) {
    players = players.slice(0, params.limit);
  }

  return players;
}

export interface ClubPlayersResult {
  club: string;
  players: FifaPlayer[];
  avg_overall: number;
}

export function getPlayersByClub(
  loader: DataLoader,
  club: string,
): ClubPlayersResult | null {
  const players = searchPlayers(loader, { club });
  if (players.length === 0) return null;
  const avg = players.reduce((s, p) => s + p.overall, 0) / players.length;
  return {
    club,
    players: players.sort((a, b) => b.overall - a.overall),
    avg_overall: Math.round(avg * 10) / 10,
  };
}
