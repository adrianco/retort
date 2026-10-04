/**
 * DSL: finding players.
 */
import type { WorldRef } from './soccer-dsl.js';
import type { PlayerCriteria } from '../drivers/soccer-system-driver.js';

export class PlayersDsl {
  constructor(private readonly world: WorldRef) {}

  async confirmProfile({ name, ...expected }: { name: string; club?: string; position?: string; overall?: number; nationality?: string }) {
    await (await this.world().system()).confirmPlayerProfile(name, expected);
  }

  async confirmUnknown({ name, suggesting }: { name: string; suggesting: string[] }) {
    await (await this.world().system()).confirmPlayerUnknown(name, suggesting);
  }

  async confirmFound({ expected, ...criteria }: PlayerCriteria & { expected: string[] }) {
    await (await this.world().system()).confirmPlayersFound(criteria, expected);
  }

  async confirmFoundAtLeast({ count, ...criteria }: PlayerCriteria & { count: number }) {
    await (await this.world().system()).confirmPlayersFoundAtLeast(criteria, count);
  }

  async confirmNoneFound(criteria: PlayerCriteria) {
    await (await this.world().system()).confirmNoPlayersFound(criteria);
  }

  async confirmClubSummary({ nationality, clubs }: { nationality?: string; clubs: Array<{ club: string; players: number; averageOverall: number }> }) {
    await (await this.world().system()).confirmClubSummary(nationality, clubs);
  }

  async confirmClubSummaryIncludes({ nationality, clubs }: { nationality?: string; clubs: string[] }) {
    await (await this.world().system()).confirmClubSummaryIncludes(nationality, clubs);
  }
}
