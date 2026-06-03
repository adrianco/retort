import { Match, Competition } from '../types.js';
import { standings, TeamRecord } from './teams.js';

export interface SeasonChampion {
  season: number;
  competition: Competition;
  champion: TeamRecord;
  runnersUp: TeamRecord[];
}

export function seasonChampion(
  matches: Match[],
  competition: Competition,
  season: number,
): SeasonChampion | null {
  const table = standings(matches, { competition, season });
  if (table.length === 0) return null;
  return {
    season,
    competition,
    champion: table[0],
    runnersUp: table.slice(1, 4),
  };
}

/** Knockout-stage matches grouped by stage for Libertadores / Copa do Brasil. */
export function knockoutBracket(
  matches: Match[],
  competition: Competition,
  season: number,
): Record<string, Match[]> {
  const ms = matches.filter(
    (m) => m.competition === competition && m.season === season,
  );
  const groups: Record<string, Match[]> = {};
  for (const m of ms) {
    const stage = m.stage || m.round || 'unspecified';
    (groups[stage] ??= []).push(m);
  }
  for (const k of Object.keys(groups)) {
    groups[k].sort((a, b) => a.date.localeCompare(b.date));
  }
  return groups;
}
