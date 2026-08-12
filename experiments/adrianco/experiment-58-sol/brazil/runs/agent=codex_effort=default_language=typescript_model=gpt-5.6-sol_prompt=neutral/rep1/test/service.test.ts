import assert from "node:assert/strict";
import { before, describe, it } from "node:test";
import { performance } from "node:perf_hooks";
import { join } from "node:path";
import { loadSoccerData, type SoccerData } from "../src/data-loader.js";
import { SoccerService } from "../src/soccer-service.js";

let data: SoccerData;
let service: SoccerService;

before(() => {
  data = loadSoccerData(join(process.cwd(), "data", "kaggle"));
  service = new SoccerService(data);
});

describe("Dataset loading", () => {
  it("Given the supplied data directory, when loaded, then every one of the six CSV files is queryable", () => {
    assert.equal(data.summary.rawMatchRows, 23_954);
    assert.equal(data.summary.players, 18_207);
    assert.equal(Object.keys(data.summary.sourceRows).length, 6);
    for (const count of Object.values(data.summary.sourceRows)) assert.ok(count > 1_000);
    assert.ok(data.summary.uniqueMatches > 15_000);
  });

  it("Given overlapping match files, when normalized, then source provenance is retained on merged matches", () => {
    const merged = data.matches.find((match) => match.sources.length > 1);
    assert.ok(merged, "expected at least one cross-source duplicate to merge");
  });

  it("Given cross-source fixtures, when deduplicated, then no normalized pairing repeats within one day", () => {
    const byPair = new Map<string, typeof data.matches>();
    for (const match of data.matches) {
      const key = `${match.season}|${match.homeTeamKey}|${match.awayTeamKey}`;
      const fixtures = byPair.get(key) ?? [];
      fixtures.push(match);
      byPair.set(key, fixtures);
    }
    for (const fixtures of byPair.values()) {
      fixtures.sort((left, right) => left.date.localeCompare(right.date));
      for (let index = 1; index < fixtures.length; index++) {
        const previous = fixtures[index - 1]!;
        const current = fixtures[index]!;
        const days = (Date.parse(`${current.date}T00:00:00Z`) - Date.parse(`${previous.date}T00:00:00Z`)) / 86_400_000;
        assert.ok(days > 1, `duplicate fixture remained: ${previous.homeTeam} vs ${previous.awayTeam} on ${previous.date}/${current.date}`);
      }
    }
  });
});

describe("Match and team behavior", () => {
  it("Given venue, season, competition, and date filters, when matches are searched, then home, away, and either-team modes are exact", () => {
    const common = { season: 2019, competition: "Brasileirão", dateFrom: "2019-01-01", dateTo: "2019-12-31", limit: 500 } as const;
    const home = service.searchMatches({ ...common, homeTeam: "Flamengo-RJ" });
    const away = service.searchMatches({ ...common, awayTeam: "Flamengo" });
    const either = service.searchMatches({ ...common, team: "Flamengo" });
    assert.equal(home.total, 19);
    assert.equal(away.total, 19);
    assert.equal(either.total, 38);
    assert.ok(home.matches.every((match) => match.homeTeamKey === "flamengo" && match.competition === "Brasileirão Série A"));
    assert.ok(away.matches.every((match) => match.awayTeamKey === "flamengo" && match.date.startsWith("2019-")));
  });

  it("Given Flamengo and Fluminense aliases, when comparing them, then each result has a date, score, and competition", () => {
    const result = service.compareTeams("Flamengo-RJ", "Fluminense");
    assert.ok(result.matches.length > 10);
    assert.equal(result.team1.matches, result.matches.length);
    for (const match of result.matches) {
      assert.match(match.date, /^\d{4}-\d{2}-\d{2}$/);
      assert.equal(typeof match.homeGoals, "number");
      assert.ok(match.competition);
    }
  });

  it("Given accent and state-suffix variants, when searched, then they resolve to the same team", () => {
    const accented = service.searchMatches({ team: "São Paulo", season: 2019, limit: 500 });
    const plain = service.searchMatches({ team: "Sao Paulo-SP", season: 2019, limit: 500 });
    assert.ok(accented.total > 0);
    assert.equal(plain.total, accented.total);
  });

  it("Given Corinthians' 2022 home matches, when statistics are requested, then wins, draws, losses, and goals reconcile", () => {
    const record = service.getTeamStatistics("Corinthians", { season: 2022, competition: "Brasileirão", venue: "home" });
    assert.equal(record.matches, record.wins + record.draws + record.losses);
    assert.equal(record.matches, 19);
    assert.ok(record.goalsFor > 0);
    assert.equal(record.goalDifference, record.goalsFor - record.goalsAgainst);
  });

  it("Given Flamengo's 2019 league matches, when team statistics are requested, then the official totals are returned once", () => {
    const record = service.getTeamStatistics("Flamengo", { season: 2019, competition: "Brasileirão Série A" });
    assert.deepEqual(record, {
      team: "Flamengo",
      matches: 38,
      wins: 28,
      draws: 6,
      losses: 4,
      goalsFor: 86,
      goalsAgainst: 37,
      goalDifference: 49,
      points: 90,
      winRate: 73.7,
    });
  });

  it("Given the 2019 Brasileirão, when standings are calculated, then Flamengo is champion", () => {
    const standings = service.getStandings(2019, "Brasileirão Série A");
    assert.equal(standings.length, 20);
    assert.deepEqual(standings[0], {
      team: "Flamengo",
      matches: 38,
      wins: 28,
      draws: 6,
      losses: 4,
      goalsFor: 86,
      goalsAgainst: 37,
      goalDifference: 49,
      points: 90,
      winRate: 73.7,
      position: 1,
    });
    assert.equal(standings.filter(({ team }) => team.includes("Atlético") || team.includes("Athletico")).length, 2);
  });

  it("Given competition filters, when aggregating, then goals and result categories reconcile", () => {
    const stats = service.getCompetitionStatistics("Copa Libertadores", 2018);
    assert.ok(stats.matches > 100);
    assert.equal(stats.matches, stats.homeWins + stats.awayWins + stats.draws);
    assert.equal(stats.averageGoals, Math.round((stats.goals / stats.matches) * 100) / 100);
    assert.ok(stats.biggestWins.length > 0);
  });
});

describe("Player and graph behavior", () => {
  it("Given Brazilian players, when filtered and sorted, then all results are Brazilian and ratings descend", () => {
    const players = service.searchPlayers({ nationality: "Brazil", limit: 100 });
    assert.equal(players.length, 100);
    assert.ok(players.every((player) => player.nationality === "Brazil"));
    for (let index = 1; index < players.length; index++) assert.ok((players[index - 1]?.overall ?? 0) >= (players[index]?.overall ?? 0));
  });

  it("Given a player name, when searched, then FIFA attributes are returned", () => {
    const [neymar] = service.searchPlayers({ name: "Neymar", limit: 1 });
    assert.ok(neymar);
    assert.ok((neymar.overall ?? 0) > 80);
    assert.ok(Object.keys(neymar.attributes).length > 20);
  });

  it("Given nationality, club, position, and rating filters, when combined, then every returned player satisfies them", () => {
    const players = service.searchPlayers({ nationality: "Brazil", club: "Santos", position: "forward", minOverall: 60, limit: 100 });
    assert.ok(players.length > 0);
    assert.ok(players.every((player) => player.nationality === "Brazil"));
    assert.ok(players.every((player) => player.clubKey?.startsWith("santos")));
    assert.ok(players.every((player) => (player.overall ?? 0) >= 60));
    assert.ok(players.every((player) => ["ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"].includes(player.position ?? "")));
  });

  it("Given a team-centered graph query, when explored, then team, match, competition, and relationship data are connected", () => {
    const graph = service.exploreGraph({ team: "Santos", season: 2019, limit: 10 });
    assert.ok(graph.nodes.some((node) => node.type === "team" && node.label.includes("Santos")));
    assert.ok(graph.nodes.some((node) => node.type === "match"));
    assert.ok(graph.nodes.some((node) => node.type === "competition"));
    assert.ok(graph.nodes.some((node) => node.type === "player"));
    assert.ok(graph.edges.some((edge) => edge.type === "HOME_TEAM" || edge.type === "AWAY_TEAM"));
    assert.ok(graph.edges.some((edge) => edge.type === "PLAYED_IN"));
    assert.ok(graph.edges.some((edge) => edge.type === "PLAYS_FOR"));
  });
});

describe("Natural-language and performance behavior", () => {
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
    "Which team has the best away record in 2023?",
    "Show me the biggest wins in the dataset",
    "When did Flamengo last play Corinthians?",
    "Who is Neymar Jr?",
    "Which players play for Flamengo?",
    "Show me all derbies in 2023",
    "What competitions has Palmeiras played in?",
  ];

  for (const question of questions) {
    it(`answers: ${question}`, () => {
      const result = service.answerQuestion(question);
      assert.notEqual(result.intent, "help");
      assert.ok(result.answer.length > 10);
    });
  }

  it("Given an unsupported scorer request, when answered, then the service does not fabricate unavailable data", () => {
    const result = service.answerQuestion("Who was the top scorer in the 2019 Brasileirão?");
    assert.equal(result.intent, "unsupported_top_scorers");
    assert.match(result.answer, /no goal-scorer events/i);
  });

  it("Given loaded data, when simple and aggregate queries run, then both satisfy the required latency budgets", () => {
    const simpleStart = performance.now();
    service.searchMatches({ team: "Flamengo", season: 2023 });
    assert.ok(performance.now() - simpleStart < 2_000);
    const aggregateStart = performance.now();
    service.getStandings(2019);
    assert.ok(performance.now() - aggregateStart < 5_000);
  });
});
