import { describe, it, beforeAll, afterAll } from "vitest";
import { SoccerDsl } from "../dsl/SoccerDsl";

// Executable specifications for the Brazilian soccer knowledge service.
// Written in the language of the domain: no MCP, CSV or JSON details here.
describe("Brazilian soccer knowledge", () => {
  const soccer = new SoccerDsl();
  beforeAll(() => soccer.start(), 60_000);
  afterAll(() => soccer.stop());

  describe("Match queries", () => {
    it("should list matches between two rivals with a head-to-head summary", async () => {
      await soccer.askForMatchesBetween({ team: "Flamengo", opponent: "Fluminense" });
      await soccer.confirmMatchesListed({ atLeast: 10 });
      await soccer.confirmAnswerMentions("Head-to-head");
    });

    it("should find a team's matches in a season", async () => {
      await soccer.askForMatchesOf({ team: "Palmeiras", season: 2023 });
      await soccer.confirmMatchesListed({ atLeast: 1 });
    });

    it("should find Copa do Brasil finals", async () => {
      await soccer.askForMatchesIn({ competition: "Copa do Brasil", stage: "final" });
      await soccer.confirmMatchesListed({ atLeast: 1 });
    });

    it("should find Libertadores matches by date range", async () => {
      await soccer.askForMatchesIn({ competition: "Libertadores", from: "2018-01-01", to: "2018-12-31" });
      await soccer.confirmMatchesListed({ atLeast: 10 });
    });

    it("should find the most recent meeting of two teams", async () => {
      await soccer.askForLastMeeting({ team: "Flamengo", opponent: "Corinthians" });
      await soccer.confirmAnswerHasScore();
    });

    it("should treat team name variations as the same team", async () => {
      await soccer.confirmSameAnswerFor("Palmeiras-SP", "Palmeiras");
      await soccer.confirmSameAnswerFor("Sao Paulo", "São Paulo");
    });

    it("should find derbies in a season", async () => {
      await soccer.askForDerbies({ season: 2022 });
      await soccer.confirmMatchesListed({ atLeast: 2 });
    });
  });

  describe("Team queries", () => {
    it("should report a team's home record for a season", async () => {
      await soccer.askForTeamRecord({ team: "Corinthians", season: 2022, venue: "home" });
      await soccer.confirmRecord({ matches: 19 });
    });

    it("should compare two teams head to head", async () => {
      await soccer.askForHeadToHead({ team: "Palmeiras", opponent: "Santos" });
      await soccer.confirmAnswerMentions("Palmeiras", "Santos", "wins", "draws");
    });

    it("should list the competitions a team has played in", async () => {
      await soccer.askForCompetitionsOf({ team: "Palmeiras" });
      await soccer.confirmAnswerMentions("Brasileirão", "Copa do Brasil", "Libertadores");
    });
  });

  describe("Player queries", () => {
    it("should find a player by name", async () => {
      await soccer.askForPlayer({ name: "Neymar" });
      await soccer.confirmAnswerMentions("Neymar Jr", "Paris Saint-Germain");
    });

    it("should rank the top Brazilian players", async () => {
      await soccer.askForPlayers({ nationality: "Brazil" });
      await soccer.confirmTopPlayerIs("Neymar Jr");
    });

    it("should list players at a Brazilian club", async () => {
      await soccer.askForPlayers({ club: "Santos" });
      await soccer.confirmAnswerMentions("Santos");
      await soccer.confirmPlayersListed({ atLeast: 5 });
    });

    it("should filter players by position", async () => {
      await soccer.askForPlayers({ nationality: "Brazil", position: "GK" });
      await soccer.confirmTopPlayerIs("Ederson");
    });
  });

  describe("Competition queries", () => {
    it("should name the Brasileirão champion from calculated standings", async () => {
      await soccer.askForStandings({ season: 2019 });
      await soccer.confirmChampion({ team: "Flamengo", points: 90 });
    });

    it("should identify the relegated teams of a season", async () => {
      await soccer.askForStandings({ season: 2020 });
      await soccer.confirmRelegatedCount(4);
    });

    it("should show the top scoring team of a season", async () => {
      await soccer.askForTopScoringTeam({ season: 2019 });
      await soccer.confirmAnswerMentions("Flamengo");
    });
  });

  describe("Statistical analysis", () => {
    it("should calculate average goals per match", async () => {
      await soccer.askForCompetitionStats({ competition: "Brasileirão" });
      await soccer.confirmAnswerMentions("Average goals per match", "Home win rate");
    });

    it("should list the biggest wins", async () => {
      await soccer.askForBiggestWins({ limit: 5 });
      await soccer.confirmMatchesListed({ atLeast: 5 });
    });

    it("should rank teams by away record", async () => {
      await soccer.askForBestRecord({ venue: "away" });
      await soccer.confirmAnswerMentions("away");
    });

    it("should compare two seasons", async () => {
      await soccer.askToCompareSeasons({ first: 2018, second: 2019 });
      await soccer.confirmAnswerMentions("2018", "2019");
    });
  });

  describe("Data coverage and performance", () => {
    it("should make all six datasets queryable", async () => {
      await soccer.confirmAllDatasetsLoaded(6);
    });

    it("should answer simple lookups within two seconds", async () => {
      await soccer.confirmAnsweredWithin(2000, () => soccer.askForPlayer({ name: "Casemiro" }));
    });

    it("should answer aggregate queries within five seconds", async () => {
      await soccer.confirmAnsweredWithin(5000, () => soccer.askForBestRecord({ venue: "home" }));
    });
  });
});
