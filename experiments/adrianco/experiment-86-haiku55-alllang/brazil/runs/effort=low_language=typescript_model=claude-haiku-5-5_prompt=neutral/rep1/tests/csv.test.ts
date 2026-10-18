import { describe, expect, it } from "vitest";
import { parseCsv } from "../src/csv.js";

describe("Feature: CSV parsing", () => {
  it("Given a header and rows, When parsed, Then each row is keyed by header", () => {
    const rows = parseCsv("a,b\n1,2\n3,4\n");
    expect(rows).toEqual([
      { a: "1", b: "2" },
      { a: "3", b: "4" },
    ]);
  });

  it("Given quoted fields with commas and doubled quotes, When parsed, Then they are preserved", () => {
    const rows = parseCsv('name,note\n"Santos, SP","said ""hi"""\n');
    expect(rows[0]).toEqual({ name: "Santos, SP", note: 'said "hi"' });
  });

  it("Given a UTF-8 BOM and CRLF endings, When parsed, Then the BOM is ignored", () => {
    const rows = parseCsv("﻿id,team\r\n1,Grêmio\r\n");
    expect(rows).toEqual([{ id: "1", team: "Grêmio" }]);
  });

  it("Given an empty leading header column, When parsed, Then it is keyed by the empty string", () => {
    const rows = parseCsv(",ID,Name\n0,158023,L. Messi\n");
    expect(rows[0]).toEqual({ "": "0", ID: "158023", Name: "L. Messi" });
  });

  it("Given a quoted field containing a newline, When parsed, Then the newline is kept", () => {
    const rows = parseCsv('a,b\n"line1\nline2",x\n');
    expect(rows[0]?.a).toBe("line1\nline2");
  });
});
