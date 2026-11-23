package main

import (
	"cmp"
	"slices"
	"strings"
	"time"
)

type pairing struct{ competition, home, away string }

func (m Match) pairing() pairing {
	return pairing{m.Competition, m.homeKey, m.awayKey}
}

func newest(a, b Match) int {
	if order := cmp.Compare(b.Date, a.Date); order != 0 {
		return order
	}
	return cmp.Compare(b.Kickoff, a.Kickoff)
}

func nearbyDates(date string) []string {
	t, err := parseDate(date)
	if err != nil {
		return []string{date}
	}
	return []string{date, t.AddDate(0, 0, -1).Format(time.DateOnly), t.AddDate(0, 0, 1).Format(time.DateOnly)}
}

func (s *Store) reconcileMatches() {
	cupFinalRounds := make(map[int]int)
	for _, m := range s.bySource[cupFile] {
		cupFinalRounds[m.Season] = max(cupFinalRounds[m.Season], number(m.Round))
	}
	// The dedicated cup file ends in the early rounds of the 2021 edition.
	delete(cupFinalRounds, 2021)
	for i, m := range s.bySource[cupFile] {
		if number(m.Round) == cupFinalRounds[m.Season] {
			s.bySource[cupFile][i].Stage = "final"
		}
	}

	for season := 2021; season <= 2023; season++ {
		var last []int
		for i, m := range s.bySource[extendedFile] {
			if m.Competition == cup && m.Season == season {
				last = append(last, i)
			}
		}
		slices.SortStableFunc(last, func(a, b int) int {
			return newest(s.bySource[extendedFile][a], s.bySource[extendedFile][b])
		})
		if len(last) >= 2 {
			a, b := &s.bySource[extendedFile][last[0]], &s.bySource[extendedFile][last[1]]
			if a.homeKey == b.awayKey && a.awayKey == b.homeKey {
				a.Stage, b.Stage = "final", "final"
			}
		}
	}

	// The dedicated league file supplies the participant lists for its editions.
	leagueTeams := make(map[int]map[string]bool)
	for _, m := range s.bySource[leagueFile] {
		if leagueTeams[m.Season] == nil {
			leagueTeams[m.Season] = make(map[string]bool)
		}
		leagueTeams[m.Season][m.homeKey], leagueTeams[m.Season][m.awayKey] = true, true
	}

	index := make(map[pairing][]int)
	for _, file := range []string{leagueFile, historyFile, cupFile, libertadoresFile, extendedFile} {
		for i, m := range s.bySource[file] {
			key := m.pairing()
			found := -1
			if file == extendedFile {
				// Extended timestamps can cross midnight relative to the other sources.
				for _, date := range nearbyDates(m.Date) {
					for _, j := range index[key] {
						if s.matches[j].Date == date && date != "" {
							found = j
							break
						}
					}
					if found >= 0 {
						break
					}
				}
			}
			if found < 0 && (m.Competition == serieA || m.Competition == serieB) && m.Season > 0 {
				for _, j := range index[key] {
					if s.matches[j].Season == m.Season {
						found = j
						break
					}
				}
			}
			if found < 0 {
				if participants := leagueTeams[m.Season]; file == extendedFile && m.Competition == serieA &&
					participants != nil && (!participants[m.homeKey] || !participants[m.awayKey]) {
					// Keep conflicting competition labels available through source queries.
					continue
				}
				index[key] = append(index[key], len(s.matches))
				s.matches = append(s.matches, m)
				continue
			}
			first := &s.matches[found]
			if file == extendedFile && first.Season != m.Season {
				s.bySource[file][i].Season = first.Season
			}
			if !slices.Contains(first.Sources, file) {
				first.Sources = append(first.Sources, file)
			}
			if !first.played() && m.played() && file != historyFile {
				first.HomeGoals, first.AwayGoals = m.HomeGoals, m.AwayGoals
			}
			if first.HistoricalID == "" {
				first.HistoricalID = m.HistoricalID
			}
			if first.HomeState == "" {
				first.HomeState = m.HomeState
			}
			if first.AwayState == "" {
				first.AwayState = m.AwayState
			}
			if first.Stadium == "" {
				first.Stadium = m.Stadium
			}
			if first.Kickoff == "" {
				first.Kickoff = m.Kickoff
			}
			if first.Stage == "" {
				first.Stage = m.Stage
			}
			if len(first.Stats) == 0 {
				first.Stats = m.Stats
			}
			if file == extendedFile && first.Stage != "" && s.bySource[file][i].Stage == "" {
				s.bySource[file][i].Stage = first.Stage
			}
		}
	}
	slices.SortStableFunc(s.matches, newest)
	for _, matches := range s.bySource {
		slices.SortStableFunc(matches, newest)
	}
	slices.SortFunc(s.players, func(a, b Player) int {
		if order := cmp.Compare(b.Overall, a.Overall); order != 0 {
			return order
		}
		return cmp.Compare(a.ID, b.ID)
	})
}

var rivalries = [][]string{
	{"Flamengo", "Fluminense", "Botafogo-RJ", "Vasco da Gama"},
	{"Corinthians", "Palmeiras", "São Paulo", "Santos"},
	{"Atlético Mineiro", "Cruzeiro", "América-MG"},
	{"Grêmio", "Internacional"},
	{"Athletico Paranaense", "Coritiba", "Paraná"},
	{"Bahia", "Vitória"},
	{"Ceará", "Fortaleza"},
	{"Sport", "Náutico", "Santa Cruz"},
	{"Goiás", "Atlético Goianiense", "Vila Nova"},
	{"Avaí", "Figueirense"},
	{"Paysandu", "Remo"},
	{"Ponte Preta", "Guarani"},
	{"CSA", "CRB"},
}

func derby(m Match) bool {
	for _, group := range rivalries {
		home, away := false, false
		for _, club := range group {
			key := words(club)
			home = home || m.homeKey == key
			away = away || m.awayKey == key
		}
		if home && away {
			return true
		}
	}
	return false
}

func stageName(s string) string {
	switch words(s) {
	case "finals", "final":
		return "final"
	case "semi finals", "semi final", "semifinal", "semifinals":
		return "semifinals"
	case "quarterfinal", "quarterfinals", "quarter finals":
		return "quarterfinals"
	default:
		return strings.TrimSpace(strings.ToLower(s))
	}
}

func matchesStage(actual, requested string) bool {
	if requested == "knockout" {
		return slices.Contains([]string{"round of 16", "quarterfinals", "semifinals", "final"}, actual)
	}
	return actual == requested
}
