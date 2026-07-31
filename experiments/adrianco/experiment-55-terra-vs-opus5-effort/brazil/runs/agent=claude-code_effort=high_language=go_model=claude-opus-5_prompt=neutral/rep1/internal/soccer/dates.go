// dates.go handles the several date encodings present in the datasets:
// ISO dates ("2023-09-24"), ISO date-times ("2012-05-19 18:30:00") and
// Brazilian day-first dates ("29/03/2003").
package soccer

import (
	"fmt"
	"strings"
	"time"
)

var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05Z07:00",
	"2006-01-02T15:04:05",
	"2006-01-02 15:04",
	"2006-01-02",
	"02/01/2006 15:04:05",
	"02/01/2006 15:04",
	"02/01/2006",
	"02-01-2006",
	"2006/01/02",
	"Jan 2, 2006",
}

// ParseDate parses any of the date formats used by the datasets. The second
// return value reports whether a time-of-day component was present.
func ParseDate(s string) (t time.Time, hasTime bool, err error) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, false, fmt.Errorf("empty date")
	}
	for _, layout := range dateLayouts {
		if v, err := time.Parse(layout, s); err == nil {
			// "15" is Go's reference hour; its presence means the layout, and
			// therefore the input, carried a time of day.
			return v, strings.Contains(layout, "15"), nil
		}
	}
	return time.Time{}, false, fmt.Errorf("unrecognised date format: %q", s)
}

// ParseDateOnly parses a user-supplied filter bound, accepting the same set of
// layouts plus a bare year ("2019").
func ParseDateOnly(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	if len(s) == 4 {
		if v, err := time.Parse("2006", s); err == nil {
			return v, nil
		}
	}
	t, _, err := ParseDate(s)
	return t, err
}

// FormatDate renders a match date in ISO form for output.
func FormatDate(t time.Time) string {
	if t.IsZero() {
		return ""
	}
	return t.Format("2006-01-02")
}
