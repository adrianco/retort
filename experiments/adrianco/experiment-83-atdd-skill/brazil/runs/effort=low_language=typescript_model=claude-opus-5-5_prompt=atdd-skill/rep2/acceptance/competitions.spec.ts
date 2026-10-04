import { describe, it, beforeAll, afterAll } from "vitest";
import { SoccerDsl, startDsl } from "./dsl/soccerDsl";

let soccer: SoccerDsl;
beforeAll(async () => { soccer = await startDsl(); }, 60000);
afterAll(async () => { await soccer.stop(); });

describe("Competition queries", () => {
  it("should name Flamengo champion of the 2019 Brasileirão", async () => {
    await soccer.competitions.requestStandings({ season: 2019 });
    await soccer.competitions.confirmChampion({ team: "Flamengo", points: 90 });
  });

  it("should identify the relegated teams of a season", async () => {
    await soccer.competitions.requestStandings({ season: 2019 });
    await soccer.competitions.confirmRelegated(["Chapecoense", "Avaí", "CSA", "Cruzeiro"]);
  });

  it("should show the Libertadores knockout bracket for a season", async () => {
    await soccer.competitions.requestBracket({ season: 2018 });
    await soccer.competitions.confirmBracketHasStage("final");
  });
});

describe("Statistical analysis", () => {
  it("should report average goals per match and home win rate", async () => {
    await soccer.stats.requestOverview({ competition: "Brasileirão" });
    await soccer.stats.confirmAverageGoalsBetween(2, 3);
  });

  it("should list the biggest wins", async () => {
    await soccer.stats.requestBiggestWins({ limit: 5 });
    await soccer.stats.confirmWinsListed(5);
  });

  it("should rank teams by home record", async () => {
    await soccer.stats.requestBestRecord({ venue: "away" });
    await soccer.stats.confirmRankingShown();
  });

  it("should compare two seasons", async () => {
    await soccer.stats.compareSeasons({ first: 2018, second: 2019 });
    await soccer.stats.confirmSeasonsCompared(2018, 2019);
  });
});

describe("Cross-dataset queries", () => {
  it("should combine a club's players with its match record", async () => {
    await soccer.teams.requestProfile({ team: "Juventus" });
    await soccer.teams.confirmProfileHasPlayers();
  });
});

describe("Responsiveness", () => {
  it("should answer an aggregate query in under five seconds", async () => {
    await soccer.stats.confirmRespondsWithin(5000);
  });
});
