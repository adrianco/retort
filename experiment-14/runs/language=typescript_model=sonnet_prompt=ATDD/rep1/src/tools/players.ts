import { loadAllData } from '../data/loader.js';

export interface FindPlayersArgs {
  name?: string;
  nationality?: string;
  club?: string;
  minRating?: number;
  position?: string;
  limit?: number;
}

export function findPlayers(args: FindPlayersArgs): any[] {
  const { name, nationality, club, minRating, position, limit = 20 } = args;
  const data = loadAllData();

  // Merge FIFA data with supplementary Brazilian clubs players data
  // Use a Set to avoid duplicates by ID
  const playerMap = new Map<any, any>();
  for (const p of data.fifa) {
    playerMap.set(p.ID, p);
  }
  for (const p of data.brazilianClubPlayers) {
    if (!playerMap.has(p.ID)) {
      playerMap.set(p.ID, p);
    }
  }
  let players = Array.from(playerMap.values());

  if (name) {
    const lName = name.toLowerCase();
    players = players.filter(p => p.Name?.toLowerCase().includes(lName));
  }

  if (nationality) {
    const lNat = nationality.toLowerCase();
    players = players.filter(p => p.Nationality?.toLowerCase() === lNat);
  }

  if (club) {
    const lClub = club.toLowerCase();
    players = players.filter(p => p.Club?.toLowerCase().includes(lClub));
  }

  if (minRating !== undefined) {
    players = players.filter(p => Number(p.Overall) >= minRating);
  }

  if (position) {
    const lPos = position.toLowerCase();
    players = players.filter(p => p.Position?.toLowerCase() === lPos);
  }

  // Sort by Overall rating descending
  players = players.sort((a, b) => Number(b.Overall) - Number(a.Overall));

  return players.slice(0, limit);
}
