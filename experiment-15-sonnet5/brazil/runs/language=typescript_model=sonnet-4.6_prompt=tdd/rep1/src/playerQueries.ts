import type { AllData, FifaPlayer } from './dataLoader.js';

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
}

export function searchPlayers(data: AllData, filter: PlayerFilter): FifaPlayer[] {
  return data.fifaPlayers.filter(p => {
    if (filter.name && !p.name.toLowerCase().includes(filter.name.toLowerCase())) return false;
    if (filter.nationality && p.nationality.toLowerCase() !== filter.nationality.toLowerCase()) return false;
    if (filter.club && !p.club.toLowerCase().includes(filter.club.toLowerCase())) return false;
    if (filter.position && p.position.toLowerCase() !== filter.position.toLowerCase()) return false;
    if (filter.minOverall !== undefined && p.overall < filter.minOverall) return false;
    return true;
  });
}

export function getTopRatedPlayers(data: AllData, filter: PlayerFilter, limit = 10): FifaPlayer[] {
  return searchPlayers(data, filter)
    .sort((a, b) => b.overall - a.overall)
    .slice(0, limit);
}

export interface ClubEntry {
  count: number;
  avgRating: number;
  players: FifaPlayer[];
}

export function getPlayersByClub(data: AllData, filter: Omit<PlayerFilter, 'club'>): Record<string, ClubEntry> {
  const players = searchPlayers(data, filter);
  const clubs: Record<string, ClubEntry> = {};

  for (const player of players) {
    if (!player.club) continue;
    if (!clubs[player.club]) {
      clubs[player.club] = { count: 0, avgRating: 0, players: [] };
    }
    clubs[player.club].players.push(player);
    clubs[player.club].count++;
  }

  for (const club of Object.values(clubs)) {
    const total = club.players.reduce((sum, p) => sum + p.overall, 0);
    club.avgRating = club.count > 0 ? total / club.count : 0;
  }

  return clubs;
}
