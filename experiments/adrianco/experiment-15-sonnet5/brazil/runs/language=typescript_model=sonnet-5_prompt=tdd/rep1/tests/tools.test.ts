import { describe, it, expect } from "vitest";
import type { Match, Player } from "../src/types.js";
import {
  searchMatchesTool,
  teamRecordTool,
  compareTeamsTool,
  searchPlayersTool,
  competitionStandingsTool,
  datasetStatisticsTool,
  listTeamCompetitionsTool,
  playerClubContextTool,
} from "../src/tools.js";

function makeMatch(overrides: Partial<Match>): Match {
  return {
    id: "m1",
    source: "Brasileirao_Matches.csv",
    competition: "Brasileirão",
    date: new Date("2023-01-01T00:00:00Z"),
    season: 2023,
    homeTeam: "Flamengo",
    awayTeam: "Fluminense",
    homeGoals: 1,
    awayGoals: 0,
    ...overrides,
  };
}

const matches: Match[] = [
  makeMatch({ id: "1", homeTeam: "Flamengo", awayTeam: "Fluminense", homeGoals: 2, awayGoals: 1, date: new Date("2023-09-03"), round: "22" }),
  makeMatch({ id: "2", homeTeam: "Fluminense", awayTeam: "Flamengo", homeGoals: 1, awayGoals: 0, date: new Date("2023-05-28"), round: "8" }),
  makeMatch({ id: "3", homeTeam: "Palmeiras", awayTeam: "Santos", homeGoals: 3, awayGoals: 0, date: new Date("2023-06-01") }),
  makeMatch({ id: "4", homeTeam: "Flamengo", awayTeam: "Palmeiras", competition: "Copa do Brasil", season: 2022, date: new Date("2022-04-01"), homeGoals: 0, awayGoals: 0 }),
];

const players: Player[] = [
  { id: "1", name: "Neymar Jr", nationality: "Brazil", club: "Paris Saint-Germain", overall: 92, position: "LW" },
  { id: "2", name: "Alisson", nationality: "Brazil", club: "Liverpool", overall: 89, position: "GK" },
];

const data = { matches, players };

describe("searchMatchesTool", () => {
  it("lists matches for a team with a head-to-head summary when an opponent is given", () => {
    const result = searchMatchesTool(data, { team: "Flamengo", opponent: "Fluminense" });
    expect(result).toContain("Found 2 match(es) for Flamengo");
    expect(result).toContain("2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)");
    expect(result).toContain("2023-05-28: Fluminense 1-0 Flamengo (Brasileirão Round 8)");
    expect(result).toContain("Head-to-head vs Fluminense: Flamengo 1 win, Fluminense 1 win, 0 draws");
  });

  it("reports when no matches are found", () => {
    const result = searchMatchesTool(data, { team: "Nonexistent FC" });
    expect(result).toBe("No matches found for Nonexistent FC.");
  });
});

describe("teamRecordTool", () => {
  it("formats a team's record with scope details", () => {
    const result = teamRecordTool(data, { team: "Flamengo", season: 2023 });
    expect(result).toContain("Flamengo record (2023):");
    expect(result).toContain("- Matches: 2");
    expect(result).toContain("- Wins: 1, Draws: 0, Losses: 1");
    expect(result).toContain("- Goals For: 2, Goals Against: 2");
    expect(result).toContain("- Win rate: 50.0%");
  });
});

describe("compareTeamsTool", () => {
  it("shows head-to-head plus each team's overall record", () => {
    const result = compareTeamsTool(data, { teamA: "Flamengo", teamB: "Fluminense" });
    expect(result).toContain("Flamengo vs Fluminense head-to-head:");
    expect(result).toContain("- Flamengo wins: 1");
    expect(result).toContain("- Fluminense wins: 1");
    expect(result).toContain("- Draws: 0");
  });
});

describe("searchPlayersTool", () => {
  it("lists matching players ranked by overall rating", () => {
    const result = searchPlayersTool(data, { nationality: "Brazil" });
    expect(result).toContain("Found 2 player(s)");
    expect(result).toContain("1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain");
    expect(result).toContain("2. Alisson - Overall: 89, Position: GK, Club: Liverpool");
  });

  it("reports when no players are found", () => {
    const result = searchPlayersTool(data, { name: "Nobody" });
    expect(result).toBe("No players found.");
  });
});

describe("competitionStandingsTool", () => {
  it("formats a standings table for a competition and season", () => {
    const result = competitionStandingsTool(data, { competition: "Brasileirão", season: 2023 });
    expect(result).toContain("Brasileirão 2023 Standings:");
    expect(result).toContain("1. Palmeiras - 3 pts (1W, 0D, 0L) GD +3");
    expect(result).toContain("2. Flamengo - 3 pts (1W, 0D, 1L) GD +0");
  });
});

describe("datasetStatisticsTool", () => {
  it("summarizes average goals, win rates and biggest wins", () => {
    const result = datasetStatisticsTool(data, {});
    expect(result).toContain("Matches analyzed: 4");
    expect(result).toContain("Average goals per match:");
    expect(result).toContain("Home win rate:");
    expect(result).toContain("Biggest wins:");
  });
});

describe("listTeamCompetitionsTool", () => {
  it("lists the distinct competitions a team has played in", () => {
    const result = listTeamCompetitionsTool(data, { team: "Flamengo" });
    expect(result).toContain("Brasileirão");
    expect(result).toContain("Copa do Brasil");
  });
});

describe("playerClubContextTool", () => {
  const crossFileMatches: Match[] = [
    makeMatch({ id: "1", homeTeam: "Flamengo", awayTeam: "Vasco", homeGoals: 2, awayGoals: 0 }),
    makeMatch({ id: "2", homeTeam: "Vasco", awayTeam: "Flamengo", homeGoals: 1, awayGoals: 1 }),
  ];
  const crossFilePlayers: Player[] = [
    { id: "1", name: "Gabriel Barbosa", nationality: "Brazil", club: "Flamengo", overall: 80, position: "ST" },
  ];
  const crossFileData = { matches: crossFileMatches, players: crossFilePlayers };

  it("joins player data with that player's club match record", () => {
    const result = playerClubContextTool(crossFileData, { name: "Gabriel Barbosa" });
    expect(result).toContain("Gabriel Barbosa");
    expect(result).toContain("Flamengo");
    expect(result).toContain("- Matches: 2");
    expect(result).toContain("- Wins: 1, Draws: 1, Losses: 0");
  });

  it("reports when no player matches the name", () => {
    const result = playerClubContextTool(crossFileData, { name: "Nobody" });
    expect(result).toBe('No player found matching "Nobody".');
  });
});

describe("source deduplication", () => {
  // Brazilian_Cup_Matches.csv and BR-Football-Dataset.csv can both label a match
  // "Copa do Brasil" for the same season; aggregate tools must use the canonical
  // source only, not double-count both.
  const overlapping = [
    makeMatch({
      id: "canonical",
      source: "Brazilian_Cup_Matches.csv",
      competition: "Copa do Brasil",
      season: 2020,
      homeTeam: "Corinthians",
      awayTeam: "Santos",
      homeGoals: 2,
      awayGoals: 0,
    }),
    makeMatch({
      id: "duplicate",
      source: "BR-Football-Dataset.csv",
      competition: "Copa do Brasil",
      season: 2020,
      homeTeam: "Corinthians",
      awayTeam: "Santos",
      homeGoals: 2,
      awayGoals: 0,
    }),
  ];
  const overlappingData = { matches: overlapping, players: [] };

  it("team_record does not double-count matches duplicated across overlapping sources", () => {
    const result = teamRecordTool(overlappingData, { team: "Corinthians", season: 2020 });
    expect(result).toContain("- Matches: 1");
  });

  it("competition_standings does not double-count matches duplicated across overlapping sources", () => {
    const result = competitionStandingsTool(overlappingData, { competition: "Copa do Brasil", season: 2020 });
    expect(result).toContain("(1W, 0D, 0L)");
  });

  it("dataset_statistics does not double-count matches duplicated across overlapping sources", () => {
    const result = datasetStatisticsTool(overlappingData, {});
    expect(result).toContain("Matches analyzed: 1");
  });

  it("search_matches lists the duplicated real-world match only once", () => {
    const result = searchMatchesTool(overlappingData, { team: "Corinthians" });
    expect(result).toContain("Found 1 match(es) for Corinthians");
  });
});
