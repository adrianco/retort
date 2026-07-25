/**
 * The specification's latency budget: simple lookups under 2 s, aggregate
 * queries under 5 s, no timeouts. The graph is built before timing starts,
 * matching the server, which loads the CSVs before accepting a connection.
 */

import { beforeAll, describe, expect, it } from 'vitest';
import { buildGraph, getGraph } from '../src/graph/graph.js';
import { toolByName } from '../src/tools/index.js';

const graph = getGraph();

function time(tool: string, args: Record<string, unknown>): number {
  const definition = toolByName(tool)!;
  const parsed = definition.schema.parse(args);
  const started = performance.now();
  definition.handler(graph, parsed as never);
  return performance.now() - started;
}

// The specification allows 2 s and 5 s. Measured values are 0-6 ms and 1-5 ms,
// so asserting the specification limit would pass through a 100x regression.
// These are set well above observed noise but far below the stated ceiling, so
// they still fail long before a user would notice.
const SIMPLE_BUDGET_MS = 250;
const AGGREGATE_BUDGET_MS = 750;
const SPEC_SIMPLE_BUDGET_MS = 2000;
const SPEC_AGGREGATE_BUDGET_MS = 5000;

describe('query performance', () => {
  beforeAll(() => {
    // Warm the indexes so the first measured call is not paying for lazy work.
    time('dataset_info', {});
  });

  const simple: Array<[string, Record<string, unknown>]> = [
    ['search_matches', { team: 'Flamengo', opponent: 'Corinthians', limit: 20 }],
    ['head_to_head', { teamA: 'Palmeiras', teamB: 'Santos' }],
    ['team_stats', { team: 'Corinthians', season: 2022, competition: 'serie-a', venue: 'home' }],
    ['player_profile', { name: 'Neymar' }],
    ['search_players', { nationality: 'Brazil', limit: 25 }],
    ['competition_standings', { competition: 'serie-a', season: 2019 }],
    ['list_teams', { limit: 60 }],
  ];

  it.each(simple)('%s responds well inside the simple-lookup budget', (tool, args) => {
    expect(time(tool, args)).toBeLessThan(SIMPLE_BUDGET_MS);
  });

  const aggregate: Array<[string, Record<string, unknown>]> = [
    ['match_statistics', {}],
    ['record_extremes', { kind: 'biggest-margin', limit: 25 }],
    ['team_rankings', { metric: 'points', venue: 'away', minimumPlayed: 10 }],
    ['compare_seasons', { competition: 'serie-a', seasons: [2015, 2016, 2017, 2018, 2019] }],
    ['find_derbies', { limit: 200 }],
    ['team_profile', { team: 'Flamengo' }],
    ['club_squad', {}],
  ];

  it.each(aggregate)('%s responds well inside the aggregate budget', (tool, args) => {
    expect(time(tool, args)).toBeLessThan(AGGREGATE_BUDGET_MS);
  });

  it('does not slow down as queries accumulate', () => {
    const run = (count: number) => {
      const started = performance.now();
      for (let i = 0; i < count; i++) {
        time('team_stats', { team: 'Palmeiras', season: 2010 + (i % 13) });
      }
      return performance.now() - started;
    };

    run(50); // warm up
    const first = run(200);
    const second = run(200);
    // Compares like for like rather than against a fixed ceiling: per-query
    // cost must not grow as the process does more work (a cache that only ever
    // grows, or an index rebuilt per call, would show up here).
    expect(second).toBeLessThan(Math.max(first * 3, 50));
  });

  it('stays inside the budgets the specification states', () => {
    expect(SIMPLE_BUDGET_MS).toBeLessThan(SPEC_SIMPLE_BUDGET_MS);
    expect(AGGREGATE_BUDGET_MS).toBeLessThan(SPEC_AGGREGATE_BUDGET_MS);
    expect(time('competition_standings', { competition: 'serie-a', season: 2019 })).toBeLessThan(
      SPEC_SIMPLE_BUDGET_MS,
    );
    expect(time('match_statistics', {})).toBeLessThan(SPEC_AGGREGATE_BUDGET_MS);
  });

  it('loads the whole corpus in a few seconds', () => {
    const started = performance.now();
    buildGraph();
    expect(performance.now() - started).toBeLessThan(15_000);
  });
});
