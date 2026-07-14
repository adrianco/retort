package main

import (
	"strconv"
	"strings"
	"time"
)

var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05",
	"2006-01-02",
	"02/01/2006",
	"02/01/2006 15:04:05",
}

// parseDateFlexible tries a handful of layouts seen across the source CSVs
// (ISO with/without time, and Brazilian DD/MM/YYYY) and returns ok=false if
// none apply.
func parseDateFlexible(raw string) (time.Time, bool) {
	s := strings.TrimSpace(raw)
	if s == "" || strings.EqualFold(s, "NA") {
		return time.Time{}, false
	}
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

// combineDateTime merges a separate date-only string with a time-only string
// (used by BR-Football-Dataset.csv, which stores "date" and "time" columns
// independently).
func combineDateTime(dateRaw, timeRaw string) (time.Time, bool) {
	d, ok := parseDateFlexible(dateRaw)
	if !ok {
		return time.Time{}, false
	}
	t := strings.TrimSpace(timeRaw)
	if t == "" {
		return d, true
	}
	if parsed, err := time.Parse("15:04:05", t); err == nil {
		return time.Date(d.Year(), d.Month(), d.Day(), parsed.Hour(), parsed.Minute(), parsed.Second(), 0, time.UTC), true
	}
	return d, true
}

// parseGoal parses a goal-count value that may be rendered as "2", "2.0",
// quoted, blank or "NA" across the different datasets.
func parseGoal(raw string) (int, bool) {
	s := strings.TrimSpace(strings.Trim(raw, `"`))
	if s == "" || strings.EqualFold(s, "NA") {
		return 0, false
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}

func parseIntLoose(raw string) (int, bool) {
	s := strings.TrimSpace(raw)
	if s == "" || strings.EqualFold(s, "NA") {
		return 0, false
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}

func parseFloatLoose(raw string) (float64, bool) {
	s := strings.TrimSpace(raw)
	if s == "" || strings.EqualFold(s, "NA") {
		return 0, false
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return f, true
	}
	return 0, false
}
