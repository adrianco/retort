/**
 * Context: builds small in-memory datasets for unit tests so query behaviour
 * can be checked against known answers without loading the full CSV set.
 */
import { inferTeamStates } from '../src/loader.js';
import { normalizeTeam, type CompetitionName } from '../src/normalize.js';
import type { Dataset, Match, Player } from '../src/types.js';

let counter = 0;

export function makeMatch(
  date: string,
  home: string,
  away: string,
  homeGoals: number,
  awayGoals: number,
  competition: CompetitionName = 'Brasileirão Série A',
  extra: Partial<Pick<Match, 'round' | 'stage' | 'season'>> = {},
): Match {
  counter++;
  return {
    id: `test:${counter}`,
    source: 'test',
    competition,
    season: extra.season ?? Number(date.slice(0, 4)),
    date,
    round: extra.round,
    stage: extra.stage,
    home: normalizeTeam(home),
    away: normalizeTeam(away),
    homeGoals,
    awayGoals,
  };
}

export function makePlayer(overrides: Partial<Player> & Pick<Player, 'name' | 'club'>): Player {
  return {
    id: ++counter,
    nationality: 'Brazil',
    overall: 70,
    clubKey: normalizeTeam(overrides.club).key,
    attributes: {},
    ...overrides,
  };
}

/** Applies the same team-state inference the real loader uses. */
export function makeDataset(matches: Match[], players: Player[] = []): Dataset {
  return { matches: inferTeamStates(matches), players, sources: [] };
}
