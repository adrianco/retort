import { describe, it, beforeAll, afterAll } from "vitest";
import { SoccerDsl, startDsl } from "./dsl/soccerDsl";

let soccer: SoccerDsl;
beforeAll(async () => { soccer = await startDsl(); }, 60000);
afterAll(async () => { await soccer.stop(); });

describe("Team queries", () => {
  it("should give a team's home record for a season", async () => {
    await soccer.teams.requestRecord({ team: "Corinthians", season: 2022, competition: "Brasileirão", venue: "home" });
    await soccer.teams.confirmRecord({ matches: 19 });
  });

  it("should compare two teams head-to-head", async () => {
    await soccer.teams.compareHeadToHead({ team: "Palmeiras", opponent: "Santos" });
    await soccer.teams.confirmHeadToHeadNamesBothTeams("Palmeiras", "Santos");
  });

  it("should list the competitions a team has played in", async () => {
    await soccer.teams.requestCompetitions({ team: "Palmeiras" });
    await soccer.teams.confirmCompetitions(["Brasileirão", "Copa do Brasil", "Libertadores"]);
  });

  it("should treat accented and unaccented team names as the same team", async () => {
    await soccer.teams.requestRecord({ team: "Sao Paulo", season: 2019 });
    await soccer.teams.confirmRecordFor("São Paulo");
  });
});
