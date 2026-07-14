package soccer

import (
	"strconv"
	"strings"
	"time"
)

// dateLayouts lists the formats found across the provided datasets, tried in
// order. The Brazilian DD/MM/YYYY format is handled separately below because
// time.Parse cannot disambiguate it from MM/DD/YYYY reliably here.
var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02",
}

// ParseDate parses a match date from any of the formats present in the
// datasets (ISO with or without time, and Brazilian DD/MM/YYYY). The second
// return value is false when the string cannot be parsed.
func ParseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, false
	}
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			return t, true
		}
	}
	// Brazilian DD/MM/YYYY.
	if t, err := time.Parse("02/01/2006", s); err == nil {
		return t, true
	}
	return time.Time{}, false
}

// itoa is a thin wrapper around strconv.Itoa used for building map keys.
func itoa(i int) string { return strconv.Itoa(i) }

// parseInt parses an integer, tolerating the trailing ".0" that the
// BR-Football dataset uses for goal counts.
func parseInt(s string) (int, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0, false
	}
	if i, err := strconv.Atoi(s); err == nil {
		return i, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}
