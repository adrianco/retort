package main

import (
	"fmt"
	"strings"
	"time"
)

// dateLayouts lists every date/time layout observed across the provided
// datasets, tried in order until one succeeds.
var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05",
	"2006-01-02",
	"02/01/2006 15:04:05",
	"02/01/2006",
}

// ParseFlexibleDate attempts to parse a date string that may be in any of
// the formats used by the source CSV files: ISO with time
// ("2012-05-19 18:30:00"), ISO date only ("2023-09-24"), or Brazilian
// day/month/year ("29/03/2003").
func ParseFlexibleDate(raw string) (time.Time, error) {
	s := strings.TrimSpace(raw)
	if s == "" {
		return time.Time{}, fmt.Errorf("empty date string")
	}
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("unrecognized date format: %q", raw)
}
