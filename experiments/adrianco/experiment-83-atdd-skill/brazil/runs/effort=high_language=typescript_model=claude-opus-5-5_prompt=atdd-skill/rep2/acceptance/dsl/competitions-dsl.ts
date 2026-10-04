/**
 * DSL: league tables and knockout brackets. The competition defaults to the
 * Brasileirão Série A, the competition people usually mean.
 */
import type { WorldRef } from './soccer-dsl.js';

const BRASILEIRAO = 'Brasileirão';

export class CompetitionsDsl {
  constructor(private readonly world: WorldRef) {}

  async confirmChampion({ season, competition = BRASILEIRAO, ...expected }: { season: number; competition?: string; team: string; points?: number; wins?: number; draws?: number; losses?: number }) {
    await (await this.world().system()).confirmChampion(season, competition, expected);
  }

  async confirmStandings({ season, competition = BRASILEIRAO, order }: { season: number; competition?: string; order: string[] }) {
    await (await this.world().system()).confirmStandingsOrder(season, competition, order);
  }

  async confirmRelegated({ season, competition = BRASILEIRAO, teams }: { season: number; competition?: string; teams: string[] }) {
    await (await this.world().system()).confirmRelegated(season, competition, teams);
  }

  async confirmBracket({ competition, season, stages }: { competition: string; season: number; stages: Record<string, string[]> }) {
    await (await this.world().system()).confirmBracket(competition, season, stages);
  }

  async confirmBracketIncludes({ competition, season, stage, teams }: { competition: string; season: number; stage: string; teams: string[] }) {
    await (await this.world().system()).confirmBracketIncludes(competition, season, stage, teams);
  }
}
