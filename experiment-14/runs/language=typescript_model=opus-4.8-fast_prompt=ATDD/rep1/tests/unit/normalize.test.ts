/**
 * Unit tests for the normalization layer that underpins consistent matching.
 */
import { describe, it, expect } from 'vitest';
import {
  cleanTeamName,
  teamKey,
  parseDate,
  parseGoals,
  deburr,
  foldText,
  extractState,
  wordMatch,
} from '../../src/domain/normalize.js';

describe('cleanTeamName', () => {
  it.each([
    ['Palmeiras-SP', 'Palmeiras'],
    ['Flamengo-RJ', 'Flamengo'],
    ['América - MG', 'América'],
    ['Nacional (URU)', 'Nacional'],
    ['Barcelona-EQU', 'Barcelona'],
    ['Boavista Sport Club (antigo Esporte Clube Barreira) - RJ', 'Boavista Sport Club'],
    ['Flamengo', 'Flamengo'],
  ])('cleans %s -> %s', (raw, expected) => {
    expect(cleanTeamName(raw)).toBe(expected);
  });
});

describe('teamKey', () => {
  it('collapses suffix/accent/case variants of the same club', () => {
    expect(teamKey('Grêmio-RS')).toBe(teamKey('gremio'));
    expect(teamKey('São Paulo')).toBe(teamKey('Sao Paulo-SP'));
    expect(teamKey('Atlético-MG')).toBe(teamKey('atletico'));
  });

  it('keeps different clubs distinct', () => {
    expect(teamKey('Flamengo')).not.toBe(teamKey('Fluminense'));
  });
});

describe('parseDate', () => {
  it.each([
    ['2023-09-24', '2023-09-24'],
    ['2012-05-19 18:30:00', '2012-05-19'],
    ['29/03/2003', '2003-03-29'],
    ['1/2/2010', '2010-02-01'],
  ])('parses %s -> %s', (raw, expected) => {
    expect(parseDate(raw)).toBe(expected);
  });
});

describe('parseGoals', () => {
  it.each([
    ['2', 2],
    ['1.0', 1],
    [3, 3],
    ['', 0],
    [undefined, 0],
  ])('parses %s -> %s', (raw, expected) => {
    expect(parseGoals(raw as any)).toBe(expected);
  });
});

describe('extractState', () => {
  it.each([
    ['Atletico-MG', 'mg'],
    ['América - RN', 'rn'],
    ['Nacional (URU)', 'uru'],
    ['Flamengo', ''],
  ])('extracts state from %s -> "%s"', (raw, expected) => {
    expect(extractState(raw)).toBe(expected);
  });
});

describe('wordMatch', () => {
  it('matches whole words only', () => {
    expect(wordMatch('final', 'final')).toBe(true);
    expect(wordMatch('semifinals', 'final')).toBe(false);
    expect(wordMatch('quarterfinals', 'final')).toBe(false);
    expect(wordMatch('group stage', 'stage')).toBe(true);
  });
});

describe('deburr / foldText', () => {
  it('removes accents and cedillas', () => {
    expect(deburr('São Grêmio Avaí')).toBe('Sao Gremio Avai');
    expect(foldText('  Éder   Militão ')).toBe('eder militao');
  });
});
