import { describe, expect, it } from "vitest";
import { normalizeText, parseTeamName, stripAccents } from "../src/teams.js";

const key = (s: string) => parseTeamName(s).key;

describe("team name normalisation", () => {
  it("strips accents and cedillas", () => {
    expect(stripAccents("São Paulo Grêmio Avaí Ceará Fortaleza Esporte Clube Açaí")).toBe("Sao Paulo Gremio Avai Ceara Fortaleza Esporte Clube Acai");
    expect(normalizeText("C. R. B.")).toBe("crb");
  });

  it("maps state-suffixed, plain and full names to the same club", () => {
    for (const v of ["Palmeiras-SP", "Palmeiras - SP", "Palmeiras", "palmeiras"]) expect(key(v)).toBe("palmeiras");
    for (const v of ["Corinthians-SP", "Corinthians", "Sport Club Corinthians Paulista"]) expect(key(v)).toBe("corinthians");
    for (const v of ["Sao Paulo-SP", "São Paulo - SP", "São Paulo", "Sao Paulo", "São Paulo FC"]) expect(key(v)).toBe("sao-paulo");
    for (const v of ["Gremio-RS", "Grêmio - RS", "Grêmio", "Gremio RS"]) expect(key(v)).toBe("gremio");
    for (const v of ["Vasco da Gama-RJ", "Vasco", "Vasco Da Gama RJ"]) expect(key(v)).toBe("vasco");
    for (const v of ["Sport-PE", "Sport Recife", "Sport Club do Recife"]) expect(key(v)).toBe("sport");
    for (const v of ["Red Bull Bragantino-SP", "Bragantino - SP", "Bragantino"]) expect(key(v)).toBe("bragantino");
    for (const v of ["Csa-AL", "C.s.a. - AL", "CSA"]) expect(key(v)).toBe("csa");
    for (const v of ["C. R. B. - AL", "Crb - AL", "CRB"]) expect(key(v)).toBe("crb");
  });

  it("distinguishes the three Atléticos and their many spellings", () => {
    for (const v of ["Atletico-MG", "Atlético - MG", "Atlético Mineiro", "Atletico Mineiro"]) expect(key(v)).toBe("atletico-mg");
    for (const v of ["Atletico-PR", "Athletico-PR", "Athletico", "Athletico Paranaense", "Atlético Paranaense - PR"]) expect(key(v)).toBe("athletico-pr");
    for (const v of ["Atletico-GO", "Atlético - GO", "Atletico Goianiense"]) expect(key(v)).toBe("atletico-go");
  });

  it("keeps same-named clubs from other states apart", () => {
    expect(key("Flamengo - PI")).toBe("flamengo-pi");
    expect(key("Botafogo - PB")).toBe("botafogo-pb");
    expect(key("Botafogo SP")).toBe("botafogo-sp");
    expect(key("Santos - AP")).toBe("santos-ap");
    expect(key("America - RN")).toBe("america-rn");
    expect(key("América - MG")).toBe("america-mg");
  });

  it("handles foreign Libertadores clubs and country suffixes", () => {
    expect(key("Nacional (URU)")).toBe(key("Nacional-URU"));
    expect(key("Guaraní (PAR)")).not.toBe(key("Guarani - SP"));
    expect(key("Libertad-PAR")).toBe(key("Libertad"));
    expect(key("Barcelona-EQU")).toBe("barcelona-sc");
  });

  it("recognises FIFA club names for Brazilian clubs", () => {
    expect(parseTeamName("América FC (Minas Gerais)").club?.key).toBe("america-mg");
    expect(parseTeamName("Ceará Sporting Club").club?.key).toBe("ceara");
    expect(parseTeamName("Atlético Paranaense").club?.key).toBe("athletico-pr");
    expect(parseTeamName("Santos Laguna").club).toBeUndefined();
    expect(parseTeamName("Vitória Guimarães").club).toBeUndefined();
  });
});
