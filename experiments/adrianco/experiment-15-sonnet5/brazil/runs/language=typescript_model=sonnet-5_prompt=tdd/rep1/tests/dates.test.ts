import { describe, it, expect } from "vitest";
import { parseFlexibleDate, formatISODate, isWithinDateRange } from "../src/dates.js";

describe("parseFlexibleDate", () => {
  it("parses ISO date-only strings", () => {
    const d = parseFlexibleDate("2023-09-24");
    expect(d.getUTCFullYear()).toBe(2023);
    expect(d.getUTCMonth()).toBe(8);
    expect(d.getUTCDate()).toBe(24);
  });

  it("parses ISO datetime strings with time", () => {
    const d = parseFlexibleDate("2012-05-19 18:30:00");
    expect(d.getUTCFullYear()).toBe(2012);
    expect(d.getUTCMonth()).toBe(4);
    expect(d.getUTCDate()).toBe(19);
    expect(d.getUTCHours()).toBe(18);
    expect(d.getUTCMinutes()).toBe(30);
  });

  it("parses Brazilian DD/MM/YYYY strings", () => {
    const d = parseFlexibleDate("29/03/2003");
    expect(d.getUTCFullYear()).toBe(2003);
    expect(d.getUTCMonth()).toBe(2);
    expect(d.getUTCDate()).toBe(29);
  });

  it("throws on an unparseable date", () => {
    expect(() => parseFlexibleDate("not-a-date")).toThrow();
  });
});

describe("formatISODate", () => {
  it("formats a parsed ISO datetime back to YYYY-MM-DD", () => {
    expect(formatISODate(parseFlexibleDate("2012-05-19 18:30:00"))).toBe("2012-05-19");
  });

  it("formats a parsed Brazilian date to YYYY-MM-DD", () => {
    expect(formatISODate(parseFlexibleDate("29/03/2003"))).toBe("2003-03-29");
  });
});

describe("isWithinDateRange", () => {
  it("returns true when the date falls within an inclusive range", () => {
    const d = parseFlexibleDate("2020-06-15");
    expect(isWithinDateRange(d, "2020-01-01", "2020-12-31")).toBe(true);
  });

  it("returns false when the date falls outside the range", () => {
    const d = parseFlexibleDate("2019-06-15");
    expect(isWithinDateRange(d, "2020-01-01", "2020-12-31")).toBe(false);
  });

  it("treats missing bounds as open-ended", () => {
    const d = parseFlexibleDate("2020-06-15");
    expect(isWithinDateRange(d, undefined, undefined)).toBe(true);
    expect(isWithinDateRange(d, "2020-06-15", undefined)).toBe(true);
    expect(isWithinDateRange(d, undefined, "2020-06-15")).toBe(true);
  });
});
