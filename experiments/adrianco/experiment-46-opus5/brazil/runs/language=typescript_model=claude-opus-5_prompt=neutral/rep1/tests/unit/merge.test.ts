/**
 * De-duplication rules, exercised on synthetic rows so each rule can be
 * isolated. Série A 2014-2019 is described by three source files at once, so
 * getting this wrong would inflate every aggregate by up to 3x.
 */

import { describe, expect, it } from 'vitest';
import { mergeMatches, type RawMatch } from '../../src/data/loadMatches.js';

function row(overrides: Partial<RawMatch> = {}): RawMatch {
  return {
    source: 'brasileirao',
    competition: 'serie-a',
    season: 2019,
    date: '2019-09-03',
    homeTeamId: 'flamengo-rj',
    awayTeamId: 'fluminense-rj',
    homeGoals: 2,
    awayGoals: 1,
    ...overrides,
  };
}

describe('mergeMatches', () => {
  it('collapses the same league fixture reported by three files', () => {
    const merged = mergeMatches([
      row({ source: 'brasileirao', round: 22 }),
      row({ source: 'novo-brasileirao', venue: 'Maracanã' }),
      row({ source: 'br-football', stats: { homeShots: 12 } }),
    ]);

    expect(merged).toHaveLength(1);
    expect(merged[0]!.sources.sort()).toEqual(['br-football', 'brasileirao', 'novo-brasileirao']);
  });

  it('fills gaps from lower-priority sources without overwriting', () => {
    const merged = mergeMatches([
      row({ source: 'brasileirao', round: 22 }),
      row({ source: 'novo-brasileirao', round: 99, venue: 'Maracanã' }),
      row({ source: 'br-football', stats: { homeShots: 12 } }),
    ]);

    // Round comes from the higher-priority file, venue and stats only exist lower down.
    expect(merged[0]!.round).toBe(22);
    expect(merged[0]!.venue).toBe('Maracanã');
    expect(merged[0]!.stats?.homeShots).toBe(12);
  });

  it('merges a league fixture whose sources disagree on the date by weeks', () => {
    const merged = mergeMatches([
      row({ source: 'brasileirao', date: '2022-10-15', homeGoals: null, awayGoals: null }),
      row({ source: 'br-football', date: '2022-10-29', homeGoals: 0, awayGoals: 0 }),
    ]);

    expect(merged).toHaveLength(1);
    // A row that recorded a score outranks one that did not, so the postponed
    // date and the real result are kept together.
    expect(merged[0]!.date).toBe('2022-10-29');
    expect(merged[0]!.homeGoals).toBe(0);
  });

  it('keeps two league meetings with the same home team months apart', () => {
    // novo_campeonato_brasileiro.csv files both 2009 legs of Botafogo v Flamengo
    // under Botafogo at home; they are still two different matches.
    const merged = mergeMatches([
      row({ source: 'novo-brasileirao', date: '2009-07-19', season: 2009, round: 12 }),
      row({ source: 'novo-brasileirao', date: '2009-10-25', season: 2009, round: 31 }),
    ]);
    expect(merged).toHaveLength(2);
  });

  it('keeps the same pairing in different seasons apart', () => {
    const merged = mergeMatches([
      row({ season: 2018, date: '2018-09-03' }),
      row({ season: 2019, date: '2019-09-03' }),
    ]);
    expect(merged).toHaveLength(2);
  });

  it('keeps a Série C pair that meets twice in a season apart', () => {
    // Série C runs a second group phase, so the same ordered pair really can
    // play twice in one year -- unlike Série A and B.
    const merged = mergeMatches([
      row({ competition: 'serie-c', source: 'br-football', season: 2023, date: '2023-05-03' }),
      row({ competition: 'serie-c', source: 'br-football', season: 2023, date: '2023-10-22' }),
    ]);
    expect(merged).toHaveLength(2);
  });

  it('keeps the same pairing in different competitions apart', () => {
    const merged = mergeMatches([
      row({ competition: 'serie-a' }),
      row({ competition: 'copa-do-brasil', source: 'copa-do-brasil' }),
    ]);
    expect(merged).toHaveLength(2);
  });

  it('keeps the two legs of a cup tie apart', () => {
    const merged = mergeMatches([
      row({ competition: 'copa-do-brasil', source: 'copa-do-brasil', date: '2019-05-01' }),
      row({ competition: 'copa-do-brasil', source: 'copa-do-brasil', date: '2019-05-22' }),
    ]);
    expect(merged).toHaveLength(2);
  });

  it('merges cup rows dated a day apart by different sources', () => {
    const merged = mergeMatches([
      row({ competition: 'copa-do-brasil', source: 'copa-do-brasil', date: '2019-05-01' }),
      row({ competition: 'copa-do-brasil', source: 'br-football', date: '2019-05-02' }),
    ]);
    expect(merged).toHaveLength(1);
  });

  it('does not merge the reverse fixture', () => {
    const merged = mergeMatches([
      row(),
      row({ homeTeamId: 'fluminense-rj', awayTeamId: 'flamengo-rj', date: '2019-05-28' }),
    ]);
    expect(merged).toHaveLength(2);
  });

  it('returns matches in date order', () => {
    const merged = mergeMatches([
      row({ season: 2019, date: '2019-09-03' }),
      row({ season: 2017, date: '2017-09-03' }),
      row({ season: 2018, date: '2018-09-03' }),
    ]);
    expect(merged.map((m) => m.date)).toEqual(['2017-09-03', '2018-09-03', '2019-09-03']);
  });

  it('gives every merged match a distinct id', () => {
    const merged = mergeMatches([
      row({ season: 2017, date: '2017-09-03' }),
      row({ season: 2018, date: '2018-09-03' }),
      row({ season: 2019, date: '2019-09-03' }),
    ]);
    expect(new Set(merged.map((m) => m.id)).size).toBe(3);
  });
});

describe('score integrity', () => {
  it('takes both halves of a score from the same source', () => {
    // Composing "2" from one row and "3" from another would report a result
    // that no source ever recorded.
    const merged = mergeMatches([
      row({ source: 'brasileirao', homeGoals: 2, awayGoals: null }),
      row({ source: 'br-football', homeGoals: null, awayGoals: 3 }),
    ]);
    expect(merged).toHaveLength(1);
    const { homeGoals, awayGoals } = merged[0]!;
    expect(homeGoals === null || awayGoals === null || (homeGoals === 2 && awayGoals === 3)).toBe(
      true,
    );
    // Specifically: the fabricated 2-3 must not appear.
    expect(`${homeGoals}-${awayGoals}`).not.toBe('2-3');
  });
});
