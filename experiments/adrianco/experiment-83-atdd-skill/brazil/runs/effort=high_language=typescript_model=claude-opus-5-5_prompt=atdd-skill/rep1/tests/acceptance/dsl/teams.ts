/**
 * DSL: team records, head-to-heads, competitions entered and team rankings.
 */
import type { RankingCriteria, RecordCriteria, SoccerDriver } from '../drivers/soccer-driver.js';

type RecordFigures = Partial<Record<'played' | 'won' | 'drawn' | 'lost' | 'goalsFor' | 'goalsAgainst', number>>;

const RANKINGS: Record<string, Pick<RankingCriteria, 'metric' | 'venue'>> = {
  'goals scored': { metric: 'goals_for' },
  'home record': { metric: 'win_rate', venue: 'home' },
  'away record': { metric: 'win_rate', venue: 'away' },
  'record': { metric: 'win_rate' },
};

export function rankingFor(by: string): Pick<RankingCriteria, 'metric' | 'venue'> {
  const ranking = RANKINGS[by];
  if (!ranking) throw new Error(`Unknown ranking "${by}" — use one of: ${Object.keys(RANKINGS).join(', ')}`);
  return ranking;
}

export class TeamsDsl {
  constructor(private readonly driver: SoccerDriver) {}

  async requestRecord(criteria: RecordCriteria): Promise<void> {
    await this.driver.requestRecord(criteria);
  }

  confirmRecord(expected: RecordFigures & { winRate?: string }): void {
    this.driver.confirmRecord(expected);
  }

  async compareHeadToHead({ team, opponent }: { team: string; opponent: string }): Promise<void> {
    await this.driver.compareHeadToHead(team, opponent);
  }

  confirmHeadToHead(expected: Partial<Record<'played' | 'teamWins' | 'opponentWins' | 'draws' | 'teamGoals' | 'opponentGoals', number>>): void {
    this.driver.confirmHeadToHead(expected);
  }

  async requestCompetitions({ team }: { team: string }): Promise<void> {
    await this.driver.requestCompetitions(team);
  }

  /** Exactly these competitions, in any order. */
  confirmCompetitions(competitions: string[]): void {
    this.driver.confirmCompetitions(competitions);
  }

  confirmCompetitionRecord(expected: { competition: string } & RecordFigures): void {
    this.driver.confirmCompetitionRecord(expected);
  }

  async rank({ by, season, competition }: { by: string; season?: number; competition?: string }): Promise<void> {
    await this.driver.rankTeams({ ...rankingFor(by), season, competition });
  }

  confirmLeader(expected: { team: string; goalsFor?: number; winRate?: string }): void {
    this.driver.confirmLeader(expected);
  }
}
