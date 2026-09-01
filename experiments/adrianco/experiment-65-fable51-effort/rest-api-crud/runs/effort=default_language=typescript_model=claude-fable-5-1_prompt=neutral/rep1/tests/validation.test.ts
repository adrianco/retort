import { describe, expect, it } from "vitest";
import { isValidIsbn, normalizeIsbn, parseId, validateBookInput } from "../src/validation.js";

describe("isValidIsbn", () => {
  it("accepts valid ISBN-10 and ISBN-13 with or without separators", () => {
    expect(isValidIsbn("0-306-40615-2")).toBe(true);
    expect(isValidIsbn("0306406152")).toBe(true);
    expect(isValidIsbn("978-0441013593")).toBe(true);
    expect(isValidIsbn("9780441013593")).toBe(true);
  });

  it("rejects bad checksums and wrong lengths", () => {
    expect(isValidIsbn("0-306-40615-3")).toBe(false);
    expect(isValidIsbn("9780441013594")).toBe(false);
    expect(isValidIsbn("12345")).toBe(false);
    expect(isValidIsbn("")).toBe(false);
  });
});

describe("validateBookInput", () => {
  it("stores the ISBN in normalized form", () => {
    expect(normalizeIsbn(" 0-306-40615-x ")).toBe("030640615X");
    const result = validateBookInput({ title: "T", author: "A", isbn: "978-0-306-40615-7" });
    expect(result).toEqual({
      ok: true,
      value: { title: "T", author: "A", year: null, isbn: "9780306406157" },
    });
  });

  it("trims text fields and normalises optional fields to null", () => {
    const result = validateBookInput({ title: "  Dune ", author: " Frank Herbert " });
    expect(result).toEqual({
      ok: true,
      value: { title: "Dune", author: "Frank Herbert", year: null, isbn: null },
    });
  });

  it("rejects non-object bodies", () => {
    expect(validateBookInput(null).ok).toBe(false);
    expect(validateBookInput([]).ok).toBe(false);
    expect(validateBookInput("Dune").ok).toBe(false);
  });

  it("rejects years outside the plausible range", () => {
    const result = validateBookInput({ title: "T", author: "A", year: 99999 });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors[0]?.field).toBe("year");
  });
});

describe("parseId", () => {
  it("accepts positive integers only", () => {
    expect(parseId("1")).toBe(1);
    expect(parseId("42")).toBe(42);
    expect(parseId("0")).toBeUndefined();
    expect(parseId("-1")).toBeUndefined();
    expect(parseId("1.5")).toBeUndefined();
    expect(parseId("abc")).toBeUndefined();
    expect(parseId(undefined)).toBeUndefined();
  });
});
