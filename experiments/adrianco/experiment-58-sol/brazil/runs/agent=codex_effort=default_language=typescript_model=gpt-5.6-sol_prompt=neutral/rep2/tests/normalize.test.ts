import { describe, expect, it } from "vitest";

import { normalizeTeamName, normalizeText, parseSoccerDate } from "../src/normalize.js";

describe("data normalization", () => {
  it("folds accents without damaging UTF-8 source values", () => {
    expect(normalizeText("São Paulo, Grêmio & Avaí")).toBe("sao paulo gremio e avai");
  });

  it("unifies state suffixes and full team names", () => {
    expect(normalizeTeamName("Palmeiras-SP")).toBe("palmeiras");
    expect(normalizeTeamName("Sociedade Esportiva Palmeiras")).toBe("palmeiras");
    expect(normalizeTeamName("Sport Club Corinthians Paulista")).toBe("corinthians");
  });

  it("keeps ambiguous Atlético clubs distinct", () => {
    expect(normalizeTeamName("Atlético-MG")).toBe("atletico mg");
    expect(normalizeTeamName("Athletico-PR")).toBe("athletico pr");
    expect(normalizeTeamName("Atlético-GO")).toBe("atletico go");
  });

  it("parses ISO, timestamp, and Brazilian dates consistently", () => {
    expect(parseSoccerDate("2023-09-24").date).toBe("2023-09-24");
    expect(parseSoccerDate("2023-09-24 20:00:00").date).toBe("2023-09-24");
    expect(parseSoccerDate("29/03/2003").date).toBe("2003-03-29");
  });
});
