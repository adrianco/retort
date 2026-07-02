package soccer

import (
	"fmt"
	"time"
)

// dateLayouts are the date/time formats found across the source datasets.
var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02",
	"02/01/2006",
}

// ParseDate parses a date string in any of the formats used by the source
// CSV files (ISO with or without time, or Brazilian DD/MM/YYYY), returning
// it in UTC.
func ParseDate(s string) (time.Time, error) {
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			return t.UTC(), nil
		}
	}
	return time.Time{}, fmt.Errorf("soccer: unrecognized date format: %q", s)
}
