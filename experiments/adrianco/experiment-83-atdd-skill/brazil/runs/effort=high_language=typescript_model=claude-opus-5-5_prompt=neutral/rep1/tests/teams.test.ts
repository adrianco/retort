import { describe, expect, it } from "vitest";
import { TeamRegistry, parseTeamName } from "../src/teams.js";
import { queries } from "./helpers.js";

describe("parseTeamName", () => {
  it("extracts state suffixes in all formats", () => {
    expect(parseTeamName("Palmeiras-SP")).toMatchObject({ base: "palmeiras", state: "sp" });
    expect(parseTeamName("Palmeiras - SP")).toMatchObject({ base: "palmeiras", state: "sp" });
    expect(parseTeamName("Vasco Da Gama RJ")).toMatchObject({ base: "vasco da gama", state: "rj" });
    expect(parseTeamName("River (PI)")).toMatchObject({ base: "river", state: "pi" });
  });
  it("keeps foreign country qualifiers", () => {
    expect(parseTeamName("Nacional (URU)")).toMatchObject({ base: "nacional", qualifier: "uru" });
    expect(parseTeamName("Nacional-URU")).toMatchObject({ base: "nacional", qualifier: "uru" });
  });
  it("removes club-type noise and abbreviation dots", () => {
    expect(parseTeamName("EC Bahia").base).toBe("bahia");
    expect(parseTeamName("Fortaleza EC").base).toBe("fortaleza");
    expect(parseTeamName("C. R. B. - AL")).toMatchObject({ base: "crb", state: "al" });
    expect(parseTeamName("A.b.c. - RN")).toMatchObject({ base: "abc", state: "rn" });
    expect(parseTeamName("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")).toMatchObject({ base: "boavista", state: "rj" });
  });
});

describe("TeamRegistry", () => {
  const build = (names: string[]) => {
    const r = new TeamRegistry();
    names.forEach((n) => r.observe(n, "domestic"));
    r.finalize();
    return r;
  };

  it("maps spelling variants of the same club to one id", () => {
    const r = build(["Sao Paulo-SP", "São Paulo - SP", "São Paulo", "Sao Paulo"]);
    const ids = new Set(["Sao Paulo-SP", "São Paulo - SP", "São Paulo", "Sao Paulo"].map((n) => r.idFor(n, "domestic")));
    expect([...ids]).toEqual(["sao-paulo"]);
    expect(r.get("sao-paulo")!.name).toBe("São Paulo");
  });

  it("disambiguates Atlético / América by state", () => {
    const r = build(["Atletico-MG", "Atlético-PR", "Atletico-GO", "Atlético Mineiro", "Athletico Paranaense", "América-RN", "America MG"]);
    expect(r.idFor("Atletico-MG", "domestic")).toBe("atletico-mg");
    expect(r.idFor("Atlético Mineiro", "domestic")).toBe("atletico-mg");
    expect(r.idFor("Atlético-PR", "domestic")).toBe("athletico-pr");
    expect(r.idFor("Athletico Paranaense", "domestic")).toBe("athletico-pr");
    expect(r.idFor("Atletico-GO", "domestic")).toBe("atletico-go");
    expect(r.idFor("América-RN", "domestic")).toBe("america-rn");
    expect(r.idFor("America MG", "domestic")).toBe("america-mg");
  });

  it("keeps same-named clubs from other states separate", () => {
    const r = build(["Flamengo-RJ", "Flamengo - PI", "Santos-SP", "Santos AP", "Botafogo PB", "Botafogo RJ"]);
    expect(r.idFor("Flamengo-RJ", "domestic")).toBe("flamengo");
    expect(r.idFor("Flamengo - PI", "domestic")).toBe("flamengo-pi");
    expect(r.idFor("Santos AP", "domestic")).toBe("santos-ap");
    expect(r.idFor("Botafogo PB", "domestic")).toBe("botafogo-pb");
    expect(r.idFor("Botafogo RJ", "domestic")).toBe("botafogo");
  });

  it("merges an unsuffixed small club into its single state variant", () => {
    const r = build(["Tombense - MG", "Tombense", "Tombense MG"]);
    expect(r.idFor("Tombense", "domestic")).toBe("tombense-mg");
    expect(r.idFor("Tombense MG", "domestic")).toBe("tombense-mg");
  });
});

describe("team resolution against the real data", () => {
  const q = queries();
  it.each([
    ["Flamengo", "flamengo"],
    ["flamengo-rj", "flamengo"],
    ["Sao Paulo FC", "sao-paulo"],
    ["SÃO PAULO", "sao-paulo"],
    ["Gremio", "gremio"],
    ["Sport Club Corinthians Paulista", "corinthians"],
    ["Vasco", "vasco"],
    ["Bragantino", "bragantino"],
    ["Galo", "atletico-mg"],
    ["Sport Recife", "sport"],
    ["Athletico", "athletico-pr"],
    ["Nacional-URU", "nacional-uru"],
  ])("resolves %s -> %s", (input, id) => {
    expect(q.resolveTeam(input).id).toBe(id);
  });

  it("fuzzy matches fragments, preferring the most prominent club", () => {
    expect(q.resolveTeam("Fluminen").id).toBe("fluminense");
  });

  it("throws a helpful error for unknown teams", () => {
    expect(() => q.resolveTeam("Manchester United")).toThrow(/No team matching/);
  });
});
