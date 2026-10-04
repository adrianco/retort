/**
 * Unit tests for the low-level parsing rules behind the acceptance specs:
 * team-name variants, date formats and CSV quoting.
 */
import { describe, expect, it } from 'vitest';
import { parseTeamName, TeamRegistry } from '../../src/domain/teams.js';
import { parseDate } from '../../src/data/dates.js';
import { parseCsv } from '../../src/data/csv.js';
import { parseCompetition } from '../../src/domain/model.js';

describe('team names', () => {
  it.each([
    ['Palmeiras-SP', 'palmeiras', 'SP'],
    ['América - MG', 'america', 'MG'],
    ['Botafogo RJ', 'botafogo', 'RJ'],
    ['Nacional (URU)', 'nacional', 'URU'],
    ['Nacional-URU', 'nacional', 'URU'],
    ['América FC (Minas Gerais)', 'america', 'MG'],
    ['Atletico Mineiro', 'atletico', 'MG'],
    ['Atlético-PR', 'athletico', 'PR'],
    ['Athletico', 'athletico', 'PR'],
    ['Sport Club Corinthians Paulista', 'corinthians', 'SP'],
    ['São Paulo FC', 'sao paulo', undefined],
    ['C.r.b. - AL', 'crb', 'AL'],
    ['Vasco da Gama-RJ', 'vasco', 'RJ'],
    ['Colo-Colo', 'colo colo', undefined],
  ])('reads %s as %s (%s)', (raw, base, region) => {
    const parsed = parseTeamName(raw);
    expect(parsed.base).toBe(base);
    expect(parsed.region).toBe(region);
  });

  it('keeps club affixes for FIFA club names, so foreign namesakes stay distinct', () => {
    expect(parseTeamName('Boavista FC', false).base).toBe('boavista fc');
    expect(parseTeamName('Boavista FC').base).toBe('boavista');
  });

  it("fills in a club's usual state and resolves variants to one team", () => {
    const registry = new TeamRegistry();
    for (const name of ['Botafogo-RJ', 'Botafogo-RJ', 'Botafogo - PB']) registry.observe(parseTeamName(name), true);
    const key = registry.register(parseTeamName('Botafogo'));
    registry.register(parseTeamName('Botafogo - PB'));
    expect(key).toBe('botafogo|RJ');
    expect(registry.resolve('botafogo')).toBe('botafogo|RJ');
    expect(registry.resolve('Botafogo-PB')).toBe('botafogo|PB');
    expect(registry.displayName('botafogo|RJ')).toBe('Botafogo-RJ');
  });
});

describe('dates', () => {
  it.each([
    ['2023-09-24', '2023-09-24', undefined],
    ['2012-05-19 18:30:00', '2012-05-19', '18:30'],
    ['29/03/2003', '2003-03-29', undefined],
  ])('reads %s', (raw, date, time) => {
    expect(parseDate(raw)).toEqual({ date, time });
  });

  it('treats missing or impossible dates as unknown', () => {
    expect(parseDate('NA')).toBeUndefined();
    expect(parseDate('31/02/2020')).toBeUndefined();
  });
});

describe('CSV', () => {
  it('handles a byte-order mark, quoted commas and doubled quotes', () => {
    const rows = parseCsv('﻿"a","b"\n"x, y","say ""hi"""\n');
    expect(rows).toEqual([{ a: 'x, y', b: 'say "hi"' }]);
  });
});

describe('competitions', () => {
  it.each([
    ['Serie A', 'Brasileirão'],
    ['brasileirao', 'Brasileirão'],
    ['Copa Libertadores', 'Libertadores'],
    ['Brazilian Cup', 'Copa do Brasil'],
    ['Série B', 'Serie B'],
  ])('reads %s as %s', (text, competition) => {
    expect(parseCompetition(text)).toBe(competition);
  });
});
