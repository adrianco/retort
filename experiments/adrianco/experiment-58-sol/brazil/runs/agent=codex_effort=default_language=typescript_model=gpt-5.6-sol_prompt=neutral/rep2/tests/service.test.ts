import { beforeAll, describe, expect, it } from "vitest";

import { buildService } from "../src/index.js";
import { NaturalLanguageQueryRouter } from "../src/query-router.js";
import type { SoccerService } from "../src/soccer-service.js";

describe("Brazilian soccer knowledge graph", () => {
  let service: SoccerService;
  let router: NaturalLanguageQueryRouter;

  beforeAll(() => {
    service = buildService();
    router = new NaturalLanguageQueryRouter(service);
  });

  it("loads and indexes every required CSV source", () => {
    const summary = service.graph.summary();
    expect(summary.players).toBe(18_207);
    expect(summary.matches).toBeGreaterThan(15_000);
    expect(summary.teams).toBeGreaterThan(300);
    expect(summary.competitions).toBeGreaterThanOrEqual(3);
    expect(Object.values(summary.sourceCounts).every((count) => count > 0)).toBe(true);
  });

  it("finds head-to-head matches through name variations", () => {
    const result = service.headToHead("Flamengo-RJ", "Fluminense Football Club", { limit: 5 });
    expect(result.data.record.matches).toBeGreaterThan(20);
    expect(result.data.matches).toHaveLength(5);
    expect(result.data.matches.every((match) =>
      [match.homeTeamKey, match.awayTeamKey].includes("flamengo") &&
      [match.homeTeamKey, match.awayTeamKey].includes("fluminense"),
    )).toBe(true);
  });

  it("calculates venue-specific team records", () => {
    const result = service.teamStatistics("Corinthians", { season: 2022, competition: "Brasileirão", venue: "home" });
    const record = result.data;
    expect(record.matches).toBeGreaterThan(0);
    expect(record.wins + record.draws + record.losses).toBe(record.matches);
    expect(record.goalsFor - record.goalsAgainst).toBe(record.goalDifference);
    expect(record.points).toBe(record.wins * 3 + record.draws);
  });

  it("reconstructs the 2019 Brasileirão champion and table", () => {
    const standings = service.standings(2019, "Serie A").data;
    expect(standings).toHaveLength(20);
    expect(standings[0]).toMatchObject({ team: "Flamengo", points: 90, wins: 28 });
    expect(standings.every((entry) => entry.matches === 38)).toBe(true);
  });

  it("searches players and FIFA attributes", () => {
    const result = service.searchPlayers({ name: "Neymar", nationality: "Brazilian" });
    expect(result.data[0]).toMatchObject({ name: "Neymar Jr", nationality: "Brazil", overall: 92, position: "LW" });
    expect(result.data[0]?.attributes.Dribbling).toBeGreaterThan(90);
  });

  it("calculates competition statistics and biggest wins", () => {
    const stats = service.competitionStatistics({ competition: "Copa Libertadores", season: 2019, limit: 5 }).data;
    expect(stats.matches).toBeGreaterThan(100);
    expect(stats.averageGoals).toBeGreaterThan(1);
    expect(stats.homeWins + stats.awayWins + stats.draws).toBe(stats.matches);
    expect(stats.biggestWins).toHaveLength(5);
  });

  it("traverses cross-file team relationships", () => {
    const profile = service.teamProfile("São Paulo FC", 2023).data;
    expect(profile.competitions).toContain("Brasileirão Série A");
    expect(profile.record.matches).toBeGreaterThan(0);
    expect(profile.team).toMatch(/São Paulo|Sao Paulo/);
  });

  it("routes at least twenty representative natural-language questions", () => {
    const questions = [
      "Show me all Flamengo vs Fluminense matches",
      "What matches did Palmeiras play in 2023?",
      "Find all Copa do Brasil finals",
      "What is Corinthians' home record in 2022?",
      "Which team scored the most goals in Serie A 2023?",
      "Compare Palmeiras and Santos head-to-head",
      "Find all Brazilian players in the dataset",
      "Who are the highest-rated players at Flamengo?",
      "Show me all forwards from São Paulo FC",
      "Who won the 2019 Brasileirão?",
      "Show the 2018 Copa Libertadores bracket",
      "Which teams were relegated in 2020?",
      "What's the average goals per match in the Brasileirão?",
      "Which team has the best away record in 2019?",
      "Show me the biggest wins in the dataset",
      "When did Flamengo last play Corinthians?",
      "Who is Gabriel Barbosa?",
      "Show me all derbies in 2023",
      "What competitions has Palmeiras played in?",
      "Compare the 2018 and 2019 seasons",
    ];
    const answers = questions.map((question) => router.answer(question));
    expect(answers).toHaveLength(20);
    expect(answers.every((answer) => answer.kind !== "help" && answer.formatted.length > 20)).toBe(true);
  });

  it("reports unsupported top-scorer questions honestly", () => {
    const answer = router.answer("Who was the top scorer in the 2019 Brasileirão?");
    expect(answer.kind).toBe("unsupported");
    expect(answer.limitations?.[0]).toContain("Player-level scoring events");
  });

  it("meets the specified lookup and aggregation latency budgets after startup", () => {
    const lookupStarted = performance.now();
    service.searchMatches({ team: "Flamengo", season: 2023 });
    expect(performance.now() - lookupStarted).toBeLessThan(2_000);

    const aggregateStarted = performance.now();
    service.standings(2019, "Brasileirão");
    expect(performance.now() - aggregateStarted).toBeLessThan(5_000);
  });
});
