package soccer

import "testing"

func TestParseDate(t *testing.T) {
	cases := []struct {
		in                  string
		wantY, wantM, wantD int
		wantOK              bool
	}{
		{"2012-05-19 18:30:00", 2012, 5, 19, true},
		{"2023-09-24", 2023, 9, 24, true},
		{"29/03/2003", 2003, 3, 29, true},
		{"2013-02-12 20:15:00", 2013, 2, 12, true},
		{"", 0, 0, 0, false},
		{"not-a-date", 0, 0, 0, false},
	}
	for _, c := range cases {
		got, ok := ParseDate(c.in)
		if ok != c.wantOK {
			t.Errorf("ParseDate(%q) ok = %v, want %v", c.in, ok, c.wantOK)
			continue
		}
		if !ok {
			continue
		}
		if got.Year() != c.wantY || int(got.Month()) != c.wantM || got.Day() != c.wantD {
			t.Errorf("ParseDate(%q) = %v, want %d-%02d-%02d", c.in, got, c.wantY, c.wantM, c.wantD)
		}
	}
}

func TestParseInt(t *testing.T) {
	cases := []struct {
		in   string
		want int
		ok   bool
	}{
		{"3", 3, true},
		{"0", 0, true},
		{"2.0", 2, true}, // BR-Football stores goals as floats
		{"5.0", 5, true},
		{"", 0, false},
		{"x", 0, false},
	}
	for _, c := range cases {
		got, ok := parseInt(c.in)
		if got != c.want || ok != c.ok {
			t.Errorf("parseInt(%q) = (%d,%v), want (%d,%v)", c.in, got, ok, c.want, c.ok)
		}
	}
}
