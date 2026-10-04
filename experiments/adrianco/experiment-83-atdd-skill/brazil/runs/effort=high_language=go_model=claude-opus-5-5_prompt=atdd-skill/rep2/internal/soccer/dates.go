package soccer

import (
	"strings"
	"time"
)

var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05",
	"2006-01-02 15:04",
	"2006-01-02",
	"02/01/2006 15:04",
	"02/01/2006",
	"2/1/2006",
}

// ParseDate understands the date formats used across the datasets: ISO
// ("2023-09-24"), Brazilian ("29/03/2003") and ISO with a time
// ("2012-05-19 18:30:00").
func ParseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}
