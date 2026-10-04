import { describe, expect, it } from "vitest";
import { parseCsv } from "../src/csv.js";
import { normalizeDateBound, parseDate } from "../src/dates.js";

describe("parseCsv", () => {
  it("parses quoted fields, escaped quotes, embedded commas and newlines", () => {
    const rows = parseCsv('a,b,c\r\n"x, y","he said ""hi""","multi\nline"\n1,2,3\n');
    expect(rows).toEqual([
      { a: "x, y", b: 'he said "hi"', c: "multi\nline" },
      { a: "1", b: "2", c: "3" },
    ]);
  });

  it("strips a UTF-8 BOM and keeps accented characters", () => {
    const rows = parseCsv("﻿team,city\nGrêmio,Porto Alegre\nSão Paulo,São Paulo\nAvaí,Florianópolis\n");
    expect(Object.keys(rows[0])).toEqual(["team", "city"]);
    expect(rows.map((r) => r.team)).toEqual(["Grêmio", "São Paulo", "Avaí"]);
  });

  it("fills missing trailing cells with empty strings", () => {
    expect(parseCsv("a,b\n1\n")).toEqual([{ a: "1", b: "" }]);
  });
});

describe("parseDate", () => {
  it("handles ISO, ISO with time and Brazilian DD/MM/YYYY formats", () => {
    expect(parseDate("2023-09-24")).toEqual({ date: "2023-09-24", time: undefined });
    expect(parseDate("2012-05-19 18:30:00")).toEqual({ date: "2012-05-19", time: "18:30" });
    expect(parseDate("29/03/2003")).toEqual({ date: "2003-03-29", time: undefined });
    expect(parseDate("2023-09-24T20:00:00Z")?.date).toBe("2023-09-24");
  });

  it("rejects missing or invalid values", () => {
    expect(parseDate("NA")).toBeNull();
    expect(parseDate("")).toBeNull();
    expect(parseDate("not a date")).toBeNull();
    expect(parseDate("2020-13-01")).toBeNull();
  });

  it("expands year and month bounds", () => {
    expect(normalizeDateBound("2019", false)).toBe("2019-01-01");
    expect(normalizeDateBound("2019", true)).toBe("2019-12-31");
    expect(normalizeDateBound("2019-05", true)).toBe("2019-05-31");
    expect(normalizeDateBound("01/02/2019", false)).toBe("2019-02-01");
  });
});
