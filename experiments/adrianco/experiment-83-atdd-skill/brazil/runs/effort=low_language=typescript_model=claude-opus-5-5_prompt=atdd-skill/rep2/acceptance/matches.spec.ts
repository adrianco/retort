import { describe, it, beforeAll, afterAll } from "vitest";
import { SoccerDsl, startDsl } from "./dsl/soccerDsl";

let soccer: SoccerDsl;
beforeAll(async () => { soccer = await startDsl(); }, 60000);
afterAll(async () => { await soccer.stop(); });

describe("Match queries", () => {
  it("should find matches between two rivals regardless of how team names are written", async () => {
    await soccer.matches.findBetween({ team: "Flamengo", opponent: "Fluminense" });
    await soccer.matches.confirmIncludes({ home: "Flamengo", away: "Fluminense" });
    await soccer.matches.confirmHeadToHeadSummaryShown();
  });

  it("should find a team's matches in a given season", async () => {
    await soccer.matches.findForTeam({ team: "Palmeiras", season: 2019 });
    await soccer.matches.confirmAllInSeason(2019);
  });

  it("should find Copa do Brasil finals", async () => {
    await soccer.matches.findForCompetition({ competition: "Copa do Brasil", stage: "final" });
    await soccer.matches.confirmAllFromCompetition("Copa do Brasil");
  });

  it("should find Libertadores matches", async () => {
    await soccer.matches.findForCompetition({ competition: "Libertadores", season: 2018 });
    await soccer.matches.confirmAllFromCompetition("Libertadores");
  });

  it("should find matches within a date range", async () => {
    await soccer.matches.findForTeam({ team: "Corinthians", from: "2010-01-01", to: "2010-12-31" });
    await soccer.matches.confirmAllBetweenDates("2010-01-01", "2010-12-31");
  });

  it("should report the most recent meeting of two teams", async () => {
    await soccer.matches.findLastMeeting({ team: "Flamengo", opponent: "Corinthians" });
    await soccer.matches.confirmScoreShown();
  });

  it("should include matches from the historical and extended statistics datasets", async () => {
    await soccer.matches.findForTeam({ team: "Guarani", season: 2003 });
    await soccer.matches.confirmIncludes({ home: "Guarani", away: "Vasco" });
    await soccer.matches.findForCompetition({ competition: "Serie B" });
    await soccer.matches.confirmAllFromCompetition("Serie B");
  });
});
