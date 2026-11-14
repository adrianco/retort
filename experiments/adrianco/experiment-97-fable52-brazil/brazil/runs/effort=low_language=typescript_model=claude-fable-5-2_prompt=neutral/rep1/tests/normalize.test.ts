import { describe, expect, it } from 'vitest';
import { parseCsv } from '../src/csv.js';
import { clean, parseCompetition, parseDate, parseNum, teamKey } from '../src/normalize.js';

describe('Feature: Data quality handling', () => {
  describe('Scenario: Team name variations are normalised', () => {
    it.each([
      [['Palmeiras-SP', 'Palmeiras', 'Palmeiras - SP', 'palmeiras'], 'palmeiras'],
      [['Flamengo-RJ', 'Flamengo', 'Flamengo - RJ', 'Clube de Regatas do Flamengo'], 'flamengo'],
      [['São Paulo', 'Sao Paulo', 'Sao Paulo-SP', 'São Paulo FC', 'São Paulo - SP'], 'sao paulo'],
      [['Grêmio', 'Gremio-RS', 'Gremio RS', 'Grêmio - RS'], 'gremio'],
      [['Atlético-MG', 'Atletico-MG', 'Atlético - MG', 'Atletico Mineiro', 'Atlético Mineiro - MG'], 'atletico mg'],
      [['Athletico-PR', 'Atletico-PR', 'Atlético Paranaense - PR', 'Athletico Paranaense', 'Athletico'], 'athletico pr'],
      [['América-MG', 'America MG', 'América - MG', 'América FC (Minas Gerais)'], 'america mg'],
      [['Vasco', 'Vasco da Gama-RJ', 'Vasco da Gama - RJ'], 'vasco'],
      [['Sport', 'Sport-PE', 'Sport Club do Recife', 'Sport Recife'], 'sport'],
      [['CRB', 'C.r.b. - AL', 'C. R. B. - AL'], 'crb'],
      [['Sport Club Corinthians Paulista', 'Corinthians-SP'], 'corinthians'],
      [['Red Bull Bragantino-SP', 'Bragantino', 'Bragantino - SP'], 'bragantino'],
      [['Nacional (URU)', 'Nacional-URU'], 'nacional uru'],
      [['Fortaleza Esporte Clube', 'Fortaleza EC', 'Fortaleza - CE'], 'fortaleza'],
    ])('Given variants %j Then they share the key "%s"', (variants, key) => {
      for (const v of variants) expect(teamKey(v), v).toBe(key);
    });

    it('Then different clubs with the same base name stay distinct', () => {
      expect(teamKey('Atlético-GO')).not.toBe(teamKey('Atlético-MG'));
      expect(teamKey('Botafogo - PB')).not.toBe(teamKey('Botafogo-RJ'));
      expect(teamKey('Botafogo SP')).toBe('botafogo sp');
      expect(teamKey('Bragantino - PA')).not.toBe(teamKey('Bragantino - SP'));
      expect(teamKey('América - RN')).not.toBe(teamKey('América - MG'));
    });
  });

  describe('Scenario: Multiple date formats are parsed', () => {
    it('When given ISO, ISO with time, and Brazilian formats Then all become ISO dates', () => {
      expect(parseDate('2023-09-24')).toEqual({ date: '2023-09-24', time: null });
      expect(parseDate('2012-05-19 18:30:00')).toEqual({ date: '2012-05-19', time: '18:30' });
      expect(parseDate('29/03/2003')).toEqual({ date: '2003-03-29', time: null });
      expect(parseDate('NA').date).toBeNull();
      expect(parseDate(undefined).date).toBeNull();
    });
  });

  describe('Scenario: Scores and text are parsed safely', () => {
    it('Then numeric variants and missing markers are handled', () => {
      expect(parseNum('2')).toBe(2);
      expect(parseNum('2.0')).toBe(2);
      expect(parseNum('NA')).toBeNull();
      expect(parseNum('-')).toBeNull();
      expect(parseNum('')).toBeNull();
    });
    it('Then UTF-8 accents and cedillas are folded for matching', () => {
      expect(clean('São Paulo')).toBe('sao paulo');
      expect(clean('Avaí')).toBe('avai');
      expect(clean('Confiança')).toBe('confianca');
    });
    it('Then competition names are recognised in several spellings', () => {
      expect(parseCompetition('Brasileirão')).toBe('Brasileirão Série A');
      expect(parseCompetition('serie a')).toBe('Brasileirão Série A');
      expect(parseCompetition('Copa do Brasil')).toBe('Copa do Brasil');
      expect(parseCompetition('Copa Libertadores')).toBe('Copa Libertadores');
      expect(parseCompetition('Série B')).toBe('Série B');
      expect(parseCompetition('xyz')).toBeUndefined();
    });
  });

  describe('Scenario: CSV parsing', () => {
    it('Then quoted fields, embedded commas, escaped quotes, CRLF and BOM are handled', () => {
      const rows = parseCsv('\ufeffa,b,c\r\n"x, y","say ""hi""",3\r\n1,,"Jul 1, 2004"\n');
      expect(rows).toEqual([
        { a: 'x, y', b: 'say "hi"', c: '3' },
        { a: '1', b: '', c: 'Jul 1, 2004' },
      ]);
    });
  });
});
