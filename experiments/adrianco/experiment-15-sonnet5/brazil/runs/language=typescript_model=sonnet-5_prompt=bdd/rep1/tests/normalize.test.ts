import { describe, expect, it } from "vitest";
import { formatDate, normalizeTeamName, parseFlexibleDate, parseIntLoose, parseNumber } from "../src/data/normalize.js";

describe("normalizeTeamName", () => {
  it("test_given_state_suffixed_name_when_normalized_then_state_is_stripped", () => {
    // Given a team name with a Brazilian-state suffix as used in Brasileirao_Matches.csv
    const raw = "Palmeiras-SP";
    // When normalizing the team name
    const result = normalizeTeamName(raw);
    // Then the state suffix is removed from the display name
    expect(result.displayName).toBe("Palmeiras");
  });

  it("test_given_accented_and_unaccented_spellings_when_normalized_then_they_share_a_key", () => {
    // Given the same club spelled with and without diacritics, as happens across datasets
    const withAccent = normalizeTeamName("São Paulo");
    const withoutAccent = normalizeTeamName("Sao Paulo");
    // When normalizing both spellings
    // Then they resolve to the same lookup key
    expect(withAccent.teamKey).toBe(withoutAccent.teamKey);
  });

  it("test_given_state_qualified_ambiguous_clubs_when_normalized_then_they_remain_distinct", () => {
    // Given two different clubs that share a name stem but are disambiguated only by state
    const mineiro = normalizeTeamName("Atlético-MG");
    const paranaense = normalizeTeamName("Athletico-PR");
    // When normalizing both
    // Then they resolve to different canonical clubs rather than being collapsed together
    expect(mineiro.teamKey).not.toBe(paranaense.teamKey);
    expect(mineiro.displayName).toBe("Atlético Mineiro");
    expect(paranaense.displayName).toBe("Athletico Paranaense");
  });

  it("test_given_legal_long_form_name_when_normalized_then_it_matches_the_short_form", () => {
    // Given a legal long-form club name as used in some source files
    const longForm = normalizeTeamName("Sport Club Corinthians Paulista");
    const shortForm = normalizeTeamName("Corinthians");
    // When normalizing both forms
    // Then they resolve to the same team key
    expect(longForm.teamKey).toBe(shortForm.teamKey);
  });

  it("test_given_name_with_parenthetical_note_when_normalized_then_note_is_removed", () => {
    // Given a club name with a parenthetical aside, as seen in Brazilian_Cup_Matches.csv
    const raw = "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ";
    // When normalizing the team name
    const result = normalizeTeamName(raw);
    // Then the parenthetical note and state suffix are both stripped, with no stray punctuation left behind
    expect(result.displayName).toBe("Boavista Sport Club");
  });

  it("test_given_foreign_country_suffix_when_normalized_then_suffix_is_stripped", () => {
    // Given a non-Brazilian club with a parenthetical country code, as seen in Libertadores_Matches.csv
    const raw = "Nacional (URU)";
    // When normalizing the team name
    const result = normalizeTeamName(raw);
    // Then the country code is removed
    expect(result.displayName).toBe("Nacional");
  });

  it("test_given_ordinary_club_name_ending_in_a_non_code_word_when_normalized_then_it_is_left_untouched", () => {
    // Given a club name that happens to end in a short word which is NOT a recognized state/country code
    const raw = "Aparecidense GO";
    // When normalizing the team name
    const result = normalizeTeamName(raw);
    // Then the recognized state code is still stripped (GO = Goiás), proving the whitelist actually matches
    expect(result.displayName).toBe("Aparecidense");
  });
});

describe("parseFlexibleDate", () => {
  it("test_given_brazilian_date_format_when_parsed_then_year_month_day_are_correct", () => {
    // Given a date in Brazilian DD/MM/YYYY format, as used in novo_campeonato_brasileiro.csv
    const raw = "29/03/2003";
    // When parsing the date
    const date = parseFlexibleDate(raw);
    // Then it is interpreted as 29 March 2003, not 3 April 1929 or similar
    expect(formatDate(date)).toBe("2003-03-29");
  });

  it("test_given_iso_date_with_time_when_parsed_then_date_portion_is_correct", () => {
    // Given an ISO datetime string, as used in Brasileirao_Matches.csv
    const raw = "2012-05-19 18:30:00";
    // When parsing the date
    const date = parseFlexibleDate(raw);
    // Then the date portion is extracted correctly
    expect(formatDate(date)).toBe("2012-05-19");
  });

  it("test_given_iso_date_only_when_parsed_then_it_is_accepted", () => {
    // Given a bare ISO date, as used in BR-Football-Dataset.csv
    const raw = "2023-09-24";
    // When parsing the date
    const date = parseFlexibleDate(raw);
    // Then it parses without needing a time component
    expect(formatDate(date)).toBe("2023-09-24");
  });

  it("test_given_separate_date_and_time_fields_when_parsed_then_they_combine", () => {
    // Given a date and a separate time field, as BR-Football-Dataset.csv provides them
    const date = parseFlexibleDate("2012-05-19", "18:30:00");
    // When combining them during parsing
    // Then the resulting date reflects both fields
    expect(date?.toISOString()).toBe("2012-05-19T18:30:00.000Z");
  });

  it("test_given_unparseable_date_when_parsed_then_null_is_returned", () => {
    // Given a placeholder value that isn't a real date (seen as "NA" in Libertadores_Matches.csv)
    const raw = "NA";
    // When parsing the date
    const date = parseFlexibleDate(raw);
    // Then parsing fails gracefully instead of throwing
    expect(date).toBeNull();
  });
});

describe("parseIntLoose", () => {
  it("test_given_float_formatted_integer_when_parsed_then_it_rounds_to_an_integer", () => {
    // Given a goals column value formatted as a float, as seen in BR-Football-Dataset.csv ("1.0")
    const raw = "1.0";
    // When parsing it as a loose integer
    const value = parseIntLoose(raw);
    // Then it is returned as the integer 1
    expect(value).toBe(1);
  });

  it("test_given_empty_string_when_parsed_then_null_is_returned", () => {
    // Given an empty CSV cell
    const raw = "";
    // When parsing it as a loose integer
    const value = parseIntLoose(raw);
    // Then null is returned rather than 0 or NaN
    expect(value).toBeNull();
  });
});

describe("parseNumber", () => {
  it("test_given_undefined_input_when_parsed_then_null_is_returned", () => {
    // Given a missing column value
    // When parsing it as a number
    const value = parseNumber(undefined);
    // Then null is returned
    expect(value).toBeNull();
  });
});
