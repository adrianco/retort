import { describe, it, expect } from "vitest";
import { parseCSV } from "../src/csv.js";

describe("parseCSV", () => {
  it("parses a simple unquoted CSV into row objects", () => {
    const rows = parseCSV("a,b\n1,2\n3,4");
    expect(rows).toEqual([
      { a: "1", b: "2" },
      { a: "3", b: "4" },
    ]);
  });

  it("handles quoted fields containing commas", () => {
    const rows = parseCSV('a,b\n"1,2",3');
    expect(rows).toEqual([{ a: "1,2", b: "3" }]);
  });

  it("handles escaped double quotes inside quoted fields", () => {
    const rows = parseCSV('a,b\n"he said ""hi""",3');
    expect(rows).toEqual([{ a: 'he said "hi"', b: "3" }]);
  });

  it("strips a leading UTF-8 BOM from the header", () => {
    const rows = parseCSV("﻿a,b\n1,2");
    expect(rows).toEqual([{ a: "1", b: "2" }]);
  });

  it("handles CRLF line endings", () => {
    const rows = parseCSV("a,b\r\n1,2\r\n3,4");
    expect(rows).toEqual([
      { a: "1", b: "2" },
      { a: "3", b: "4" },
    ]);
  });

  it("skips trailing blank lines", () => {
    const rows = parseCSV("a,b\n1,2\n");
    expect(rows).toEqual([{ a: "1", b: "2" }]);
  });

  it("preserves UTF-8 accented characters", () => {
    const rows = parseCSV("team\nSão Paulo");
    expect(rows).toEqual([{ team: "São Paulo" }]);
  });
});
