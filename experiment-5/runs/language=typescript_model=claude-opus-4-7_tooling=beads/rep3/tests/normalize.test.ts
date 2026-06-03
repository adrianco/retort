import { describe, it, expect } from 'vitest';
import {
  normalizeTeamName,
  parseDate,
  parseNumber,
  extractStateSuffix,
  teamMatches,
} from '../src/normalize.js';

describe('Feature: Team name normalization', () => {
  describe('Scenario: Preserve disambiguating state suffix', () => {
    it('Given a team with -SP suffix, When normalized, Then canonical is "palmeiras-sp"', () => {
      expect(normalizeTeamName('Palmeiras-SP')).toBe('palmeiras-sp');
    });

    it('Given "Atletico-MG" and "Atletico-GO", When normalized, Then they remain distinct', () => {
      expect(normalizeTeamName('Atletico-MG')).toBe('atletico-mg');
      expect(normalizeTeamName('Atletico-GO')).toBe('atletico-go');
      expect(normalizeTeamName('Atletico-MG')).not.toBe(normalizeTeamName('Atletico-GO'));
    });

    it('Given full name "Sport Club Corinthians Paulista", When normalized, Then becomes "corinthians"', () => {
      expect(normalizeTeamName('Sport Club Corinthians Paulista')).toBe('corinthians');
    });
  });

  describe('Scenario: Country suffixes in continental matches are preserved', () => {
    it('Given "Nacional (URU)", When normalized, Then becomes "nacional-uru"', () => {
      expect(normalizeTeamName('Nacional (URU)')).toBe('nacional-uru');
    });

    it('Given "Barcelona-EQU", When normalized, Then becomes "barcelona-equ"', () => {
      expect(normalizeTeamName('Barcelona-EQU')).toBe('barcelona-equ');
    });
  });

  describe('Scenario: Handle accented characters', () => {
    it('Given "São Paulo", When normalized, Then accents are stripped', () => {
      expect(normalizeTeamName('São Paulo')).toBe('sao paulo');
    });

    it('Given "Grêmio-RS", When normalized, Then accents are stripped and suffix retained', () => {
      expect(normalizeTeamName('Grêmio-RS')).toBe('gremio-rs');
    });
  });

  describe('Scenario: Extract state suffix', () => {
    it('Given "Palmeiras-SP", Then state is SP', () => {
      expect(extractStateSuffix('Palmeiras-SP')).toBe('SP');
    });

    it('Given "Flamengo" without suffix, Then state is undefined', () => {
      expect(extractStateSuffix('Flamengo')).toBeUndefined();
    });
  });
});

describe('Feature: Lenient team matching', () => {
  it('Given query "Flamengo", When tested against canonical "flamengo-rj", Then it matches', () => {
    expect(teamMatches('flamengo-rj', 'Flamengo')).toBe(true);
  });

  it('Given query "Flamengo-RJ", When tested against canonical "flamengo-rj", Then it matches', () => {
    expect(teamMatches('flamengo-rj', 'Flamengo-RJ')).toBe(true);
  });

  it('Given query "Atletico-MG", When tested against "atletico-go", Then it does not match', () => {
    expect(teamMatches('atletico-go', 'Atletico-MG')).toBe(false);
  });

  it('Given query "Atletico" (no suffix), When tested, Then both atletico-mg and atletico-go match', () => {
    expect(teamMatches('atletico-mg', 'Atletico')).toBe(true);
    expect(teamMatches('atletico-go', 'Atletico')).toBe(true);
  });
});

describe('Feature: Date parsing', () => {
  describe('Scenario: Parse ISO date with time', () => {
    it('Given "2012-05-19 18:30:00", Then date is "2012-05-19"', () => {
      const { date, datetime } = parseDate('2012-05-19 18:30:00');
      expect(date).toBe('2012-05-19');
      expect(datetime).toBe('2012-05-19 18:30:00');
    });
  });

  describe('Scenario: Parse Brazilian date', () => {
    it('Given "29/03/2003", Then date is "2003-03-29"', () => {
      expect(parseDate('29/03/2003').date).toBe('2003-03-29');
    });
  });

  describe('Scenario: Parse ISO date only', () => {
    it('Given "2023-09-24", Then date is preserved', () => {
      expect(parseDate('2023-09-24').date).toBe('2023-09-24');
    });
  });
});

describe('Feature: Number parsing', () => {
  it('Given quoted number "2", Then parsed as 2', () => {
    expect(parseNumber('"2"')).toBe(2);
  });
  it('Given empty string, Then parsed as 0', () => {
    expect(parseNumber('')).toBe(0);
  });
});
