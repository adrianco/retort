package soccer

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

// TestParseDateHandlesEveryFormat covers the "Date Formats" data quality note.
func TestParseDateHandlesEveryFormat(t *testing.T) {
	cases := []struct {
		in    string
		want  string
		clock string
	}{
		{"2023-09-24", "2023-09-24", ""},
		{"2012-05-19 18:30:00", "2012-05-19", "18:30"},
		{"29/03/2003", "2003-03-29", ""},
		{"31/12/2019", "2019-12-31", ""},
		{`"2013-02-12 20:15:00"`, "2013-02-12", "20:15"},
		{"2012-03-07 16:00:00", "2012-03-07", "16:00"},
	}
	for _, c := range cases {
		got, clock, err := parseDate(c.in)
		if err != nil {
			t.Errorf("parseDate(%q): %v", c.in, err)
			continue
		}
		if got.Format("2006-01-02") != c.want {
			t.Errorf("parseDate(%q) = %s, want %s", c.in, got.Format("2006-01-02"), c.want)
		}
		if clock != c.clock {
			t.Errorf("parseDate(%q) clock = %q, want %q", c.in, clock, c.clock)
		}
		if got.Location() != time.UTC {
			t.Errorf("parseDate(%q) should normalise to UTC", c.in)
		}
	}
	// Brazilian day-first must not be misread as month-first.
	d, _, err := parseDate("05/11/2003")
	if err != nil {
		t.Fatal(err)
	}
	if d.Month() != time.November || d.Day() != 5 {
		t.Errorf("parseDate(05/11/2003) = %s, want 2003-11-05 (day first)", d.Format("2006-01-02"))
	}

	for _, bad := range []string{"", "   ", "not a date", "13/13/2020"} {
		if _, _, err := parseDate(bad); err == nil {
			t.Errorf("parseDate(%q) should fail", bad)
		}
	}
}

func TestParseIntTolerance(t *testing.T) {
	cases := []struct {
		in   string
		want int
		ok   bool
	}{
		{"3", 3, true},
		{`"2"`, 2, true},
		{"1.0", 1, true}, // BR-Football writes floats
		{"104.0", 104, true},
		{" 7 ", 7, true},
		{"0", 0, true},
		{"", 0, false},
		{"NA", 0, false}, // abandoned fixtures
		{"-", 0, false},
	}
	for _, c := range cases {
		got, ok := parseInt(c.in)
		if got != c.want || ok != c.ok {
			t.Errorf("parseInt(%q) = (%d, %v), want (%d, %v)", c.in, got, ok, c.want, c.ok)
		}
	}
}

// TestReadCSVStripsBOM guards the fifa_data.csv leading byte order mark, which
// would otherwise corrupt the first column name.
func TestReadCSVStripsBOM(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "bom.csv")
	content := "\xEF\xBB\xBFID,Name,Club\n1,Neymar,PSG\n"
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
	idx, rows, err := readCSV(path)
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := idx["ID"]; !ok {
		t.Errorf("BOM not stripped: header keys are %v", idx)
	}
	if len(rows) != 1 || rows[0][1] != "Neymar" {
		t.Errorf("unexpected rows %v", rows)
	}
}

func TestReadCSVToleratesRaggedRows(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "ragged.csv")
	content := "a,b,c\n1,2,3\n4,5\n6,7,8,9\n"
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
	idx, rows, err := readCSV(path)
	if err != nil {
		t.Fatalf("ragged rows should not abort the read: %v", err)
	}
	if len(rows) != 3 {
		t.Fatalf("got %d rows, want 3", len(rows))
	}
	// A short row must read as empty rather than panicking.
	if got := (row{idx: idx, rec: rows[1]}).get("c"); got != "" {
		t.Errorf("short row column c = %q, want empty", got)
	}
}

// TestDedupKeySeparatesLegs checks that a two-legged cup tie is not collapsed
// into one match while a league fixture recorded twice is.
func TestDedupKeySeparatesLegs(t *testing.T) {
	mk := func(comp string, month int, home, away string) Match {
		return Match{
			Competition: comp, Season: 2019,
			Date: time.Date(2019, time.Month(month), 10, 0, 0, 0, 0, time.UTC),
			Home: TeamRef{ID: home}, Away: TeamRef{ID: away},
		}
	}
	// Same league fixture from two files, dates a day apart.
	a := mk(SerieA, 5, "flamengo", "santos")
	b := mk(SerieA, 5, "flamengo", "santos")
	b.Date = b.Date.AddDate(0, 0, 1)
	if dedupKey(a) != dedupKey(b) {
		t.Error("league fixtures a day apart should share a dedup key")
	}
	// Reversed fixture is a different match.
	if dedupKey(a) == dedupKey(mk(SerieA, 5, "santos", "flamengo")) {
		t.Error("home and away legs of a league season must stay distinct")
	}
	// Cup ties in different months are separate matches.
	if dedupKey(mk(CopaDoBrasil, 5, "flamengo", "santos")) ==
		dedupKey(mk(CopaDoBrasil, 8, "flamengo", "santos")) {
		t.Error("cup replays in different months must stay distinct")
	}
}

func TestMergeIntoFillsGapsOnly(t *testing.T) {
	dst := Match{Round: "22", Sources: []string{FileBrasileirao}}
	src := Match{
		Round: "ignored", Venue: "Maracanã", KickOff: "16:00",
		Stats:   &MatchStats{HomeShots: 12},
		Sources: []string{FileExtended},
	}
	mergeInto(&dst, src)
	if dst.Round != "22" {
		t.Errorf("existing round overwritten: %q", dst.Round)
	}
	if dst.Venue != "Maracanã" || dst.KickOff != "16:00" {
		t.Errorf("gaps not filled: %+v", dst)
	}
	if dst.Stats == nil || dst.Stats.HomeShots != 12 {
		t.Errorf("stats not merged: %+v", dst.Stats)
	}
	if len(dst.Sources) != 2 {
		t.Errorf("sources = %v, want both files", dst.Sources)
	}
	// Merging the same source twice must not duplicate it.
	mergeInto(&dst, src)
	if len(dst.Sources) != 2 {
		t.Errorf("sources duplicated: %v", dst.Sources)
	}
}

func TestLabelCupStages(t *testing.T) {
	// 2012 ended at round 6, 2018 at round 8, 2021 stopped at round 4.
	matches := []Match{
		{Season: 2012, Round: "6"}, {Season: 2012, Round: "6"},
		{Season: 2012, Round: "5"}, {Season: 2012, Round: "1"},
		{Season: 2018, Round: "8"}, {Season: 2018, Round: "8"},
		{Season: 2018, Round: "7"}, {Season: 2018, Round: "6"}, {Season: 2018, Round: "5"},
		{Season: 2021, Round: "4"}, {Season: 2021, Round: "4"},
		{Season: 2021, Round: "4"}, {Season: 2021, Round: "3"},
	}
	labelCupStages(matches)
	want := []string{
		"Final", "Final", "Semi-final", "Round 1",
		"Final", "Final", "Semi-final", "Quarter-final", "Round of 16",
		"Round 4", "Round 4", "Round 4", "Round 3", // 2021 never reached a final
	}
	for i, w := range want {
		if matches[i].Stage != w {
			t.Errorf("match %d (season %d round %s) stage = %q, want %q",
				i, matches[i].Season, matches[i].Round, matches[i].Stage, w)
		}
	}
}

func TestMatchHelpers(t *testing.T) {
	m := Match{Home: TeamRef{ID: "flamengo"}, Away: TeamRef{ID: "santos"}, HomeGoals: 2, AwayGoals: 1}
	if m.Result() != "home" || m.Winner() != "flamengo" || m.TotalGoals() != 3 {
		t.Errorf("home win misread: %+v", m)
	}
	m.HomeGoals, m.AwayGoals = 1, 1
	if m.Result() != "draw" || m.Winner() != "" {
		t.Errorf("draw misread")
	}
	m.AwayGoals = 3
	if m.Result() != "away" || m.Winner() != "santos" {
		t.Errorf("away win misread")
	}
	if !m.Involves("santos") || m.Involves("palmeiras") {
		t.Errorf("Involves is wrong")
	}
}

func TestLoadMissingDirectory(t *testing.T) {
	if _, err := Load(filepath.Join(t.TempDir(), "nope")); err == nil {
		t.Error("loading a missing directory should fail")
	}
}
