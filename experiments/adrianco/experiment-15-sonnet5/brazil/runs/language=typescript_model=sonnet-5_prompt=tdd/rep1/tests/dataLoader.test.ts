import { describe, it, expect } from "vitest";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  parseBrasileiraoMatches,
  parseCopaDoBrasilMatches,
  parseLibertadoresMatches,
  parseBRFootballDataset,
  parseHistoricalBrasileirao,
  parseFifaPlayers,
  loadAllData,
} from "../src/dataLoader.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.resolve(__dirname, "..", "data", "kaggle");

describe("parseBrasileiraoMatches", () => {
  const csv = [
    '"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"',
    '2012-05-19 18:30:00,"Palmeiras-SP","SP","Portuguesa-SP","SP",1,1,2012,1',
  ].join("\n");

  it("parses matches with normalized team names and correct goals/season", () => {
    const matches = parseBrasileiraoMatches(csv);
    expect(matches).toHaveLength(1);
    expect(matches[0]).toMatchObject({
      competition: "Brasileirão",
      source: "Brasileirao_Matches.csv",
      homeTeam: "Palmeiras",
      awayTeam: "Portuguesa",
      homeTeamState: "SP",
      awayTeamState: "SP",
      homeGoals: 1,
      awayGoals: 1,
      season: 2012,
      round: "1",
    });
    expect(matches[0].date.getUTCFullYear()).toBe(2012);
  });
});

describe("parseCopaDoBrasilMatches", () => {
  const csv = [
    '"round","datetime","home_team","away_team","home_goal","away_goal","season"',
    '"1",2012-03-07 16:00:00,"América - MG","Boavista Sport Club (antigo Esporte Clube Barreira) - RJ",0,0,2012',
  ].join("\n");

  it("parses matches and strips ' - UF' suffixes from team names, capturing the state separately", () => {
    const matches = parseCopaDoBrasilMatches(csv);
    expect(matches).toHaveLength(1);
    expect(matches[0]).toMatchObject({
      competition: "Copa do Brasil",
      source: "Brazilian_Cup_Matches.csv",
      homeTeam: "América",
      homeTeamState: "MG",
      awayTeamState: "RJ",
      awayGoals: 0,
      homeGoals: 0,
      season: 2012,
      round: "1",
    });
  });
});

describe("parseLibertadoresMatches", () => {
  const csv = [
    '"datetime","home_team","away_team","home_goal","away_goal","season","stage"',
    '2013-02-12 20:15:00,"Nacional (URU)","Barcelona-EQU","2","2",2013,"group stage"',
  ].join("\n");

  it("parses matches including the tournament stage", () => {
    const matches = parseLibertadoresMatches(csv);
    expect(matches).toHaveLength(1);
    expect(matches[0]).toMatchObject({
      competition: "Copa Libertadores",
      source: "Libertadores_Matches.csv",
      homeGoals: 2,
      awayGoals: 2,
      season: 2013,
      stage: "group stage",
    });
  });
});

describe("parseBRFootballDataset", () => {
  const csv = [
    "tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners",
    "Copa do Brasil,Sao Paulo,1.0,1.0,Flamengo,2.0,4.0,75.0,104.0,8.0,13.0,20:00:00,2023-09-24,0.0,0.0,DRAW,DRAW,6.0",
  ].join("\n");

  it("parses matches deriving season from the date and keeping extra stats", () => {
    const matches = parseBRFootballDataset(csv);
    expect(matches).toHaveLength(1);
    expect(matches[0]).toMatchObject({
      competition: "Copa do Brasil",
      source: "BR-Football-Dataset.csv",
      homeTeam: "Sao Paulo",
      awayTeam: "Flamengo",
      homeGoals: 1,
      awayGoals: 1,
      season: 2023,
    });
    expect(matches[0].extra?.total_corners).toBe(6);
  });
});

describe("parseHistoricalBrasileirao", () => {
  const csv = [
    "ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS",
    "2003.01.0001,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco de Ouro,",
  ].join("\n");

  it("parses matches from the Brazilian-format historical dataset", () => {
    const matches = parseHistoricalBrasileirao(csv);
    expect(matches).toHaveLength(1);
    expect(matches[0]).toMatchObject({
      competition: "Brasileirão",
      source: "novo_campeonato_brasileiro.csv",
      homeTeam: "Guarani",
      awayTeam: "Vasco",
      homeGoals: 4,
      awayGoals: 2,
      season: 2003,
      round: "1",
      venue: "Brinco de Ouro",
    });
    expect(matches[0].date.getUTCFullYear()).toBe(2003);
    expect(matches[0].date.getUTCMonth()).toBe(2);
    expect(matches[0].date.getUTCDate()).toBe(29);
  });
});

describe("parseFifaPlayers", () => {
  const csv = [
    ",ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number,Height,Weight",
    '0,158023,L. Messi,31,Argentina,94,94,FC Barcelona,RF,10,5\'7,159lbs',
  ].join("\n");

  it("parses player rows into Player objects", () => {
    const players = parseFifaPlayers(csv);
    expect(players).toHaveLength(1);
    expect(players[0]).toMatchObject({
      id: "158023",
      name: "L. Messi",
      age: 31,
      nationality: "Argentina",
      club: "FC Barcelona",
      overall: 94,
      potential: 94,
      position: "RF",
      jerseyNumber: 10,
    });
  });
});

describe("loadAllData", () => {
  it("loads and aggregates all 6 real dataset CSV files from data/kaggle", () => {
    const { matches, players } = loadAllData(DATA_DIR);

    const sources = new Set(matches.map((m) => m.source));
    expect(sources.has("Brasileirao_Matches.csv")).toBe(true);
    expect(sources.has("Brazilian_Cup_Matches.csv")).toBe(true);
    expect(sources.has("Libertadores_Matches.csv")).toBe(true);
    expect(sources.has("BR-Football-Dataset.csv")).toBe(true);
    expect(sources.has("novo_campeonato_brasileiro.csv")).toBe(true);

    expect(matches.length).toBeGreaterThan(20000);
    expect(players.length).toBeGreaterThan(15000);

    const flamengoMatches = matches.filter(
      (m) => m.homeTeam === "Flamengo" || m.awayTeam === "Flamengo",
    );
    expect(flamengoMatches.length).toBeGreaterThan(0);
  });

  it("collapses accented/unaccented and casing variants of the same team into one name", () => {
    const { matches } = loadAllData(DATA_DIR);
    const teamNames = new Set(matches.flatMap((m) => [m.homeTeam, m.awayTeam]));

    expect(teamNames.has("Gremio")).toBe(false);
    expect(teamNames.has("Grêmio")).toBe(true);
    expect(teamNames.has("Sao Paulo")).toBe(false);
    expect(teamNames.has("São Paulo")).toBe(true);
  });
});
