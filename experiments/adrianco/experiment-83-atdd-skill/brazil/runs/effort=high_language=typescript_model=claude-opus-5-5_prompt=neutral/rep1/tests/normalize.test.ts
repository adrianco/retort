import { describe, expect, it } from "vitest";
import { foldText, parseDate, parseIntOrNull, stripAccents } from "../src/normalize.js";

describe("date parsing", () => {
  it("parses ISO dates", () => {
    expect(parseDate("2023-09-24")).toEqual({ date: "2023-09-24" });
  });
  it("parses ISO dates with time", () => {
    expect(parseDate("2012-05-19 18:30:00")).toEqual({ date: "2012-05-19", time: "18:30" });
  });
  it("parses Brazilian DD/MM/YYYY dates", () => {
    expect(parseDate("29/03/2003")).toEqual({ date: "2003-03-29" });
    expect(parseDate("1/2/2010 16:00")).toEqual({ date: "2010-02-01", time: "16:00" });
  });
  it("returns null for NA / garbage", () => {
    expect(parseDate("NA")).toBeNull();
    expect(parseDate("")).toBeNull();
  });
});

describe("text and numbers", () => {
  it("strips Portuguese accents and cedillas", () => {
    expect(stripAccents("São Paulo Grêmio Avaí Confiança")).toBe("Sao Paulo Gremio Avai Confianca");
    expect(foldText("  Atlético   MINEIRO ")).toBe("atletico mineiro");
  });
  it("parses goal cells in different formats", () => {
    expect(parseIntOrNull("2")).toBe(2);
    expect(parseIntOrNull("1.0")).toBe(1);
    expect(parseIntOrNull("NA")).toBeNull();
    expect(parseIntOrNull("-")).toBeNull();
  });
});
