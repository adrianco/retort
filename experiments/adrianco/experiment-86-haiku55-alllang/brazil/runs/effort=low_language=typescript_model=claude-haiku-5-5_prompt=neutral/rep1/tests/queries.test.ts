import { describe, expect, it } from "vitest";
import type { Dataset, Match, Player } from "../src/model.js";
import {
  clubSummary,
  headToHead,
  matchStatistics,
  searchMatches,
  searchPlayers,
  standings,
  teamRecord,
} from "../src/queries.js";

let n = 0;
function m(
  date: string,
  home: string,
  hg: number,
  away: string,
  ag: number,
  competition = "Brasileirão Série A",
  round = "",
): Match {
  n++;
  return {
    id: `t#${n}`,
    date,
    season: Number(date.slice(0, 4)),
    competition,
    round,
    home,
    away,
    homeGoals: hg,
    awayGoals: ag,
    source: "test",
  };
}

function p(name: string, overall: number, nationality: string, club: string, position = "ST"): Player {
  return {
    id: n++,
    name,
    age: 25,
    nationality,
    overall,
    potential: overall,
    club,
    position,
    height: "",
    weight: "",
    preferredFoot: "",
    value: "",
  };
}

const fixture: Dataset = {
  matches: [
    m("2023-03-01", "Flamengo-RJ", 2, "Fluminense-RJ", 1),
    m("2023-05-28", "Fluminense-RJ", 1, "Flamengo-RJ", 0),
    m("2023-06-10", "Palmeiras-SP", 3, "Santos-SP", 0),
    m("2023-07-01", "Santos - SP", 1, "Palmeiras-SP", 1),
    m("2023-08-01", "Palmeiras-SP", 0, "Corinthians-SP", 0),
    m("2022-04-01", "Corinthians-SP", 2, "Palmeiras-SP", 0),
    m("2022-05-01", "Corinthians-SP", 1, "Flamengo-RJ", 1),
    m("2022-06-01", "Flamengo-RJ", 4, "Corinthians-SP", 0),
    m("2022-07-01", "Corinthians-SP", 3, "Santos-SP", 1, "Copa do Brasil"),
  ],
  players: [
    p("Gabriel Barbosa Almeida", 85, "Brazil", "Flamengo", "ST"),
    p("Alisson Becker", 89, "Brazil", "Liverpool", "GK"),
    p("Casemiro", 89, "Brazil", "Real Madrid", "CDM"),
    p("Lucas Paquetá", 84, "Brazil", "Flamengo", "CAM"),
    p("L. Messi", 94, "Argentina", "FC Barcelona", "RF"),
    p("Pedro", 80, "Brazil", "Flamengo", "ST"),
  ],
};

describe("Feature: Match queries", () => {
  it("Given matches between two teams, When searched head-to-head, Then they are returned newest first", () => {
    const result = searchMatches(fixture, { team: "Flamengo", opponent: "Fluminense" });
    expect(result.total).toBe(2);
    expect(result.matches.map((x) => x.date)).toEqual(["2023-05-28", "2023-03-01"]);
  });

  it("Given a season filter, When searched, Then only that season is returned", () => {
    const result = searchMatches(fixture, { team: "Palmeiras", season: 2023 });
    expect(result.matches.every((x) => x.season === 2023)).toBe(true);
    expect(result.total).toBe(3);
  });

  it("Given a competition filter, When searched, Then only that competition is returned", () => {
    const result = searchMatches(fixture, { competition: "Copa do Brasil" });
    expect(result.total).toBe(1);
    expect(result.matches[0]?.home).toBe("Corinthians-SP");
  });

  it("Given a date range, When searched, Then matches outside the range are excluded", () => {
    const result = searchMatches(fixture, { startDate: "2023-06-01", endDate: "2023-07-31" });
    expect(result.matches.map((x) => x.date).sort()).toEqual(["2023-06-10", "2023-07-01"]);
  });

  it("Given more matches than the limit, When searched, Then total still reports all of them", () => {
    const result = searchMatches(fixture, { team: "Corinthians", limit: 2 });
    expect(result.total).toBe(5);
    expect(result.matches).toHaveLength(2);
  });
});

describe("Feature: Team queries", () => {
  it("Given a team's matches, When the record is requested, Then wins, draws, losses and goals are counted", () => {
    const rec = teamRecord(fixture, { team: "Palmeiras", season: 2023 });
    expect(rec).toMatchObject({ matches: 3, wins: 1, draws: 2, losses: 0, goalsFor: 4, goalsAgainst: 1 });
    expect(rec.winRate).toBeCloseTo(1 / 3);
  });

  it("Given a venue filter, When the record is requested, Then only home games are counted", () => {
    // Home games in 2022: 2-0 v Palmeiras, 1-1 v Flamengo, 3-1 v Santos (cup).
    const rec = teamRecord(fixture, { team: "Corinthians", season: 2022, venue: "home" });
    expect(rec).toMatchObject({ matches: 3, wins: 2, draws: 1, losses: 0, goalsFor: 6, goalsAgainst: 2 });
  });

  it("Given a team with no matches, When the record is requested, Then it is all zeros", () => {
    const rec = teamRecord(fixture, { team: "Nobody FC" });
    expect(rec).toMatchObject({ matches: 0, wins: 0, winRate: 0 });
  });

  it("Given two teams, When head-to-head is requested, Then the record is from the first team's perspective", () => {
    const h = headToHead(fixture, { teamA: "Flamengo", teamB: "Fluminense" });
    expect(h.record).toMatchObject({ matches: 2, wins: 1, losses: 1, draws: 0, goalsFor: 2, goalsAgainst: 2 });
    expect(h.winsB).toBe(1);
  });

  it("Given two teams, When head-to-head is requested in either order, Then the totals agree", () => {
    const ab = headToHead(fixture, { teamA: "Palmeiras", teamB: "Santos" });
    const ba = headToHead(fixture, { teamA: "Santos", teamB: "Palmeiras" });
    expect(ab.record.wins).toBe(ba.winsB);
    expect(ab.record.goalsFor).toBe(ba.record.goalsAgainst);
  });
});

describe("Feature: Standings", () => {
  it("Given a season's results, When the table is calculated, Then points are 3 per win and 1 per draw", () => {
    const table = standings(fixture, { season: 2023 });
    const palmeiras = table.find((r) => r.team === "Palmeiras-SP");
    expect(palmeiras).toMatchObject({ points: 5, wins: 1, draws: 2, goalDifference: 3 });
    expect(table[0]?.team).toBe("Palmeiras-SP");
  });

  it("Given a season with no matches, When the table is calculated, Then it is empty", () => {
    expect(standings(fixture, { season: 1999 })).toEqual([]);
  });
});

describe("Feature: Player queries", () => {
  it("Given the player data, When searched by nationality, Then only that nationality is returned, best first", () => {
    const players = searchPlayers(fixture, { nationality: "Brazil" });
    expect(players.every((x) => x.nationality === "Brazil")).toBe(true);
    expect(players[0]?.name).toBe("Alisson Becker");
  });

  it("Given a club filter, When searched, Then players from that club are returned", () => {
    const players = searchPlayers(fixture, { club: "Flamengo" });
    expect(players.map((x) => x.name)).toEqual(["Gabriel Barbosa Almeida", "Lucas Paquetá", "Pedro"]);
  });

  it("Given a surname, When searched by name, Then the full name is found", () => {
    expect(searchPlayers(fixture, { name: "Gabriel Barbosa" })).toHaveLength(1);
  });

  it("Given a position and minimum rating, When searched, Then both constraints apply", () => {
    const players = searchPlayers(fixture, { position: "st", minOverall: 82 });
    expect(players.map((x) => x.name)).toEqual(["Gabriel Barbosa Almeida"]);
  });

  it("Given Brazilian players grouped by club, When summarized, Then counts and averages are correct", () => {
    const rows = clubSummary(fixture, { nationality: "Brazil" });
    expect(rows[0]).toEqual({ club: "Flamengo", players: 3, averageOverall: 83 });
  });
});

describe("Feature: Match statistics", () => {
  it("Given matches, When aggregated, Then average goals and win rates are computed", () => {
    const s = matchStatistics(fixture, { competition: "Brasileirão" });
    // 8 league matches: 2023 totals 9 goals, 2022 totals 8 goals (cup match excluded).
    expect(s.matches).toBe(8);
    expect(s.totalGoals).toBe(17);
    expect(s.averageGoalsPerMatch).toBe(2.13);
    expect(s.homeWinRate).toBeCloseTo(0.625);
    expect(s.drawRate).toBeCloseTo(0.375);
    expect(s.awayWinRate).toBe(0);
  });

  it("Given matches, When the biggest wins are listed, Then they are ordered by margin", () => {
    const s = matchStatistics(fixture, { biggestWinsLimit: 2 });
    expect(s.biggestWins.map((x) => `${x.home}-${x.away}`)).toEqual([
      "Flamengo-RJ-Corinthians-SP",
      "Palmeiras-SP-Santos-SP",
    ]);
  });

  it("Given no matches, When aggregated, Then the statistics are zero", () => {
    expect(matchStatistics(fixture, { season: 1999 })).toMatchObject({ matches: 0, averageGoalsPerMatch: 0 });
  });
});
