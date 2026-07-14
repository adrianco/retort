import { DataStore, Player } from '../data/types.js';
import { stripAccents, normalizeTeam } from '../data/normalize.js';

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
  sortBy?: 'overall' | 'potential' | 'age' | 'name';
  sortOrder?: 'asc' | 'desc';
}

function normalizeForSearch(s: string): string {
  return stripAccents(s).toLowerCase();
}

export function findPlayers(store: DataStore, f: PlayerFilter): Player[] {
  let results = store.players;

  if (f.name) {
    const q = normalizeForSearch(f.name);
    results = results.filter((p) => normalizeForSearch(p.name).includes(q));
  }
  if (f.nationality) {
    const q = normalizeForSearch(f.nationality);
    results = results.filter((p) => normalizeForSearch(p.nationality) === q);
  }
  if (f.club) {
    const q = normalizeTeam(f.club);
    results = results.filter((p) => {
      const cn = p.clubNormalized;
      if (!cn || !q) return false;
      return cn === q || cn.includes(q) || q.includes(cn);
    });
  }
  if (f.position) {
    const q = f.position.toUpperCase();
    results = results.filter((p) => p.position.toUpperCase() === q);
  }
  if (f.minOverall !== undefined) {
    results = results.filter((p) => p.overall >= f.minOverall!);
  }
  if (f.maxOverall !== undefined) {
    results = results.filter((p) => p.overall <= f.maxOverall!);
  }
  if (f.minAge !== undefined) results = results.filter((p) => p.age >= f.minAge!);
  if (f.maxAge !== undefined) results = results.filter((p) => p.age <= f.maxAge!);

  const sortBy = f.sortBy ?? 'overall';
  const order = f.sortOrder ?? 'desc';
  const cmp = order === 'asc' ? 1 : -1;
  results = [...results].sort((a, b) => {
    let av: number | string, bv: number | string;
    switch (sortBy) {
      case 'name': av = a.name; bv = b.name; break;
      case 'age': av = a.age; bv = b.age; break;
      case 'potential': av = a.potential; bv = b.potential; break;
      default: av = a.overall; bv = b.overall;
    }
    if (av < bv) return -1 * cmp;
    if (av > bv) return 1 * cmp;
    return 0;
  });

  if (f.limit) results = results.slice(0, f.limit);
  return results;
}

export function formatPlayer(p: Player): string {
  return `${p.name} — Overall: ${p.overall}, Position: ${p.position || 'N/A'}, Club: ${p.club || 'N/A'}, Nat: ${p.nationality}`;
}

export interface ClubPlayerSummary {
  club: string;
  count: number;
  averageOverall: number;
  topPlayers: Player[];
}

export function playersByClub(
  store: DataStore,
  options: { nationality?: string; limitTopPerClub?: number } = {},
): ClubPlayerSummary[] {
  let pool = store.players.filter((p) => !!p.club);
  if (options.nationality) {
    const q = normalizeForSearch(options.nationality);
    pool = pool.filter((p) => normalizeForSearch(p.nationality) === q);
  }
  const byClub = new Map<string, Player[]>();
  for (const p of pool) {
    const list = byClub.get(p.club) ?? [];
    list.push(p);
    byClub.set(p.club, list);
  }
  const top = options.limitTopPerClub ?? 5;
  const out: ClubPlayerSummary[] = [];
  for (const [club, players] of byClub.entries()) {
    const sorted = [...players].sort((a, b) => b.overall - a.overall);
    const sum = sorted.reduce((acc, p) => acc + p.overall, 0);
    out.push({
      club,
      count: sorted.length,
      averageOverall: sorted.length ? sum / sorted.length : 0,
      topPlayers: sorted.slice(0, top),
    });
  }
  return out.sort((a, b) => b.averageOverall - a.averageOverall);
}
