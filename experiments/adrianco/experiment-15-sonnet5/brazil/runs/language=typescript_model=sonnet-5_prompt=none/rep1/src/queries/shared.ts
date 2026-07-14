import type { Match, TeamKey } from "../types.js";

export const DEFAULT_LIMIT = 25;

/** Matches a competition filter against a match's competition label or
 * dataset source name, case-insensitively and in either substring direction
 * (so "brasileirao" matches "Brasileirao Serie A" and vice versa). */
export function competitionMatches(match: Match, competition: string): boolean {
  const c = competition.trim().toLowerCase();
  if (!c) return true;
  const comp = match.competition.toLowerCase();
  const source = match.source.toLowerCase();
  return comp.includes(c) || c.includes(comp) || source.includes(c) || c.includes(source);
}

export function byDateDesc(a: Match, b: Match): number {
  const at = a.date ? a.date.getTime() : -Infinity;
  const bt = b.date ? b.date.getTime() : -Infinity;
  return bt - at;
}

export function byDateAsc(a: Match, b: Match): number {
  const at = a.date ? a.date.getTime() : Infinity;
  const bt = b.date ? b.date.getTime() : Infinity;
  return at - bt;
}

export interface TableRowBase {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
}

export function makeRowMap(): Map<string, TableRowBase> {
  return new Map<string, TableRowBase>();
}

export function getOrCreateRow(table: Map<string, TableRowBase>, teamKey: TeamKey): TableRowBase {
  let row = table.get(teamKey.key);
  if (!row) {
    row = {
      team: teamKey.display,
      played: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goalsFor: 0,
      goalsAgainst: 0,
    };
    table.set(teamKey.key, row);
  }
  return row;
}
