/**
 * DSL: aggregate statistics — averages, rankings, biggest wins, season
 * comparisons and team profiles.
 */
import type { SoccerDriver } from '../drivers/soccer-driver.js';
import { parseMatch } from './notation.js';
import { rankingFor } from './teams.js';

export class StatisticsDsl {
  constructor(private readonly driver: SoccerDriver) {}

  async summariseCompetition({ competition, season }: { competition?: string; season?: number } = {}): Promise<void> {
    await this.driver.summariseCompetition(competition, season);
  }

  confirmSummary(expected: { matches?: number; averageGoals?: number; homeWinRate?: string; drawRate?: string; awayWinRate?: string }): void {
    this.driver.confirmSummary(expected);
  }

  async rankTeams({ by, season, competition }: { by: string; season?: number; competition?: string }): Promise<void> {
    await this.driver.rankTeams({ ...rankingFor(by), season, competition });
  }

  confirmBest(expected: { team: string; winRate?: string; goalsFor?: number }): void {
    this.driver.confirmLeader(expected);
  }

  async findBiggestWins({ limit = 10, competition }: { limit?: number; competition?: string }): Promise<void> {
    await this.driver.findBiggestWins(limit, competition);
  }

  /** Exactly these wins, in this order. */
  confirmBiggestWins(matches: string[]): void {
    this.driver.confirmBiggestWins(matches.map(parseMatch));
  }

  async compareSeasons({ seasons, competition = 'Brasileirão' }: { seasons: number[]; competition?: string }): Promise<void> {
    await this.driver.compareSeasons(seasons, competition);
  }

  confirmSeason(expected: { season: number; matches?: number; averageGoals?: number; champion?: string }): void {
    this.driver.confirmSeason(expected);
  }

  async profileTeam({ team }: { team: string }): Promise<void> {
    await this.driver.profileTeam(team);
  }

  confirmProfile(expected: { team?: string; played?: number; won?: number; squadSize?: number; bestPlayer?: string }): void {
    this.driver.confirmProfile(expected);
  }
}
