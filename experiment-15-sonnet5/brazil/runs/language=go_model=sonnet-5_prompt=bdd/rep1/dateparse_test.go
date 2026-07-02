package main

import "testing"

func Test_GivenIsoDateWithTime_WhenParsing_ThenDateComponentsAreExtracted(t *testing.T) {
	// Given a datetime string in the format used by Brasileirao_Matches.csv
	raw := "2012-05-19 18:30:00"

	// When parsing it
	got, err := ParseFlexibleDate(raw)

	// Then the year, month and day are extracted correctly
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.Year() != 2012 || got.Month() != 5 || got.Day() != 19 {
		t.Errorf("got %v, want 2012-05-19", got)
	}
}

func Test_GivenIsoDateOnly_WhenParsing_ThenDateComponentsAreExtracted(t *testing.T) {
	// Given a plain ISO date string as used by BR-Football-Dataset.csv
	raw := "2023-09-24"

	// When parsing it
	got, err := ParseFlexibleDate(raw)

	// Then the year, month and day are extracted correctly
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.Year() != 2023 || got.Month() != 9 || got.Day() != 24 {
		t.Errorf("got %v, want 2023-09-24", got)
	}
}

func Test_GivenBrazilianDayMonthYearDate_WhenParsing_ThenDateComponentsAreExtracted(t *testing.T) {
	// Given a DD/MM/YYYY date string as used by novo_campeonato_brasileiro.csv
	raw := "29/03/2003"

	// When parsing it
	got, err := ParseFlexibleDate(raw)

	// Then the year, month and day are extracted correctly (not swapped)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.Year() != 2003 || got.Month() != 3 || got.Day() != 29 {
		t.Errorf("got %v, want 2003-03-29", got)
	}
}

func Test_GivenUnrecognizedDateFormat_WhenParsing_ThenAnErrorIsReturned(t *testing.T) {
	// Given a string that isn't a date in any known layout
	raw := "not-a-date"

	// When parsing it
	_, err := ParseFlexibleDate(raw)

	// Then an error is returned
	if err == nil {
		t.Error("expected an error, got nil")
	}
}

func Test_GivenEmptyDateString_WhenParsing_ThenAnErrorIsReturned(t *testing.T) {
	// Given an empty string
	raw := ""

	// When parsing it
	_, err := ParseFlexibleDate(raw)

	// Then an error is returned
	if err == nil {
		t.Error("expected an error, got nil")
	}
}
