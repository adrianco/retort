/**
 * Wiring for executable specifications: gives each spec the DSL areas it
 * asks for, backed by a protocol driver connected to the system under test.
 *
 *  - `spec`             — a fresh system per test holding only the synthetic
 *                         data that the test describes.
 *  - `providedDataSpec` — one system per spec file, loaded with the provided
 *                         Kaggle datasets (read-only, so safe to share).
 */
import { test } from 'vitest';
import type { SoccerDriver } from '../drivers/soccer-driver.js';
import { McpSoccerDriver } from '../drivers/mcp/mcp-soccer-driver.js';
import { GivenDsl } from './given.js';
import { MatchesDsl } from './matches.js';
import { TeamsDsl } from './teams.js';
import { PlayersDsl } from './players.js';
import { CompetitionsDsl } from './competitions.js';
import { StatisticsDsl } from './statistics.js';
import { AnswersDsl, DatasetsDsl } from './datasets.js';

export interface QuestionAreas {
  matches: MatchesDsl;
  teams: TeamsDsl;
  players: PlayersDsl;
  competitions: CompetitionsDsl;
  statistics: StatisticsDsl;
}

export interface SoccerSpecContext extends QuestionAreas {
  given: GivenDsl;
  datasets: DatasetsDsl;
  answers: AnswersDsl;
}

type Use<T> = (value: T) => Promise<void>;

const dslAreas = {
  given: async ({ driver }: { driver: SoccerDriver }, use: Use<GivenDsl>) => use(new GivenDsl(driver)),
  matches: async ({ driver }: { driver: SoccerDriver }, use: Use<MatchesDsl>) => use(new MatchesDsl(driver)),
  teams: async ({ driver }: { driver: SoccerDriver }, use: Use<TeamsDsl>) => use(new TeamsDsl(driver)),
  players: async ({ driver }: { driver: SoccerDriver }, use: Use<PlayersDsl>) => use(new PlayersDsl(driver)),
  competitions: async ({ driver }: { driver: SoccerDriver }, use: Use<CompetitionsDsl>) => use(new CompetitionsDsl(driver)),
  statistics: async ({ driver }: { driver: SoccerDriver }, use: Use<StatisticsDsl>) => use(new StatisticsDsl(driver)),
  datasets: async ({ driver }: { driver: SoccerDriver }, use: Use<DatasetsDsl>) => use(new DatasetsDsl(driver)),
  answers: async ({ driver }: { driver: SoccerDriver }, use: Use<AnswersDsl>) => use(new AnswersDsl(driver)),
};

export const spec = test.extend<SoccerSpecContext & { driver: SoccerDriver }>({
  driver: async ({}, use: Use<SoccerDriver>) => {
    const driver = McpSoccerDriver.withSyntheticData();
    try {
      await use(driver);
    } finally {
      await driver.close();
    }
  },
  ...dslAreas,
});

export const providedDataSpec = test.extend<{ $file: { driver: SoccerDriver }; $test: SoccerSpecContext }>({
  driver: [
    async ({}, use: Use<SoccerDriver>) => {
      const driver = McpSoccerDriver.withProvidedData();
      await driver.start();
      try {
        await use(driver);
      } finally {
        await driver.close();
      }
    },
    { scope: 'file' },
  ],
  ...dslAreas,
});
