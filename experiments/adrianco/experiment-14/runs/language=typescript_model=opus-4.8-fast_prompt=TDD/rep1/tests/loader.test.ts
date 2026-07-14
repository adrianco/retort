import { describe, it, expect } from "vitest";
import {
  parseBrasileirao,
  parseCup,
  parseLibertadores,
  parseBRFootball,
  parseNovoBrasileirao,
  parsePlayers,
  canonicalMatches,
} from "../src/loader.js";
import type { Match } from "../src/types.js";

function m(over: Partial<Match>): Match {
  return {
    competition: "Brasileirão Série A",
    date: null,
    season: 2019,
    homeTeam: "A",
    awayTeam: "B",
    homeKey: "a",
    awayKey: "b",
    homeGoals: 1,
    awayGoals: 0,
    source: "src1",
    ...over,
  };
}

describe("parseBrasileirao", () => {
  const csv = `"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
2012-05-19 18:30:00,"Palmeiras-SP","SP","Portuguesa-SP","SP",1,1,2012,1
2012-05-19 18:30:00,"Sport-PE","PE","Flamengo-RJ","RJ",2,0,2012,1`;

  it("parses rows into Match objects with canonical competition", () => {
    const matches = parseBrasileirao(csv);
    expect(matches).toHaveLength(2);
    expect(matches[0].competition).toBe("Brasileirão Série A");
  });

  it("keeps raw display names and normalized keys", () => {
    const [m] = parseBrasileirao(csv);
    expect(m.homeTeam).toBe("Palmeiras-SP");
    expect(m.homeKey).toBe("palmeiras");
    expect(m.awayKey).toBe("portuguesa");
  });

  it("parses goals, season, round and date", () => {
    const m = parseBrasileirao(csv)[1];
    expect(m.homeGoals).toBe(2);
    expect(m.awayGoals).toBe(0);
    expect(m.season).toBe(2012);
    expect(m.round).toBe("1");
    expect(m.date?.getUTCFullYear()).toBe(2012);
  });
});

describe("parseCup", () => {
  const csv = `"round","datetime","home_team","away_team","home_goal","away_goal","season"
"1",2012-03-07 16:00:00,"Boavista - RJ","América - MG",0,0,2012`;

  it("maps to Copa do Brasil", () => {
    const [m] = parseCup(csv);
    expect(m.competition).toBe("Copa do Brasil");
    expect(m.homeKey).toBe("boavista");
    expect(m.awayKey).toBe("america mineiro");
    expect(m.season).toBe(2012);
    expect(m.round).toBe("1");
  });
});

describe("parseLibertadores", () => {
  const csv = `"datetime","home_team","away_team","home_goal","away_goal","season","stage"
2013-02-12 20:15:00,"Nacional (URU)","Barcelona-EQU","2","2",2013,"group stage"`;

  it("maps to Copa Libertadores with stage and string goals", () => {
    const [m] = parseLibertadores(csv);
    expect(m.competition).toBe("Copa Libertadores");
    expect(m.stage).toBe("group stage");
    expect(m.homeGoals).toBe(2);
    expect(m.awayGoals).toBe(2);
    expect(m.homeKey).toBe("nacional");
    expect(m.awayKey).toBe("barcelona");
  });
});

describe("parseBRFootball", () => {
  const csv = `tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners
Serie A,Sao Paulo,1.0,1.0,Flamengo,2.0,4.0,75.0,104.0,8.0,13.0,20:00:00,2023-09-24,0.0,0.0,DRAW,DRAW,6.0
Copa do Brasil,Flamengo,0.0,1.0,Sao Paulo,3.0,4.0,121.0,81.0,6.0,5.0,20:00:00,2023-09-17,-1.0,1.0,LOST,WON,7.0`;

  it("maps tournament names to canonical competitions", () => {
    const matches = parseBRFootball(csv);
    expect(matches[0].competition).toBe("Brasileirão Série A");
    expect(matches[1].competition).toBe("Copa do Brasil");
  });

  it("derives season from date year and parses float goals to ints", () => {
    const m = parseBRFootball(csv)[0];
    expect(m.season).toBe(2023);
    expect(m.homeGoals).toBe(1);
    expect(m.awayGoals).toBe(1);
  });

  it("captures extended stats", () => {
    const m = parseBRFootball(csv)[0];
    expect(m.stats?.homeCorners).toBe(2);
    expect(m.stats?.awayShots).toBe(13);
    expect(m.stats?.totalCorners).toBe(6);
  });
});

describe("parseNovoBrasileirao", () => {
  const csv = `ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
2003.01.0001,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco de Ouro,`;

  it("maps to historical Brasileirão with Brazilian date and arena", () => {
    const [m] = parseNovoBrasileirao(csv);
    expect(m.competition).toBe("Brasileirão Série A");
    expect(m.homeKey).toBe("guarani");
    expect(m.awayKey).toBe("vasco");
    expect(m.homeGoals).toBe(4);
    expect(m.awayGoals).toBe(2);
    expect(m.season).toBe(2003);
    expect(m.round).toBe("1");
    expect(m.arena).toBe("Brinco de Ouro");
    expect(m.date?.getUTCFullYear()).toBe(2003);
    expect(m.date?.getUTCMonth()).toBe(2);
  });
});

describe("parsePlayers", () => {
  const csv = `,ID,Name,Age,Photo,Nationality,Flag,Overall,Potential,Club,Club Logo,Value,Wage,Special,Preferred Foot,International Reputation,Weak Foot,Skill Moves,Work Rate,Body Type,Real Face,Position,Jersey Number,Joined,Loaned From,Contract Valid Until,Height,Weight
0,158023,L. Messi,31,photo,Argentina,flag,94,94,FC Barcelona,logo,€110.5M,€565K,2202,Left,5,4,4,Medium/ Medium,Messi,Yes,RF,10,"Jul 1, 2004",,2021,5'7,159lbs
1,200000,Gabriel Barbosa,26,photo,Brazil,flag,83,85,Flamengo,logo,€20M,€50K,2000,Right,4,4,4,High/ Medium,Normal,Yes,ST,9,"Jan 1, 2019",,2024,5'9,untreated`;

  it("parses player rows", () => {
    const players = parsePlayers(csv);
    expect(players).toHaveLength(2);
    expect(players[0].name).toBe("L. Messi");
    expect(players[0].overall).toBe(94);
    expect(players[0].nationality).toBe("Argentina");
  });

  it("builds normalized name and club keys", () => {
    const gabriel = parsePlayers(csv)[1];
    expect(gabriel.nameKey).toBe("gabriel barbosa");
    expect(gabriel.clubKey).toBe("flamengo");
    expect(gabriel.position).toBe("ST");
    expect(gabriel.jerseyNumber).toBe(9);
  });
});

describe("canonicalMatches", () => {
  it("drops matches with non-finite goals", () => {
    const result = canonicalMatches([
      m({ source: "s", homeGoals: NaN }),
      m({ source: "s", homeKey: "c", awayKey: "d", homeGoals: 2, awayGoals: 2 }),
    ]);
    expect(result).toHaveLength(1);
    expect(result[0].homeKey).toBe("c");
  });

  it("keeps only the most complete source per competition+season", () => {
    const matches = [
      // source 'rich' has 2 matches for SerieA 2019; 'poor' has 1.
      m({ source: "rich", homeKey: "a", awayKey: "b" }),
      m({ source: "rich", homeKey: "c", awayKey: "d" }),
      m({ source: "poor", homeKey: "a", awayKey: "b" }),
    ];
    const result = canonicalMatches(matches);
    expect(result).toHaveLength(2);
    expect(result.every((x) => x.source === "rich")).toBe(true);
  });

  it("treats different seasons and competitions independently", () => {
    const matches = [
      m({ source: "s1", season: 2018 }),
      m({ source: "s2", season: 2019 }),
      m({ source: "s3", competition: "Copa do Brasil", season: 2019 }),
    ];
    const result = canonicalMatches(matches);
    expect(result).toHaveLength(3);
  });
});
