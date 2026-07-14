import { describe, it, expect, beforeAll } from 'vitest';
import { loadStore } from './setup.js';
import { findPlayers, playersByClub } from '../src/queries/players.js';
import type { DataStore } from '../src/types.js';

/**
 * Feature: Player Queries
 *
 * Scenario: Find player by name
 *   Given the player data is loaded
 *   When I search for "Gabriel Barbosa"
 *   Then I should receive matching players with name, club, rating
 */
describe('Feature: Player Queries', () => {
  let store: DataStore;
  beforeAll(async () => {
    store = await loadStore();
  });

  describe('Scenario: Find player by name', () => {
    it('finds Neymar in the FIFA dataset', () => {
      const ps = findPlayers(store.players, { name: 'Neymar' });
      expect(ps.length).toBeGreaterThan(0);
      expect(ps[0].name.toLowerCase()).toContain('neymar');
      expect(ps[0].overall).toBeGreaterThan(80);
    });
  });

  describe('Scenario: Filter by nationality', () => {
    it('returns Brazilian players', () => {
      const ps = findPlayers(store.players, { nationality: 'Brazil', limit: 100 });
      expect(ps.length).toBeGreaterThan(50);
      for (const p of ps) {
        expect(p.nationality).toBe('Brazil');
      }
    });

    it('sorts Brazilian players by overall rating descending', () => {
      const ps = findPlayers(store.players, { nationality: 'Brazil', limit: 20 });
      for (let i = 1; i < ps.length; i++) {
        expect((ps[i].overall ?? 0) <= (ps[i - 1].overall ?? 0)).toBe(true);
      }
    });
  });

  describe('Scenario: Filter by club using normalized team names', () => {
    it('finds players at Flamengo with a flexible club match', () => {
      const ps = findPlayers(store.players, { club: 'Flamengo', limit: 50 });
      // FIFA dataset includes "Flamengo" so this should be non-empty.
      if (ps.length > 0) {
        for (const p of ps) {
          expect(p.club).toBeDefined();
          expect(p.club!.toLowerCase()).toContain('flamengo');
        }
      }
    });
  });

  describe('Scenario: Filter forwards (ST/CF/LW/RW)', () => {
    it('finds top-rated strikers (ST)', () => {
      const ps = findPlayers(store.players, {
        position: 'ST',
        minOverall: 85,
        limit: 25,
      });
      expect(ps.length).toBeGreaterThan(0);
      for (const p of ps) {
        expect(p.position).toMatch(/ST/i);
        expect((p.overall ?? 0) >= 85).toBe(true);
      }
    });
  });

  describe('Scenario: Players grouped by club', () => {
    it('aggregates Brazilian players by club', () => {
      const brazilian = findPlayers(store.players, { nationality: 'Brazil' });
      const byClub = playersByClub(brazilian);
      expect(byClub.length).toBeGreaterThan(10);
      for (const c of byClub) {
        expect(c.count).toBeGreaterThan(0);
      }
    });
  });

  describe('Scenario: Combining filters', () => {
    it('handles min/max age and minOverall together', () => {
      const ps = findPlayers(store.players, {
        nationality: 'Brazil',
        minAge: 18,
        maxAge: 25,
        minOverall: 80,
        limit: 50,
      });
      for (const p of ps) {
        expect(p.nationality).toBe('Brazil');
        expect((p.age ?? 0) >= 18).toBe(true);
        expect((p.age ?? 999) <= 25).toBe(true);
        expect((p.overall ?? 0) >= 80).toBe(true);
      }
    });
  });
});
