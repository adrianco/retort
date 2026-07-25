/**
 * Feature: Match queries
 *
 * Find matches by team, opponent, date range, competition and season,
 * and compute head-to-head records.
 */
import { describe, expect, it } from "vitest";
import { filterMatches, headToHead } from "../src/queries.js";
import { dataset } from "./helpers.js";

describe("Feature: Match queries", () => {
  describe("Scenario: Find matches between two teams", () => {
    it("Given the match data is loaded, When I search for matches between 'Flamengo' and 'Fluminense', Then I receive a list of matches with date, scores and competition", () => {
      const matches = filterMatches(dataset(), { team: "Flamengo", opponent: "Fluminense" });
      expect(matches.length).toBeGreaterThan(20);
      for (const m of matches) {
        expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
        expect(Number.isInteger(m.homeGoals)).toBe(true);
        expect(Number.isInteger(m.awayGoals)).toBe(true);
        expect(m.competition).toBeTruthy();
      }
    });

    it("Then every returned match involves both teams", () => {
      const matches = filterMatches(dataset(), { team: "Flamengo", opponent: "Fluminense" });
      for (const m of matches) {
        const names = [m.home.base, m.away.base].join("|");
        expect(names).toContain("flamengo");
        expect(names).toContain("fluminense");
      }
    });
  });

  describe("Scenario: Find matches for a team in a season", () => {
    it("Given the match data, When I search Palmeiras matches in 2023, Then all results are from 2023 and involve Palmeiras", () => {
      const matches = filterMatches(dataset(), { team: "Palmeiras", season: 2023 });
      expect(matches.length).toBeGreaterThan(30);
      for (const m of matches) {
        expect(m.season).toBe(2023);
        expect([m.home.base, m.away.base]).toContain("palmeiras");
      }
    });
  });

  describe("Scenario: Filter by competition", () => {
    it("Given a competition filter 'Libertadores', When I search, Then only Copa Libertadores matches return", () => {
      const matches = filterMatches(dataset(), { team: "Santos", competition: "Libertadores" });
      expect(matches.length).toBeGreaterThan(5);
      for (const m of matches) expect(m.competition).toBe("Copa Libertadores");
    });

    it("Given 'Copa do Brasil', When I search finals-stage rounds, Then cup matches return", () => {
      const matches = filterMatches(dataset(), { competition: "Copa do Brasil" });
      expect(matches.length).toBeGreaterThan(1000);
      for (const m of matches.slice(0, 50)) expect(m.competition).toBe("Copa do Brasil");
    });
  });

  describe("Scenario: Filter by date range", () => {
    it("Given a date range, When I search, Then all matches fall inside it", () => {
      const matches = filterMatches(dataset(), {
        team: "Corinthians",
        dateFrom: "2015-01-01",
        dateTo: "2015-12-31",
      });
      expect(matches.length).toBeGreaterThan(20);
      for (const m of matches) {
        expect(m.date! >= "2015-01-01" && m.date! <= "2015-12-31").toBe(true);
      }
    });
  });

  describe("Scenario: Most recent meeting lookup", () => {
    it("Given Flamengo and Corinthians, When I ask for their last meeting, Then the latest match by date is identifiable with a score", () => {
      const matches = filterMatches(dataset(), { team: "Flamengo", opponent: "Corinthians" });
      expect(matches.length).toBeGreaterThan(10);
      const last = matches[matches.length - 1];
      // Matches are sorted chronologically, so the last one is the most recent.
      for (const m of matches) expect(m.date! <= last.date!).toBe(true);
      expect(last.homeGoals).toBeGreaterThanOrEqual(0);
      expect(last.awayGoals).toBeGreaterThanOrEqual(0);
    });
  });

  describe("Scenario: Head-to-head record", () => {
    it("Given two rivals, When I compute head-to-head, Then wins + draws add up to total matches", () => {
      const h2h = headToHead(dataset(), "Palmeiras", "Santos");
      expect(h2h.matches.length).toBeGreaterThan(20);
      expect(h2h.team1Wins + h2h.team2Wins + h2h.draws).toBe(h2h.matches.length);
      expect(h2h.team1Goals).toBeGreaterThan(0);
      expect(h2h.team2Goals).toBeGreaterThan(0);
    });

    it("Given the team name with state suffix, When I query 'Flamengo-RJ' vs 'Fluminense', Then the result matches the suffix-free query", () => {
      const a = headToHead(dataset(), "Flamengo", "Fluminense");
      const b = headToHead(dataset(), "Flamengo-RJ", "Fluminense");
      expect(b.matches.length).toBe(a.matches.length);
      expect(b.team1Wins).toBe(a.team1Wins);
    });
  });
});
