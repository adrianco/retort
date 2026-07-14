import { describe, it, expect, beforeEach } from "vitest";
import { createTools, type ToolDef } from "../src/tools.js";
import { SoccerDatabase } from "../src/database.js";
import type { Match, Player } from "../src/types.js";
import { normalizeTeamName, normalizeName, parseDate } from "../src/normalize.js";

function mkMatch(p: Partial<Match> & { home: string; away: string; hg: number; ag: number }): Match {
  return {
    competition: p.competition ?? "Brasileirão Série A",
    date: p.date ?? parseDate("2020-01-01"),
    season: p.season ?? 2020,
    round: p.round,
    stage: p.stage,
    homeTeam: p.home,
    awayTeam: p.away,
    homeKey: normalizeTeamName(p.home),
    awayKey: normalizeTeamName(p.away),
    homeGoals: p.hg,
    awayGoals: p.ag,
    arena: p.arena,
    source: p.source ?? "test",
  };
}
function mkPlayer(p: Partial<Player> & { name: string }): Player {
  return {
    id: p.id ?? 1,
    name: p.name,
    nameKey: normalizeName(p.name),
    age: p.age ?? 25,
    nationality: p.nationality ?? "Brazil",
    overall: p.overall ?? 75,
    potential: p.potential ?? 80,
    club: p.club ?? "Flamengo",
    clubKey: normalizeTeamName(p.club ?? "Flamengo"),
    position: p.position ?? "ST",
    jerseyNumber: p.jerseyNumber ?? 9,
    height: "",
    weight: "",
  };
}

let tools: Map<string, ToolDef>;

beforeEach(() => {
  const matches: Match[] = [
    mkMatch({ home: "Flamengo-RJ", away: "Fluminense-RJ", hg: 2, ag: 1, season: 2023, date: parseDate("2023-09-03")!, round: "22" }),
    mkMatch({ home: "Fluminense-RJ", away: "Flamengo-RJ", hg: 1, ag: 0, season: 2023, date: parseDate("2023-05-28")!, round: "8" }),
    mkMatch({ home: "Flamengo", away: "Corinthians", hg: 5, ag: 0, season: 2019, date: parseDate("2019-10-27")!, competition: "Copa Libertadores", stage: "final" }),
  ];
  const players: Player[] = [
    mkPlayer({ name: "Gabriel Barbosa", overall: 83, club: "Flamengo", position: "ST" }),
    mkPlayer({ name: "L. Messi", nationality: "Argentina", overall: 94, club: "FC Barcelona", position: "RW" }),
  ];
  const db = new SoccerDatabase({ matches, players });
  tools = new Map(createTools(db).map((t) => [t.name, t]));
});

function run(name: string, args: unknown): string {
  const tool = tools.get(name);
  if (!tool) throw new Error(`no tool ${name}`);
  const parsed = tool.schema.parse(args);
  return tool.handler(parsed);
}

describe("tool registry", () => {
  it("registers the expected tools", () => {
    expect(tools.has("find_matches")).toBe(true);
    expect(tools.has("team_record")).toBe(true);
    expect(tools.has("head_to_head")).toBe(true);
    expect(tools.has("standings")).toBe(true);
    expect(tools.has("match_statistics")).toBe(true);
    expect(tools.has("biggest_wins")).toBe(true);
    expect(tools.has("search_players")).toBe(true);
    expect(tools.has("brazilian_players_by_club")).toBe(true);
  });

  it("every tool has a description and JSON schema", () => {
    for (const t of tools.values()) {
      expect(t.description.length).toBeGreaterThan(0);
      expect(t.jsonSchema).toBeTruthy();
    }
  });
});

describe("find_matches tool", () => {
  it("lists matches between two teams and appends head-to-head", () => {
    const out = run("find_matches", { team: "Flamengo", team2: "Fluminense" });
    expect(out).toContain("Flamengo");
    expect(out).toContain("Head-to-head");
  });

  it("with no filters returns all matches", () => {
    const out = run("find_matches", {});
    expect(out).toContain("2023-09-03");
    expect(out).toContain("Matches found");
  });
});

describe("team_record tool", () => {
  it("returns a formatted record", () => {
    const out = run("team_record", { team: "Flamengo", season: 2023 });
    expect(out).toContain("Matches: 2");
    expect(out).toContain("Win rate");
  });
});

describe("head_to_head tool", () => {
  it("summarises and lists games", () => {
    const out = run("head_to_head", { teamA: "Flamengo", teamB: "Fluminense" });
    expect(out).toContain("Flamengo 1 win");
    expect(out).toContain("Fluminense 1 win");
  });
});

describe("standings tool", () => {
  it("returns a table for a season", () => {
    const out = run("standings", { competition: "Brasileirão", season: 2023 });
    expect(out).toContain("1.");
    expect(out).toContain("pts");
  });
});

describe("statistics & biggest wins tools", () => {
  it("computes statistics", () => {
    const out = run("match_statistics", { season: 2023 });
    expect(out).toContain("Average goals per match");
  });
  it("lists biggest wins", () => {
    const out = run("biggest_wins", { limit: 1 });
    expect(out).toContain("5-0");
  });
});

describe("player tools", () => {
  it("searches players by name", () => {
    const out = run("search_players", { name: "Gabriel" });
    expect(out).toContain("Gabriel Barbosa");
  });
  it("groups Brazilian players by club", () => {
    const out = run("brazilian_players_by_club", {});
    expect(out).toContain("Flamengo");
  });
});
