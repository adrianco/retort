import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { parseCsv } from "../src/csv.js";

describe("CSV parser", () => {
  it("Given quoted Brazilian text, when parsed, then commas, escaped quotes, and CRLF are preserved", () => {
    const rows = parseCsv('\uFEFFname,club,notes\r\n"José","São Paulo","Said ""olá"", then left"\r\n');
    assert.deepEqual(rows, [{ name: "José", club: "São Paulo", notes: 'Said "olá", then left' }]);
  });
});
