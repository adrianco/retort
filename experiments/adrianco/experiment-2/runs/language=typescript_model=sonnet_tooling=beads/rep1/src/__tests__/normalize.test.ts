import { describe, it, expect } from 'vitest';
import { normalizeTeamName, teamsMatch, teamMatchesQuery } from '../normalize.js';

describe('Feature: Team name normalization', () => {
  describe('Scenario: Strip state suffixes', () => {
    it('Given "Palmeiras-SP", When normalized, Then returns "Palmeiras"', () => {
      expect(normalizeTeamName('Palmeiras-SP')).toBe('Palmeiras');
    });
    it('Given "Flamengo-RJ", When normalized, Then returns "Flamengo"', () => {
      expect(normalizeTeamName('Flamengo-RJ')).toBe('Flamengo');
    });
    it('Given "Sport-PE", When normalized, Then returns "Sport"', () => {
      expect(normalizeTeamName('Sport-PE')).toBe('Sport');
    });
  });

  describe('Scenario: Handle alias variations', () => {
    it('Given "Atletico-MG", When normalized, Then returns "Atlético Mineiro"', () => {
      expect(normalizeTeamName('Atletico-MG')).toBe('Atlético Mineiro');
    });
    it('Given "Gremio-RS", When normalized, Then returns "Grêmio"', () => {
      expect(normalizeTeamName('Gremio-RS')).toBe('Grêmio');
    });
  });

  describe('Scenario: Team matching', () => {
    it('Given "Palmeiras-SP" and "Palmeiras", When matched, Then returns true', () => {
      expect(teamsMatch('Palmeiras-SP', 'Palmeiras')).toBe(true);
    });
    it('Given "Flamengo" and "Fluminense", When matched, Then returns false', () => {
      expect(teamsMatch('Flamengo', 'Fluminense')).toBe(false);
    });
  });

  describe('Scenario: Query matching', () => {
    it('Given "Flamengo-RJ" and query "Flamengo", When matched, Then returns true', () => {
      expect(teamMatchesQuery('Flamengo-RJ', 'Flamengo')).toBe(true);
    });
  });
});
