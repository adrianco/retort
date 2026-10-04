/**
 * DSL: aggregate statistics.
 */
import type { WorldRef } from './soccer-dsl.js';
import type { StatisticsScope, SummaryExpectation } from '../drivers/soccer-system-driver.js';

export class StatisticsDsl {
  constructor(private readonly world: WorldRef) {}

  async confirmSummary({ competition, season, team, ...expected }: StatisticsScope & SummaryExpectation) {
    await (await this.world().system()).confirmSummary({ competition, season, team }, expected);
  }

  async confirmSummaryBetween({ competition, season, team, ...ranges }: StatisticsScope & { [K in keyof SummaryExpectation]?: [number, number] }) {
    await (await this.world().system()).confirmSummaryBetween({ competition, season, team }, ranges as Record<string, [number, number]>);
  }

  async confirmBiggestWins({ limit = 10, expected, ...scope }: StatisticsScope & { limit?: number; expected: string[] }) {
    await (await this.world().system()).confirmBiggestWins(scope, limit, expected);
  }

  async confirmBiggestWinsMarginAtLeast({ limit = 10, margin, ...scope }: StatisticsScope & { limit?: number; margin: number }) {
    await (await this.world().system()).confirmBiggestWinsMarginAtLeast(scope, limit, margin);
  }

  async confirmSeasonComparison({ competition = 'Brasileirão', seasons }: { competition?: string; seasons: Record<number, { matches?: number; averageGoals?: number; champion?: string }> }) {
    await (await this.world().system()).confirmSeasonComparison(competition, seasons);
  }
}
