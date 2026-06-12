/**
 * Test data builders. Express seed data in the language of the problem domain
 * so acceptance scenarios read like the questions in the specification.
 */
import type { Match, Player } from '../../src/domain/types.js';

export function match(p: Partial<Match> & {
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
}): Match {
  return {
    competition: p.competition ?? 'Brasileirão',
    season: p.season ?? 2023,
    date: p.date ?? `${p.season ?? 2023}-01-01`,
    round: p.round,
    stadium: p.stadium,
    homeTeam: p.homeTeam,
    awayTeam: p.awayTeam,
    homeGoals: p.homeGoals,
    awayGoals: p.awayGoals,
  };
}

let nextId = 1;
export function player(p: Partial<Player> & { name: string }): Player {
  return {
    id: p.id ?? nextId++,
    name: p.name,
    age: p.age,
    nationality: p.nationality,
    overall: p.overall,
    potential: p.potential,
    club: p.club,
    position: p.position,
    jerseyNumber: p.jerseyNumber,
  };
}
