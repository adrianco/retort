import { describe, expect, it } from "vitest";
import { parseId, validateBookInput } from "../src/validation.js";

describe("validateBookInput", () => {
  it("accepts a minimal valid payload", () => {
    const result = validateBookInput({ title: "T", author: "A" });
    expect(result).toEqual({ ok: true, value: { title: "T", author: "A", year: null, isbn: null } });
  });

  it("accepts ISBN-10 with an X check digit and ISBN-13 with hyphens", () => {
    expect(validateBookInput({ title: "T", author: "A", isbn: "0-8044-2957-X" }).ok).toBe(true);
    expect(validateBookInput({ title: "T", author: "A", isbn: "9780306406157" }).ok).toBe(true);
  });

  it("treats an empty isbn string as null", () => {
    const result = validateBookInput({ title: "T", author: "A", isbn: "  " });
    expect(result.ok && result.value.isbn).toBeNull();
  });

  it("rejects years outside the supported range and non-integers", () => {
    expect(validateBookInput({ title: "T", author: "A", year: 1999.5 }).ok).toBe(false);
    expect(validateBookInput({ title: "T", author: "A", year: 99999 }).ok).toBe(false);
  });

  it("rejects non-object bodies", () => {
    for (const body of [null, undefined, "str", 42, []]) {
      const result = validateBookInput(body);
      expect(result.ok).toBe(false);
      expect(!result.ok && result.errors[0].field).toBe("body");
    }
  });
});

describe("parseId", () => {
  it("parses positive integers only", () => {
    expect(parseId("1")).toBe(1);
    expect(parseId("42")).toBe(42);
    expect(parseId("0")).toBeNull();
    expect(parseId("-1")).toBeNull();
    expect(parseId("1.5")).toBeNull();
    expect(parseId("abc")).toBeNull();
    expect(parseId("")).toBeNull();
  });
});
