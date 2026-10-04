import { describe, it, beforeAll, afterAll } from "vitest";
import { SoccerDsl, startDsl } from "./dsl/soccerDsl";

let soccer: SoccerDsl;
beforeAll(async () => { soccer = await startDsl(); }, 60000);
afterAll(async () => { await soccer.stop(); });

describe("Player queries", () => {
  it("should find a player by name", async () => {
    await soccer.players.search({ name: "Neymar" });
    await soccer.players.confirmFound("Neymar Jr");
  });

  it("should list top Brazilian players by rating", async () => {
    await soccer.players.search({ nationality: "Brazil" });
    await soccer.players.confirmFirstIs("Neymar Jr");
    await soccer.players.confirmAllOfNationality("Brazil");
  });

  it("should find players at a club filtered by position", async () => {
    await soccer.players.search({ club: "Juventus", position: "ST" });
    await soccer.players.confirmFound("Cristiano Ronaldo");
  });

  it("should summarise Brazilian players by club", async () => {
    await soccer.players.requestNationalityByClub({ nationality: "Brazil" });
    await soccer.players.confirmClubListed("Paris Saint-Germain");
  });
});
