import { describe, expect, it } from 'vitest';
import { COMPETITIONS, FILES } from '../src/data.js';
import { kb } from './helpers.js';

describe('Feature: Data coverage', () => {
  it('Scenario: all six CSV files are loaded with their full row counts', () => {
    expect(kb.data.rowCounts).toEqual({
      [FILES.historical]: 6886,
      [FILES.brasileirao]: 4180,
      [FILES.cup]: 1337,
      [FILES.libertadores]: 1255,
      [FILES.extended]: 10296,
      [FILES.fifa]: 18207,
    });
  });

  it('Scenario: every match file contributes queryable matches', () => {
    const sources = new Set(kb.data.matches.flatMap((m) => m.sources));
    for (const f of [FILES.historical, FILES.brasileirao, FILES.cup, FILES.libertadores, FILES.extended]) {
      expect(sources).toContain(f);
    }
    expect(kb.data.players).toHaveLength(18207);
  });

  it('Scenario: every match has a date, teams, scores and a competition', () => {
    const known = new Set<string>(Object.values(COMPETITIONS));
    for (const m of kb.data.matches) {
      expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(known.has(m.competition)).toBe(true);
      expect(Number.isInteger(m.homeGoals) && Number.isInteger(m.awayGoals)).toBe(true);
      expect(m.home && m.away && m.home !== m.away).toBeTruthy();
    }
  });

  it('Scenario: the same fixture found in several files is merged, not double counted', () => {
    // 20 teams play 380 matches; 2012-2019 are present in up to three files.
    for (let season = 2006; season <= 2022; season++) {
      expect(kb.findMatches({ competition: 'Brasileirão', season }), `season ${season}`).toHaveLength(380);
    }
    const merged = kb.findMatches({ competition: 'Brasileirão', season: 2019, homeTeam: 'Flamengo', awayTeam: 'Grêmio' });
    expect(merged).toHaveLength(1);
    expect(merged[0].sources).toEqual([FILES.historical, FILES.brasileirao, FILES.extended]);
    // Merging keeps the best of each file: stadium, round and shot statistics.
    expect(merged[0]).toMatchObject({ homeGoals: 3, awayGoals: 1, round: '14', arena: 'Maracanã' });
    expect(merged[0].stats?.homeShots).toBeGreaterThan(0);
  });

  it('Scenario: the pandemic-delayed 2020 season is attributed to 2020, not 2021', () => {
    const late = kb.findMatches({ competition: 'Brasileirão', season: 2020, dateFrom: '2021-01-01' });
    expect(late.length).toBeGreaterThan(50);
    expect(kb.findMatches({ competition: 'Série B', season: 2020, dateFrom: '2021-01-01' }).length).toBeGreaterThan(0);
  });

  it('Scenario: unplayed fixtures without a score are skipped', () => {
    // Chapecoense v Atlético-MG (2016, round 38) was never played after the air disaster.
    const m = kb.findMatches({ season: 2016, competition: 'Brasileirão', homeTeam: 'Chapecoense', awayTeam: 'Atlético-MG' });
    expect(m).toHaveLength(1);
    expect(m[0].sources).toEqual([FILES.historical]);
  });
});
