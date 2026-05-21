import { describe, it, expect, beforeAll } from "vitest";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { SoccerData, normalizeTeamName, teamMatches } from "./data.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const dataDir = join(__dirname, "..", "data", "kaggle");

let data: SoccerData;

beforeAll(() => {
  data = new SoccerData(dataDir);
  data.load();
});

describe("Team name normalization", () => {
  it("should strip state suffixes", () => {
    expect(normalizeTeamName("Palmeiras-SP")).toBe("Palmeiras");
    expect(normalizeTeamName("Flamengo-RJ")).toBe("Flamengo");
  });

  it("should normalize accented names", () => {
    expect(normalizeTeamName("Sao Paulo")).toBe("São Paulo");
    expect(normalizeTeamName("Gremio")).toBe("Grêmio");
    expect(normalizeTeamName("Avai-SC")).toBe("Avaí");
  });

  it("should normalize Atletico variants", () => {
    expect(normalizeTeamName("Atletico-MG")).toBe("Atlético-MG");
    expect(normalizeTeamName("Atletico-PR")).toBe("Athletico-PR");
  });

  it("should handle clean names unchanged", () => {
    expect(normalizeTeamName("Flamengo")).toBe("Flamengo");
    expect(normalizeTeamName("Palmeiras")).toBe("Palmeiras");
  });
});

describe("Team matching", () => {
  it("should match exact names", () => {
    expect(teamMatches("Flamengo", "Flamengo")).toBe(true);
  });

  it("should match with state suffix", () => {
    expect(teamMatches("Palmeiras-SP", "Palmeiras")).toBe(true);
  });

  it("should match partial names", () => {
    expect(teamMatches("São Paulo", "Paulo")).toBe(true);
  });

  it("should not match unrelated teams", () => {
    expect(teamMatches("Flamengo", "Corinthians")).toBe(false);
  });
});

describe("Feature: Data Loading", () => {
  it("Scenario: All CSV files are loaded", () => {
    // Given the data directory with 6 CSV files
    // When we load the data
    // Then matches and players should be populated
    expect(data.matches.length).toBeGreaterThan(0);
    expect(data.players.length).toBeGreaterThan(0);
  });

  it("Scenario: Match data has expected fields", () => {
    const match = data.matches[0];
    expect(match).toHaveProperty("date");
    expect(match).toHaveProperty("homeTeam");
    expect(match).toHaveProperty("awayTeam");
    expect(match).toHaveProperty("homeGoals");
    expect(match).toHaveProperty("awayGoals");
    expect(match).toHaveProperty("competition");
    expect(match).toHaveProperty("season");
  });

  it("Scenario: Player data has expected fields", () => {
    const player = data.players[0];
    expect(player).toHaveProperty("name");
    expect(player).toHaveProperty("overall");
    expect(player).toHaveProperty("club");
    expect(player).toHaveProperty("nationality");
    expect(player).toHaveProperty("position");
  });

  it("Scenario: Multiple competitions are represented", () => {
    const competitions = new Set(data.matches.map((m) => m.competition));
    expect(competitions.has("Brasileirão Serie A")).toBe(true);
    expect(competitions.has("Copa do Brasil")).toBe(true);
    expect(competitions.has("Copa Libertadores")).toBe(true);
  });
});

describe("Feature: Match Queries", () => {
  it("Scenario: Find matches between two teams", () => {
    // Given the match data is loaded
    // When I search for matches between Flamengo and Fluminense
    const matches = data.searchMatches({ team: "Flamengo" });
    // Then I should receive a list of matches
    expect(matches.length).toBeGreaterThan(0);
    // And each match should have date, scores, and competition
    for (const m of matches) {
      expect(m.date).toBeTruthy();
      expect(typeof m.homeGoals).toBe("number");
      expect(typeof m.awayGoals).toBe("number");
      expect(m.competition).toBeTruthy();
    }
  });

  it("Scenario: Filter matches by competition", () => {
    const matches = data.searchMatches({ competition: "Libertadores" });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.competition.toLowerCase()).toContain("libertadores");
    }
  });

  it("Scenario: Filter matches by season", () => {
    const matches = data.searchMatches({ season: 2019 });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.season).toBe(2019);
    }
  });

  it("Scenario: Filter by date range", () => {
    const matches = data.searchMatches({ dateFrom: "2019-01-01", dateTo: "2019-12-31" });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.date >= "2019-01-01").toBe(true);
      expect(m.date <= "2019-12-31").toBe(true);
    }
  });

  it("Scenario: Limit results", () => {
    const matches = data.searchMatches({ limit: 5 });
    expect(matches.length).toBeLessThanOrEqual(5);
  });
});

describe("Feature: Head-to-Head", () => {
  it("Scenario: Compare two rival teams", () => {
    // Given the match data is loaded
    // When I compare Flamengo and Fluminense
    const h2h = data.headToHead("Flamengo", "Fluminense");
    // Then I should receive match history and aggregated stats
    expect(h2h.matches.length).toBeGreaterThan(0);
    expect(h2h.team1Wins + h2h.team2Wins + h2h.draws).toBeGreaterThanOrEqual(h2h.matches.length);
    expect(h2h.team1Goals).toBeGreaterThanOrEqual(0);
    expect(h2h.team2Goals).toBeGreaterThanOrEqual(0);
  });

  it("Scenario: Head-to-head with no matches returns zeros", () => {
    const h2h = data.headToHead("NonexistentTeam1", "NonexistentTeam2");
    expect(h2h.matches.length).toBe(0);
    expect(h2h.team1Wins).toBe(0);
    expect(h2h.draws).toBe(0);
  });
});

describe("Feature: Team Statistics", () => {
  it("Scenario: Get team statistics", () => {
    // Given the match data is loaded
    // When I request statistics for Palmeiras
    const stats = data.teamStats("Palmeiras");
    // Then I should receive wins, losses, draws, and goals
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
    expect(stats.goalsFor).toBeGreaterThan(0);
    expect(stats.points).toBe(stats.wins * 3 + stats.draws);
  });

  it("Scenario: Get team statistics for a specific season", () => {
    const stats = data.teamStats("Palmeiras", { season: 2019 });
    expect(stats.matches).toBeGreaterThan(0);
  });

  it("Scenario: Get home-only statistics", () => {
    const home = data.teamStats("Corinthians", { homeOnly: true });
    const away = data.teamStats("Corinthians", { awayOnly: true });
    const total = data.teamStats("Corinthians");
    expect(home.matches + away.matches).toBe(total.matches);
  });

  it("Scenario: Get stats filtered by competition", () => {
    const stats = data.teamStats("Flamengo", { competition: "Brasileirão" });
    expect(stats.matches).toBeGreaterThan(0);
  });
});

describe("Feature: Player Queries", () => {
  it("Scenario: Search player by name", () => {
    const players = data.searchPlayers({ name: "Neymar" });
    expect(players.length).toBeGreaterThan(0);
    expect(players[0].name.toLowerCase()).toContain("neymar");
  });

  it("Scenario: Find all Brazilian players", () => {
    const players = data.searchPlayers({ nationality: "Brazil", limit: 10 });
    expect(players.length).toBeGreaterThan(0);
    for (const p of players) {
      expect(p.nationality.toLowerCase()).toContain("brazil");
    }
  });

  it("Scenario: Find players by club", () => {
    const players = data.searchPlayers({ club: "Grêmio" });
    expect(players.length).toBeGreaterThan(0);
    for (const p of players) {
      expect(p.club.toLowerCase()).toContain("grêmio");
    }
  });

  it("Scenario: Find players by position", () => {
    const players = data.searchPlayers({ position: "ST", limit: 10 });
    expect(players.length).toBeGreaterThan(0);
    for (const p of players) {
      expect(p.position.toLowerCase()).toContain("st");
    }
  });

  it("Scenario: Find players by minimum rating", () => {
    const players = data.searchPlayers({ minOverall: 85, limit: 10 });
    expect(players.length).toBeGreaterThan(0);
    for (const p of players) {
      expect(p.overall).toBeGreaterThanOrEqual(85);
    }
  });

  it("Scenario: Players sorted by overall rating descending", () => {
    const players = data.searchPlayers({ nationality: "Brazil", limit: 10 });
    for (let i = 1; i < players.length; i++) {
      expect(players[i].overall).toBeLessThanOrEqual(players[i - 1].overall);
    }
  });
});

describe("Feature: Competition Standings", () => {
  it("Scenario: Calculate Brasileirão standings", () => {
    // Given the match data is loaded
    // When I calculate standings for 2019
    const standings = data.competitionStandings(2019);
    // Then I should receive ordered standings with points
    expect(standings.length).toBeGreaterThan(0);
    // Standings should be sorted by points descending
    for (let i = 1; i < standings.length; i++) {
      expect(standings[i].points).toBeLessThanOrEqual(standings[i - 1].points);
    }
  });

  it("Scenario: Standings include correct fields", () => {
    const standings = data.competitionStandings(2019);
    const team = standings[0];
    expect(team).toHaveProperty("team");
    expect(team).toHaveProperty("matches");
    expect(team).toHaveProperty("wins");
    expect(team).toHaveProperty("draws");
    expect(team).toHaveProperty("losses");
    expect(team).toHaveProperty("goalsFor");
    expect(team).toHaveProperty("goalsAgainst");
    expect(team).toHaveProperty("goalDifference");
    expect(team).toHaveProperty("points");
    expect(team.points).toBe(team.wins * 3 + team.draws);
    expect(team.goalDifference).toBe(team.goalsFor - team.goalsAgainst);
  });

  it("Scenario: Flamengo won the 2019 Brasileirão", () => {
    const standings = data.competitionStandings(2019);
    const topTeam = standings[0].team;
    expect(topTeam.toLowerCase()).toContain("flamengo");
  });
});

describe("Feature: Statistical Analysis", () => {
  it("Scenario: Calculate average goals per match", () => {
    const stats = data.averageGoals();
    expect(stats.totalMatches).toBeGreaterThan(0);
    expect(stats.totalGoals).toBeGreaterThan(0);
    expect(stats.avgGoalsPerMatch).toBeGreaterThan(0);
    expect(stats.homeWinRate + stats.awayWinRate + stats.drawRate).toBeCloseTo(100, 0);
  });

  it("Scenario: Calculate stats for specific competition", () => {
    const stats = data.averageGoals({ competition: "Brasileirão" });
    expect(stats.totalMatches).toBeGreaterThan(0);
  });

  it("Scenario: Find biggest wins", () => {
    const wins = data.biggestWins({ limit: 10 });
    expect(wins.length).toBe(10);
    // Should be sorted by goal difference descending
    for (let i = 1; i < wins.length; i++) {
      expect(Math.abs(wins[i].homeGoals - wins[i].awayGoals)).toBeLessThanOrEqual(
        Math.abs(wins[i - 1].homeGoals - wins[i - 1].awayGoals)
      );
    }
  });

  it("Scenario: Average goals in Brasileirão is reasonable", () => {
    const stats = data.averageGoals({ competition: "Brasileirão" });
    expect(stats.avgGoalsPerMatch).toBeGreaterThan(1);
    expect(stats.avgGoalsPerMatch).toBeLessThan(5);
  });
});

describe("Feature: Cross-file queries", () => {
  it("Scenario: Players at a club that also has match data", () => {
    const players = data.searchPlayers({ club: "Grêmio" });
    expect(players.length).toBeGreaterThan(0);

    const matches = data.searchMatches({ team: "Grêmio", limit: 5 });
    expect(matches.length).toBeGreaterThan(0);
  });

  it("Scenario: Team from multiple competitions", () => {
    const brasileirao = data.searchMatches({ team: "Flamengo", competition: "Brasileirão" });
    const copa = data.searchMatches({ team: "Flamengo", competition: "Copa do Brasil" });
    expect(brasileirao.length).toBeGreaterThan(0);
    expect(copa.length).toBeGreaterThan(0);
  });
});
