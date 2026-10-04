/**
 * DSL: the datasets the system has loaded and how quickly it answers.
 */
import type { WorldRef } from './soccer-dsl.js';

export class DatasetsDsl {
  constructor(private readonly world: WorldRef) {}

  async confirmLoaded(recordsByFile: Record<string, number>) {
    await (await this.world().system()).confirmDatasetsLoaded(recordsByFile);
  }
}

export class PerformanceDsl {
  constructor(private readonly world: WorldRef) {}

  async confirmSimpleLookupsWithin({ seconds }: { seconds: number }) {
    await (await this.world().system()).confirmSimpleLookupsWithin(seconds);
  }

  async confirmAggregateQueriesWithin({ seconds }: { seconds: number }) {
    await (await this.world().system()).confirmAggregateQueriesWithin(seconds);
  }
}
