/**
 * The acceptance-test DSL: the vocabulary the specs are written in.
 *
 * `useSoccerDsl()` wires a fresh world for every test: a private set of
 * synthetic datasets (functional isolation – no test can see another test's
 * data) and a protocol driver that talks to the system through its public
 * MCP interface. The system is started lazily, the first time a spec asks a
 * question, so every `given` step lands in the datasets before they are read.
 *
 * With `{ datasets: 'provided' }` the specs instead run against the real
 * Kaggle files shipped in data/kaggle, sharing one running system.
 */
import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest';
import { DatasetStub } from '../drivers/dataset-stub.js';
import { McpSoccerDriver } from '../drivers/mcp-soccer-driver.js';
import type { SoccerSystemDriver } from '../drivers/soccer-system-driver.js';
import { GivenDsl } from './given-dsl.js';
import { MatchesDsl } from './matches-dsl.js';
import { TeamsDsl } from './teams-dsl.js';
import { PlayersDsl } from './players-dsl.js';
import { CompetitionsDsl } from './competitions-dsl.js';
import { StatisticsDsl } from './statistics-dsl.js';
import { DatasetsDsl, PerformanceDsl } from './system-dsl.js';
import { PROVIDED_DATA_DIR } from '../drivers/paths.js';

export class TestWorld {
  private started = false;
  private readonly sequences = new Map<string, number>();

  constructor(
    readonly datasets: DatasetStub | null,
    readonly driver: SoccerSystemDriver,
  ) {}

  /** The system under test, started on first use. */
  async system(): Promise<SoccerSystemDriver> {
    if (!this.started) {
      await this.datasets?.publish();
      await this.driver.start();
      this.started = true;
    }
    return this.driver;
  }

  stub(): DatasetStub {
    if (!this.datasets) throw new Error('This spec runs against the provided datasets and cannot add data');
    if (this.started) throw new Error('Data must be given before the first question is asked');
    return this.datasets;
  }

  /** Test-scoped sequence generator: 1, 2, 3... per named sequence. */
  next(sequence: string): number {
    const value = (this.sequences.get(sequence) ?? 0) + 1;
    this.sequences.set(sequence, value);
    return value;
  }

  async dispose(): Promise<void> {
    await this.driver.stop();
    await this.datasets?.dispose();
  }
}

export type WorldRef = () => TestWorld;

export interface DslOptions {
  datasets?: 'synthetic' | 'provided';
}

export function useSoccerDsl({ datasets = 'synthetic' }: DslOptions = {}) {
  let world: TestWorld | undefined;
  const ref: WorldRef = () => {
    if (!world) throw new Error('The test world has not been created');
    return world;
  };

  if (datasets === 'provided') {
    beforeAll(async () => {
      world = new TestWorld(null, new McpSoccerDriver(PROVIDED_DATA_DIR));
      await world.system();
    });
    afterAll(async () => world?.dispose());
  } else {
    beforeEach(async () => {
      const stub = await DatasetStub.create();
      world = new TestWorld(stub, new McpSoccerDriver(stub.directory));
    });
    afterEach(async () => world?.dispose());
  }

  return {
    given: new GivenDsl(ref),
    matches: new MatchesDsl(ref),
    teams: new TeamsDsl(ref),
    players: new PlayersDsl(ref),
    competitions: new CompetitionsDsl(ref),
    statistics: new StatisticsDsl(ref),
    datasets: new DatasetsDsl(ref),
    performance: new PerformanceDsl(ref),
  };
}
