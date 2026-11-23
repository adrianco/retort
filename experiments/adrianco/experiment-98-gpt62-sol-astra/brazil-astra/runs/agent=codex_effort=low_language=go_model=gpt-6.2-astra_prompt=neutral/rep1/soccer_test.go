package main

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

func TestDatasetScenarios(t *testing.T) {
	g, err := Load("data/kaggle")
	if err != nil {
		t.Fatal(err)
	}
	query := func(tool string, a Args) any {
		t.Helper()
		v, e := g.query(tool, a)
		if e != nil {
			t.Fatal(e)
		}
		return v
	}
	for i, n := range []int{6886, 4180, 1337, 1255, 10296} {
		t.Run(files[i], func(t *testing.T) {
			if p := query("matches", Args{Source: files[i]}).(Page); p.Total != n {
				t.Fatalf("source has %d fixtures, want %d", p.Total, n)
			}
		})
	}
	t.Run("When comparing Flamengo and Fluminense both venues appear", func(t *testing.T) {
		p := query("matches", Args{Team: "Flamengo-RJ", Opponent: "Fluminense", Season: "2019", Competition: "Brasileirão"}).(Page)
		ms := p.Items.([]*Match)
		if len(ms) != 2 || ms[0].Home == ms[1].Home || ms[0].HomeGoals == nil || ms[0].Date < ms[1].Date {
			t.Fatal(ms)
		}
	})
	t.Run("When ranking the 2019 league Flamengo wins with 90 points", func(t *testing.T) {
		a := Args{Season: "2019", Competition: "Brasileirão"}
		s := query("summary", a).(map[string]any)
		if s["played"] != 380 {
			t.Fatal(s)
		}
		r := query("records", a).(Page).Items.([]*Record)[0]
		if r.Team != "flamengo" || r.Points != 90 || r.Wins != 28 || r.Draws != 6 || r.Losses != 4 || r.GoalsFor != 86 || r.GoalsAgainst != 37 {
			t.Fatal(r)
		}
	})
	t.Run("When requesting Corinthians home record only home matches count", func(t *testing.T) {
		r := query("records", Args{Team: "Sport Club Corinthians Paulista", Venue: "home", Competition: "Serie A", Season: "2022"}).(Page).Items.([]*Record)[0]
		if r.Played != 19 || r.Wins+r.Draws+r.Losses != 19 {
			t.Fatal(r)
		}
	})
	t.Run("When finding cup finals both legs are returned", func(t *testing.T) {
		for _, y := range []string{"2012", "2016", "2020", "2023"} {
			p := query("matches", Args{Competition: "Copa do Brasil", Stage: "final", Season: y}).(Page)
			if p.Total != 2 {
				t.Errorf("%s: %d", y, p.Total)
			}
		}
	})
	t.Run("When searching players ratings and attributes are available", func(t *testing.T) {
		if len(g.Players) != 18207 {
			t.Fatal(len(g.Players))
		}
		p := query("players", Args{Nationality: "Brazilian", Limit: 1}).(Page)
		r := p.Items.([]Row)[0]
		if r["Name"] != "Neymar Jr" || r["Dribbling"] == "" {
			t.Fatal(r)
		}
		p = query("players", Args{Club: "Grêmio"}).(Page)
		if p.Total != 20 {
			t.Fatal(p.Total)
		}
		club := p.Items.([]Row)[0]["Club"]
		if query("matches", Args{Team: club}).(Page).Total == 0 {
			t.Fatal(club)
		}
	})
	t.Run("When searching September derbies dates and rivals match", func(t *testing.T) {
		a := Args{Team: "Flamengo", Competition: "Copa do Brasil", Season: "2023", Start: "2023-09-01", End: "2023-09-30", Stage: "final"}
		p := query("matches", a).(Page)
		if p.Total != 2 {
			t.Fatal(p.Total)
		}
		a.Derbies = true
		if query("matches", a).(Page).Total != 0 {
			t.Fatal("São Paulo is not a listed Flamengo rival")
		}
		a = Args{Team: "Corinthians", Derbies: true, Season: "2019", Competition: "Serie A"}
		if query("matches", a).(Page).Total != 6 {
			t.Fatal("expected six league derby fixtures")
		}
	})
	t.Run("When paging the largest victories margins decrease", func(t *testing.T) {
		a := Args{Sort: "margin", Competition: "Libertadores", Limit: 2}
		p := query("matches", a).(Page)
		ms := p.Items.([]*Match)
		a.Offset = 1
		next := query("matches", a).(Page).Items.([]*Match)
		if ms[1] != next[0] {
			t.Fatal("inconsistent pages")
		}
		m := ms[0]
		if max(*m.HomeGoals-*m.AwayGoals, *m.AwayGoals-*m.HomeGoals) < 6 {
			t.Fatal(m)
		}
	})
	t.Run("When a score is missing the fixture counts only toward schedule totals", func(t *testing.T) {
		g := Graph{Matches: []*Match{{Home: "a", Away: "b"}}}
		v, _ := g.query("summary", Args{})
		s := v.(map[string]any)
		if s["played"] != 0 || s["fixtures"] != 1 || s["goalsPerMatch"] != nil {
			t.Fatal(s)
		}
	})
}

func TestStdioConversation(t *testing.T) {
	g := Graph{}
	var out bytes.Buffer
	in := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"summary","arguments":{}}}`,
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"matches","arguments":{"offset":-1}}}`}, "\n")
	if e := g.serve(strings.NewReader(in), &out); e != nil {
		t.Fatal(e)
	}
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	if len(lines) != 4 {
		t.Fatal(out.String())
	}
	for i, line := range lines {
		var v struct {
			ID            int
			Result, Error json.RawMessage
		}
		if json.Unmarshal([]byte(line), &v) != nil || v.ID != i+1 || (v.Error != nil) != (i == 3) {
			t.Fatal(line)
		}
	}
}
