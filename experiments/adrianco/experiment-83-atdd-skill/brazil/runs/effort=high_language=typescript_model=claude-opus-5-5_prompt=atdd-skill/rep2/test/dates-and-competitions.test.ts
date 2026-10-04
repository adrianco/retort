import { describe, expect, it } from 'vitest';
import { normaliseStage, parseCompetition } from '../src/competitions.js';
import { normaliseDateInput, parseDate } from '../src/dates.js';

describe('parseDate', () => {
  it.each([
    ['2023-09-24', { date: '2023-09-24' }],
    ['2012-05-19 18:30:00', { date: '2012-05-19', time: '18:30' }],
    ['29/03/2003', { date: '2003-03-29' }],
    ['1/2/2010', { date: '2010-02-01' }],
  ])('reads %s', (raw, expected) => {
    expect(parseDate(raw)).toEqual(expect.objectContaining(expected));
  });

  it.each(['NA', '', 'yesterday'])('rejects "%s"', (raw) => {
    expect(parseDate(raw)).toBeNull();
  });

  it('accepts a bare year as the start of that year', () => {
    expect(normaliseDateInput('2019')).toBe('2019-01-01');
  });
});

describe('parseCompetition', () => {
  it.each([
    ['Brasileirão', 'serie-a'],
    ['brasileirao serie a', 'serie-a'],
    ['Série A', 'serie-a'],
    ['Serie B', 'serie-b'],
    ['Copa do Brasil', 'copa-do-brasil'],
    ['Brazilian Cup', 'copa-do-brasil'],
    ['Libertadores', 'libertadores'],
    ['Copa Libertadores', 'libertadores'],
  ])('reads %s', (raw, id) => {
    expect(parseCompetition(raw)).toBe(id);
  });

  it('explains which competitions exist when it cannot recognise one', () => {
    expect(() => parseCompetition('Premier League')).toThrow(/Copa Libertadores/);
  });
});

describe('normaliseStage', () => {
  it.each([
    ['Finals', 'final'],
    ['semi-finals', 'semifinals'],
    ['Quarter finals', 'quarterfinals'],
    ['last 16', 'round of 16'],
    ['group', 'group stage'],
  ])('reads %s', (raw, stage) => {
    expect(normaliseStage(raw)).toBe(stage);
  });
});
