import { describe, it, expect } from "vitest";
import {
  formatMatch,
  formatMatchList,
  formatHeadToHead,
  formatTeamRecord,
  formatStandings,
  formatStatistics,
  formatPlayer,
  formatPlayerList,
} from "../src/format.js";
import type { Match, Player, TeamRecord } from "../src/types.js";
import { normalizeTeamName, normalizeName, parseDate } from "../src/normalize.js";

const match: Match = {
  competition: "Brasileirão Série A",
  date: parseDate("2023-09-03"),
  season: 2023,
  round: "22",
  homeTeam: "Flamengo-RJ",
  awayTeam: "Fluminense-RJ",
  homeKey: "flamengo",
  awayKey: "fluminense",
  homeGoals: 2,
  awayGoals: 1,
  source: "test",
};

describe("formatMatch", () => {
  it("renders date, score and competition context", () => {
    expect(formatMatch(match)).toBe(
      "2023-09-03: Flamengo-RJ 2-1 Fluminense-RJ (Brasileirão Série A Round 22)"
    );
  });

  it("includes stage when present and omits round", () => {
    const liber: Match = {
      ...match,
      competition: "Copa Libertadores",
      round: undefined,
      stage: "final",
    };
    expect(formatMatch(liber)).toBe(
      "2023-09-03: Flamengo-RJ 2-1 Fluminense-RJ (Copa Libertadores, final)"
    );
  });
});

describe("formatMatchList", () => {
  it("renders a header and bullet list", () => {
    const out = formatMatchList([match], "Flamengo vs Fluminense");
    expect(out).toContain("Flamengo vs Fluminense");
    expect(out).toContain("- 2023-09-03:");
  });

  it("reports when no matches are found", () => {
    expect(formatMatchList([], "Nothing")).toContain("No matches found");
  });
});

describe("formatHeadToHead", () => {
  it("summarises wins and draws", () => {
    const out = formatHeadToHead({
      teamA: "Flamengo",
      teamB: "Fluminense",
      matches: 3,
      teamAWins: 2,
      teamBWins: 0,
      draws: 1,
      games: [],
    });
    expect(out).toContain("Flamengo 2 wins");
    expect(out).toContain("Fluminense 0 wins");
    expect(out).toContain("1 draw");
  });
});

describe("formatTeamRecord", () => {
  it("renders win/draw/loss, goals and win rate", () => {
    const rec: TeamRecord = {
      team: "Corinthians",
      matches: 19,
      wins: 11,
      draws: 5,
      losses: 3,
      goalsFor: 28,
      goalsAgainst: 15,
      points: 38,
    };
    const out = formatTeamRecord(rec, "Corinthians record");
    expect(out).toContain("Matches: 19");
    expect(out).toContain("Wins: 11, Draws: 5, Losses: 3");
    expect(out).toContain("Goals For: 28, Goals Against: 15");
    expect(out).toContain("57.9%");
  });
});

describe("formatStandings", () => {
  it("renders a numbered points table", () => {
    const table: TeamRecord[] = [
      { team: "Flamengo", matches: 38, wins: 28, draws: 6, losses: 4, goalsFor: 86, goalsAgainst: 37, points: 90 },
      { team: "Santos", matches: 38, wins: 22, draws: 8, losses: 8, goalsFor: 60, goalsAgainst: 40, points: 74 },
    ];
    const out = formatStandings(table, "2019 Brasileirão");
    expect(out).toContain("1. Flamengo - 90 pts");
    expect(out).toContain("2. Santos - 74 pts");
  });
});

describe("formatStatistics", () => {
  it("renders averages and rates", () => {
    const out = formatStatistics(
      {
        totalMatches: 100,
        totalGoals: 247,
        averageGoals: 2.47,
        homeWins: 47,
        awayWins: 30,
        draws: 23,
        homeWinRate: 0.473,
        awayWinRate: 0.3,
        drawRate: 0.227,
      },
      "Brasileirão"
    );
    expect(out).toContain("Average goals per match: 2.47");
    expect(out).toContain("Home win rate: 47.3%");
  });
});

describe("formatPlayer / formatPlayerList", () => {
  const player: Player = {
    id: 1,
    name: "Neymar Jr",
    nameKey: normalizeName("Neymar Jr"),
    age: 31,
    nationality: "Brazil",
    overall: 92,
    potential: 92,
    club: "Paris Saint-Germain",
    clubKey: normalizeTeamName("Paris Saint-Germain"),
    position: "LW",
    jerseyNumber: 10,
    height: "5'9",
    weight: "150lbs",
  };

  it("formats a single player line", () => {
    expect(formatPlayer(player)).toBe(
      "Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain"
    );
  });

  it("numbers a player list under a header", () => {
    const out = formatPlayerList([player], "Top players");
    expect(out).toContain("Top players");
    expect(out).toContain("1. Neymar Jr - Overall: 92");
  });

  it("reports when no players are found", () => {
    expect(formatPlayerList([], "x")).toContain("No players found");
  });
});
