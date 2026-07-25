/**
 * Invariants over the real corpus.
 *
 * These assert facts that are independently checkable against the history of
 * Brazilian football -- a 20-team Série A plays 380 matches, 2003 and 2004 had
 * 24 teams and 552 -- so a regression in loading or merging shows up as a
 * historically wrong number rather than as an opaque count change.
 */

import { describe, expect, it } from 'vitest';
import { getGraph } from '../../src/graph/graph.js';
import { COMPETITIONS, hasScore } from '../../src/domain/types.js';
import { standings } from '../../src/query/competitionQueries.js';

const graph = getGraph();

describe('corpus', () => {
  it('reads every source file', () => {
    expect(Object.keys(graph.info.rawMatchRows).sort()).toEqual([
      'BR-Football-Dataset.csv',
      'Brasileirao_Matches.csv',
      'Brazilian_Cup_Matches.csv',
      'Libertadores_Matches.csv',
      'novo_campeonato_brasileiro.csv',
    ]);
    expect(graph.info.rawPlayerRows).toBe(18207);
  });

  it('loses almost no rows to parse failures', () => {
    // One Libertadores row carries season "NA" and no usable date; nothing else
    // in ~40k rows should be unreadable.
    expect(graph.info.skippedRows).toBeLessThanOrEqual(5);
  });

  it('merges away the overlap between the source files', () => {
    const rawTotal = Object.values(graph.info.rawMatchRows).reduce((a, b) => a + b, 0);
    expect(graph.info.mergedMatches).toBeLessThan(rawTotal);
    expect(graph.info.mergedMatches).toBeGreaterThan(15_000);
  });

  it('covers all five competitions', () => {
    for (const id of Object.keys(COMPETITIONS)) {
      const entry = graph.info.competitions.find((c) => c.id === id);
      expect(entry?.matches ?? 0).toBeGreaterThan(0);
    }
  });

  it('gives every match two distinct teams that exist in the registry', () => {
    for (const match of graph.matches) {
      expect(match.homeTeamId).not.toBe(match.awayTeamId);
      expect(graph.teams.get(match.homeTeamId)).toBeDefined();
      expect(graph.teams.get(match.awayTeamId)).toBeDefined();
    }
  });

  it('gives every match a well-formed date and a non-negative score', () => {
    for (const match of graph.matches) {
      expect(match.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      if (hasScore(match)) {
        expect(match.homeGoals).toBeGreaterThanOrEqual(0);
        expect(match.awayGoals).toBeGreaterThanOrEqual(0);
      }
    }
  });

  it('gives every match a unique id', () => {
    expect(new Set(graph.matches.map((m) => m.id)).size).toBe(graph.matches.length);
  });

  it('indexes each match under both of its teams', () => {
    const sample = graph.matches[Math.floor(graph.matches.length / 2)]!;
    expect(graph.matchesFor(sample.homeTeamId)).toContain(sample);
    expect(graph.matchesFor(sample.awayTeamId)).toContain(sample);
  });
});

describe('Série A season shapes', () => {
  // A double round-robin: n teams play n*(n-1) matches.
  const expected: Array<[number, number, number]> = [
    [2003, 24, 552],
    [2004, 24, 552],
    [2005, 22, 462],
    [2006, 20, 380],
    [2010, 20, 380],
    [2014, 20, 380],
    [2018, 20, 380],
    [2019, 20, 380],
    [2021, 20, 380],
  ];

  it.each(expected)('%i had %i teams and %i matches', (season, teams, matches) => {
    const table = standings(graph, 'serie-a', season);
    expect(table.rows).toHaveLength(teams);
    expect(table.matchesPlayed).toBe(matches);
    expect(table.complete).toBe(true);
  });

  it('every team in a complete season played 38 matches', () => {
    const table = standings(graph, 'serie-a', 2019);
    for (const row of table.rows) expect(row.record.played).toBe(38);
  });

  it('points equal three per win plus one per draw', () => {
    const table = standings(graph, 'serie-a', 2019);
    for (const row of table.rows) {
      expect(row.record.points).toBe(row.record.wins * 3 + row.record.draws);
      expect(row.record.wins + row.record.draws + row.record.losses).toBe(row.record.played);
    }
  });

  it('total goals for equal total goals against across the table', () => {
    const table = standings(graph, 'serie-a', 2019);
    const scored = table.rows.reduce((sum, row) => sum + row.record.goalsFor, 0);
    const conceded = table.rows.reduce((sum, row) => sum + row.record.goalsAgainst, 0);
    expect(scored).toBe(conceded);
  });

  it('reproduces the real 2019 title race', () => {
    const table = standings(graph, 'serie-a', 2019);
    expect(table.champion?.team.name).toBe('Flamengo');
    expect(table.champion?.record.points).toBe(90);
    expect(table.rows[1]?.team.name).toBe('Santos');
    expect(table.rows[2]?.team.name).toBe('Palmeiras');
    expect(table.relegated.map((r) => r.team.name)).toEqual([
      'Cruzeiro',
      'CSA',
      'Chapecoense',
      'Avaí',
    ]);
  });

  it('reproduces the real 2018 champion', () => {
    expect(standings(graph, 'serie-a', 2018).champion?.team.name).toBe('Palmeiras');
  });

  it('reproduces the real 2016 champion', () => {
    expect(standings(graph, 'serie-a', 2016).champion?.team.name).toBe('Palmeiras');
  });

  it('reproduces the real 2017 champion', () => {
    expect(standings(graph, 'serie-a', 2017).champion?.team.name).toBe('Corinthians');
  });
});

describe('players', () => {
  it('loads every FIFA row', () => {
    expect(graph.players).toHaveLength(18207);
  });

  it('finds the expected number of Brazilians', () => {
    expect(graph.playersOfNationality('Brazil').length).toBe(827);
  });

  it('parses money columns', () => {
    const messi = graph.players.find((p) => p.name === 'L. Messi');
    expect(messi?.valueEur).toBe(110_500_000);
    expect(messi?.wageEur).toBe(565_000);
  });

  it('classifies positions into groups', () => {
    const keeper = graph.players.find((p) => p.position === 'GK');
    expect(keeper?.positionGroup).toBe('Goalkeeper');
  });

  it('links only Brazilian club squads to the match data', () => {
    const linked = graph.players.filter((p) => p.clubTeamId);
    expect(linked.length).toBeGreaterThan(200);
    for (const player of linked) {
      const team = graph.teams.get(player.clubTeamId!);
      expect(team?.state).toBeDefined();
      expect(graph.matchesFor(player.clubTeamId!).length).toBeGreaterThan(0);
    }
  });
});
