import { describe, expect, it } from 'vitest';
import { parseCsv } from '../src/csv.js';
import { parseDate } from '../src/data.js';
import { parseTeamName } from '../src/teams.js';
import { compactYears } from '../src/tools.js';
import { kb } from './helpers.js';

describe('Feature: CSV parsing', () => {
  it('Scenario: quoted fields, embedded commas, escaped quotes, BOM and CRLF', () => {
    const rows = parseCsv('﻿a,b,c\r\n1,"x, y","say ""hi"""\r\n2,,z\n');
    expect(rows).toEqual([
      { a: '1', b: 'x, y', c: 'say "hi"' },
      { a: '2', b: '', c: 'z' },
    ]);
  });
});

describe('Feature: Date formats', () => {
  it.each([
    ['2023-09-24', '2023-09-24', undefined],
    ['29/03/2003', '2003-03-29', undefined],
    ['2012-05-19 18:30:00', '2012-05-19', '18:30'],
  ])('Scenario: %s is read as %s', (input, date, time) => {
    expect(parseDate(input)).toEqual({ date, time });
  });

  it('Scenario: garbage is rejected', () => {
    expect(parseDate('NA')).toBeUndefined();
  });
});

describe('Feature: Team name normalisation', () => {
  it('Scenario: state suffixes are split from the name', () => {
    expect(parseTeamName('Palmeiras-SP')).toMatchObject({ base: 'palmeiras', tag: 'SP' });
    expect(parseTeamName('Atlético - MG')).toMatchObject({ base: 'atletico', tag: 'MG' });
    expect(parseTeamName('Botafogo PB')).toMatchObject({ base: 'botafogo', tag: 'PB' });
    expect(parseTeamName('Nacional (URU)')).toMatchObject({ base: 'nacional', tag: 'URU' });
    expect(parseTeamName('C. R. B. - AL')).toMatchObject({ base: 'crb', tag: 'AL' });
  });

  it.each([
    ['Flamengo', ['Flamengo-RJ', 'Flamengo - RJ', 'flamengo', 'Clube de Regatas do Flamengo']],
    ['Corinthians', ['Corinthians-SP', 'Sport Club Corinthians Paulista']],
    ['São Paulo', ['Sao Paulo', 'Sao Paulo-SP', 'São Paulo FC']],
    ['Grêmio', ['Gremio', 'Gremio RS', 'Grêmio - RS']],
    ['Atlético-MG', ['Atletico Mineiro', 'Atlético - MG', 'Atletico-MG']],
    ['Athletico-PR', ['Atletico-PR', 'Athletico Paranaense', 'Atlético Paranaense - PR', 'Athletico']],
    ['Vasco', ['Vasco da Gama-RJ', 'Vasco Da Gama RJ']],
    ['Sport', ['Sport Recife', 'Sport-PE', 'Sport Club do Recife']],
    ['Bahia', ['EC Bahia', 'Bahia - BA']],
    ['Bragantino', ['Red Bull Bragantino-SP', 'Bragantino - SP']],
  ])('Scenario: every spelling of %s resolves to one team', (display, variants) => {
    const ids = new Set([display, ...variants].map((v) => kb.team(v)));
    expect(ids.size).toBe(1);
    expect(kb.teamName([...ids][0])).toBe(display);
  });

  it('Scenario: namesakes from other states stay separate teams', () => {
    expect(kb.team('Botafogo PB')).not.toBe(kb.team('Botafogo'));
    expect(kb.team('Flamengo - PI')).not.toBe(kb.team('Flamengo'));
    expect(kb.team('Atlético-GO')).not.toBe(kb.team('Atlético-MG'));
    expect(kb.team('América-RN')).not.toBe(kb.team('América-MG'));
    expect(kb.teamName(kb.team('Botafogo PB'))).toBe('Botafogo-PB');
  });

  it('Scenario: an unknown team gives a clear error', () => {
    expect(() => kb.team('Real Madrid Galacticos')).toThrow(/No team matching/);
  });
});

describe('Feature: helpers', () => {
  it('Scenario: years are compacted into ranges', () => {
    expect(compactYears([2012, 2013, 2014, 2016])).toBe('2012-2014, 2016');
    expect(compactYears([])).toBe('none');
  });
});
