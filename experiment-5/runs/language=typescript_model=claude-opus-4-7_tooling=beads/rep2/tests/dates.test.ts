// Feature: Date parsing
//   The datasets use ISO ("2023-09-24"), datetime ("2012-05-19 18:30:00"),
//   and Brazilian ("29/03/2003") formats. The parser must yield ISO dates.
import { describe, it, expect } from "vitest";
import { parseDate, parseSeason, parseGoal } from "../src/dates.js";

describe("Feature: date and number parsing", () => {
  describe("Scenario: ISO and Brazilian dates", () => {
    it("Given ISO date, When parsed, Then YYYY-MM-DD is returned", () => {
      expect(parseDate("2023-09-24")).toBe("2023-09-24");
    });
    it("Given datetime, When parsed, Then date portion is returned", () => {
      expect(parseDate("2012-05-19 18:30:00")).toBe("2012-05-19");
    });
    it("Given Brazilian DD/MM/YYYY, When parsed, Then ISO is returned", () => {
      expect(parseDate("29/03/2003")).toBe("2003-03-29");
    });
    it("Given empty/NA values, When parsed, Then null is returned", () => {
      expect(parseDate("")).toBeNull();
      expect(parseDate("NA")).toBeNull();
      expect(parseDate(null)).toBeNull();
    });
  });

  describe("Scenario: numeric coercion", () => {
    it("parses ints from strings, NA -> null", () => {
      expect(parseSeason("2019")).toBe(2019);
      expect(parseSeason("NA")).toBeNull();
      expect(parseGoal("1.0")).toBe(1);
      expect(parseGoal("-")).toBeNull();
    });
  });
});
