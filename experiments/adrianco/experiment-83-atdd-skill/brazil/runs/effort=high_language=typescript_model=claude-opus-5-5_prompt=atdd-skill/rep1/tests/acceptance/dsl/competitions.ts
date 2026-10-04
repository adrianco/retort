/**
 * DSL: league standings, champions, relegation and knockout brackets.
 */
import type { SoccerDriver } from '../drivers/soccer-driver.js';
import { parseStandingsRow, parseTie } from './notation.js';

export class CompetitionsDsl {
  constructor(private readonly driver: SoccerDriver) {}

  async requestStandings({ competition = 'Brasileirão', season }: { competition?: string; season: number }): Promise<void> {
    await this.driver.requestStandings(competition, season);
  }

  /** The whole table, exactly. */
  confirmStandings(rows: string[]): void {
    this.driver.confirmStandings(rows.map(parseStandingsRow), true);
  }

  /** The top of the table. */
  confirmStandingsStartWith(rows: string[]): void {
    this.driver.confirmStandings(rows.map(parseStandingsRow), false);
  }

  confirmChampion(team: string): void {
    this.driver.confirmChampion(team);
  }

  /** Exactly these teams, in this order. */
  confirmTeamsInTable(teams: string[]): void {
    this.driver.confirmTeamsInTable(teams);
  }

  confirmIncomplete({ matchesMissing }: { matchesMissing: number }): void {
    this.driver.confirmSeasonIncomplete(matchesMissing);
  }

  confirmRelegated(teams: string[]): void {
    this.driver.confirmRelegated(teams);
  }

  async requestBracket({ competition = 'Libertadores', season }: { competition?: string; season: number }): Promise<void> {
    await this.driver.requestBracket(competition, season);
  }

  confirmTie({ stage, result }: { stage: string; result: string }): void {
    this.driver.confirmTie(stage, parseTie(result));
  }
}
