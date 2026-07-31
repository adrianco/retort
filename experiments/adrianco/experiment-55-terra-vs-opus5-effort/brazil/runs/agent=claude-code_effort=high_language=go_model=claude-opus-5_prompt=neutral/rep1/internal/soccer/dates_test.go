package soccer

import "testing"

func TestParseDateFormats(t *testing.T) {
	cases := []struct {
		in       string
		want     string
		wantTime bool
	}{
		{"2023-09-24", "2023-09-24", false},         // ISO, BR-Football
		{"2012-05-19 18:30:00", "2012-05-19", true}, // ISO with time, Brasileirão
		{"29/03/2003", "2003-03-29", false},         // Brazilian day-first, novo
		{"01/12/2019", "2019-12-01", false},         // day and month both valid: day wins
	}
	for _, c := range cases {
		got, hasTime, err := ParseDate(c.in)
		if err != nil {
			t.Fatalf("ParseDate(%q): %v", c.in, err)
		}
		if FormatDate(got) != c.want {
			t.Errorf("ParseDate(%q) = %s, want %s", c.in, FormatDate(got), c.want)
		}
		if hasTime != c.wantTime {
			t.Errorf("ParseDate(%q) hasTime = %v, want %v", c.in, hasTime, c.wantTime)
		}
	}
	if _, _, err := ParseDate("not a date"); err == nil {
		t.Error("expected an error for an unparseable date")
	}
}

func TestParseDateOnlyAcceptsBareYear(t *testing.T) {
	got, err := ParseDateOnly("2019")
	if err != nil {
		t.Fatalf("ParseDateOnly: %v", err)
	}
	if got.Year() != 2019 {
		t.Errorf("year = %d, want 2019", got.Year())
	}
}
