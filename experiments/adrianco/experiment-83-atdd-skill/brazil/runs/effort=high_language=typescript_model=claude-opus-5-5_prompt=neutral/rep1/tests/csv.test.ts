import { describe, expect, it } from "vitest";
import { parseCsv, parseCsvObjects } from "../src/csv.js";

describe("CSV parser", () => {
  it("parses quoted fields with commas, quotes and newlines", () => {
    const rows = parseCsv('a,b,c\n"x, y","he said ""hi""","multi\nline"\n');
    expect(rows).toEqual([
      ["a", "b", "c"],
      ["x, y", 'he said "hi"', "multi\nline"],
    ]);
  });

  it("handles CRLF, a UTF-8 BOM, empty fields and a missing final newline", () => {
    const objs = parseCsvObjects("﻿id,name,club\r\n1,São Paulo,\r\n2,Grêmio,Grêmio");
    expect(objs).toEqual([
      { id: "1", name: "São Paulo", club: "" },
      { id: "2", name: "Grêmio", club: "Grêmio" },
    ]);
  });

  it("skips blank lines", () => {
    expect(parseCsv("a\n\n1\n\n")).toEqual([["a"], ["1"]]);
  });
});
