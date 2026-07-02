package soccer

import (
	"testing"
	"time"
)

func TestParseDateFormats(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want time.Time
	}{
		{
			name: "iso date with time",
			in:   "2012-05-19 18:30:00",
			want: time.Date(2012, 5, 19, 18, 30, 0, 0, time.UTC),
		},
		{
			name: "iso date only",
			in:   "2023-09-24",
			want: time.Date(2023, 9, 24, 0, 0, 0, 0, time.UTC),
		},
		{
			name: "brazilian date DD/MM/YYYY",
			in:   "29/03/2003",
			want: time.Date(2003, 3, 29, 0, 0, 0, 0, time.UTC),
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := ParseDate(tc.in)
			if err != nil {
				t.Fatalf("ParseDate(%q) returned error: %v", tc.in, err)
			}
			if !got.Equal(tc.want) {
				t.Errorf("ParseDate(%q) = %v, want %v", tc.in, got, tc.want)
			}
		})
	}
}

func TestParseDateInvalid(t *testing.T) {
	_, err := ParseDate("not-a-date")
	if err == nil {
		t.Fatal("expected error for invalid date, got nil")
	}
}
