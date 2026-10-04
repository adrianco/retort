/**
 * DSL: team records, comparisons and rankings.
 */
import type { WorldRef } from './soccer-dsl.js';
import type { RankingMeasure, RecordCriteria, TeamRecordExpectation } from '../drivers/soccer-system-driver.js';

const MEASURES: Record<string, RankingMeasure> = {
  'goals scored': 'goals_scored',
  'goals conceded': 'goals_conceded',
  points: 'points',
  wins: 'wins',
  'win rate': 'win_rate',
  'home win rate': 'home_win_rate',
  'away win rate': 'away_win_rate',
};

function measure(name: string): RankingMeasure {
  const m = MEASURES[name];
  if (!m) throw new Error(`Unknown ranking measure "${name}"; try one of: ${Object.keys(MEASURES).join(', ')}`);
  return m;
}

export class TeamsDsl {
  constructor(private readonly world: WorldRef) {}

  async confirmRecord({ team, season, competition, venue, from, to, ...expected }: RecordCriteria & TeamRecordExpectation) {
    await (await this.world().system()).confirmTeamRecord({ team, season, competition, venue, from, to }, expected);
  }

  async confirmHeadToHead({ team, opponent, ...expected }: { team: string; opponent: string } & TeamRecordExpectation) {
    await (await this.world().system()).confirmHeadToHead(team, opponent, expected);
  }

  async confirmHeadToHeadPlayedAtLeast({ team, opponent, matches }: { team: string; opponent: string; matches: number }) {
    await (await this.world().system()).confirmHeadToHeadPlayedAtLeast(team, opponent, matches);
  }

  async confirmCompetitions({ team, competitions }: { team: string; competitions: string[] }) {
    await (await this.world().system()).confirmCompetitions(team, competitions);
  }

  async confirmTopRanked({ measure: name, season, competition, team, value }: { measure: string; season?: number; competition?: string; team: string; value?: number }) {
    await (await this.world().system()).confirmTopRanked(measure(name), { season, competition }, team, value);
  }

  async confirmRankingAvailable({ measure: name, season, competition }: { measure: string; season?: number; competition?: string }) {
    await (await this.world().system()).confirmRankingAvailable(measure(name), { season, competition });
  }

  async confirmProfile({ team, ...expected }: { team: string; squadSize?: number; bestPlayer?: string; played?: number; wins?: number }) {
    await (await this.world().system()).confirmTeamProfile(team, expected);
  }

  async confirmProfileHasSquadAndMatches({ team }: { team: string }) {
    await (await this.world().system()).confirmTeamProfile(team, { hasSquad: true, hasMatches: true });
  }
}
