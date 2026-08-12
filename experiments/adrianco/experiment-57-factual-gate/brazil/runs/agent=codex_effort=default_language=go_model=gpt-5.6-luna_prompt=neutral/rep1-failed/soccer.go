package soccer

import (
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
	"unicode"
	"unicode/utf8"
)

type Match struct {
	Competition, Date, Home, Away, Stage, Round string
	Season, HomeGoals, AwayGoals                int
	HomeCorners, AwayCorners                    float64
}

type Player struct {
	ID, Name, Nationality, Club, Position string
	Age, Overall, Potential               int
}

type Store struct {
	Matches []Match
	Players []Player
}

type MatchFilter struct {
	Team, Opponent, Competition, From, To string
	Season                                int
	Limit                                 int
}
type TeamStats struct {
	Team, Competition                                            string
	Season, Matches, Wins, Draws, Losses, GoalsFor, GoalsAgainst int
	WinRate, Points                                              float64
}
type Standing struct {
	Team                                                        string
	Played, Wins, Draws, Losses, GoalsFor, GoalsAgainst, Points int
}
type PlayerFilter struct {
	Name, Nationality, Club, Position string
	MinOverall, Limit                 int
}

func normalize(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	// The CSVs mix precomposed Portuguese characters with ASCII spellings.
	s = strings.NewReplacer("á", "a", "à", "a", "ã", "a", "â", "a", "ä", "a", "é", "e", "ê", "e", "ë", "e", "í", "i", "ï", "i", "ó", "o", "ô", "o", "õ", "o", "ö", "o", "ú", "u", "ü", "u", "ç", "c").Replace(s)
	s = strings.ReplaceAll(s, "brazilian", "brasil")
	s = strings.ReplaceAll(s, "brazil", "brasil")
	var b strings.Builder
	for _, r := range s {
		if unicode.Is(unicode.Mn, r) {
			continue
		}
		b.WriteRune(r)
	}
	s = b.String()
	for _, sep := range []string{"-", "–", "—", "_", "."} {
		s = strings.ReplaceAll(s, sep, " ")
	}
	return strings.Join(strings.Fields(s), " ")
}
func teamKey(s string) string {
	s = normalize(s)
	if i := strings.LastIndex(s, " "); i > 0 && len(s)-i-1 == 2 {
		s = strings.TrimSpace(s[:i])
	}
	return s
}
func contains(hay, needle string) bool {
	return needle == "" || strings.Contains(normalize(hay), normalize(needle))
}
func intField(row map[string]string, keys ...string) int {
	for _, k := range keys {
		if v, ok := row[normalize(k)]; ok {
			n, _ := strconv.Atoi(strings.TrimSpace(v))
			return n
		}
	}
	return 0
}
func floatField(row map[string]string, keys ...string) float64 {
	for _, k := range keys {
		if v, ok := row[normalize(k)]; ok {
			n, _ := strconv.ParseFloat(strings.TrimSpace(v), 64)
			return n
		}
	}
	return 0
}
func get(row map[string]string, keys ...string) string {
	for _, k := range keys {
		if v, ok := row[normalize(k)]; ok {
			return strings.TrimSpace(v)
		}
	}
	return ""
}

func parseDate(s string) string {
	s = strings.TrimSpace(s)
	if s == "" {
		return ""
	}
	for _, layout := range []string{"2006-01-02 15:04:05", "2006-01-02", "02/01/2006", "02/01/2006 15:04:05", "2006/01/02"} {
		if t, e := time.Parse(layout, s); e == nil {
			return t.Format("2006-01-02")
		}
	}
	return s
}
func readCSV(path string) ([]map[string]string, error) {
	f, e := os.Open(path)
	if e != nil {
		return nil, e
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.FieldsPerRecord = -1
	head, e := r.Read()
	if e != nil {
		return nil, e
	}
	for i := range head {
		head[i] = strings.TrimPrefix(strings.TrimSpace(head[i]), "\ufeff")
	}
	var out []map[string]string
	for {
		rec, e := r.Read()
		if errors.Is(e, io.EOF) {
			break
		}
		if e != nil {
			continue
		}
		row := map[string]string{}
		for i, k := range head {
			if i < len(rec) {
				row[normalize(k)] = rec[i]
			}
		}
		out = append(out, row)
	}
	return out, nil
}

func Load(dataDir string) (*Store, error) {
	s := &Store{}
	matches := []struct{ name, competition string }{{"Brasileirao_Matches.csv", "Brasileirão"}, {"Brazilian_Cup_Matches.csv", "Copa do Brasil"}, {"Libertadores_Matches.csv", "Copa Libertadores"}, {"BR-Football-Dataset.csv", ""}, {"novo_campeonato_brasileiro.csv", "Brasileirão"}}
	for _, spec := range matches {
		rows, e := readCSV(filepath.Join(dataDir, spec.name))
		if e != nil {
			return nil, fmt.Errorf("load %s: %w", spec.name, e)
		}
		for _, r := range rows {
			comp := spec.competition
			if comp == "" {
				comp = get(r, "tournament")
			}
			home := get(r, "home team", "home", "equipe mandante")
			away := get(r, "away team", "away", "equipe visitante")
			if home == "" || away == "" {
				continue
			}
			season := intField(r, "season", "ano")
			date := parseDate(get(r, "datetime", "date", "data"))
			round := get(r, "round", "rodada")
			stage := get(r, "stage")
			s.Matches = append(s.Matches, Match{Competition: comp, Date: date, Home: home, Away: away, Stage: stage, Round: round, Season: season, HomeGoals: intField(r, "home goal", "home_goal", "gols mandante"), AwayGoals: intField(r, "away goal", "away_goal", "gols visitante"), HomeCorners: floatField(r, "home corner"), AwayCorners: floatField(r, "away corner")})
		}
	}
	rows, e := readCSV(filepath.Join(dataDir, "fifa_data.csv"))
	if e != nil {
		return nil, fmt.Errorf("load fifa_data.csv: %w", e)
	}
	for _, r := range rows {
		s.Players = append(s.Players, Player{ID: get(r, "id"), Name: get(r, "name"), Nationality: get(r, "nationality"), Club: get(r, "club"), Position: get(r, "position"), Age: intField(r, "age"), Overall: intField(r, "overall"), Potential: intField(r, "potential")})
	}
	return s, nil
}

func (s *Store) SearchMatches(f MatchFilter) []Match {
	out := []Match{}
	for _, m := range s.Matches {
		if f.Team != "" && teamKey(m.Home) != teamKey(f.Team) && teamKey(m.Away) != teamKey(f.Team) {
			continue
		}
		if f.Opponent != "" && !(teamKey(m.Home) == teamKey(f.Team) && teamKey(m.Away) == teamKey(f.Opponent) || teamKey(m.Home) == teamKey(f.Opponent) && teamKey(m.Away) == teamKey(f.Team)) {
			continue
		}
		if f.Competition != "" && !contains(m.Competition, f.Competition) {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if f.From != "" && m.Date < f.From {
			continue
		}
		if f.To != "" && m.Date > f.To {
			continue
		}
		out = append(out, m)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Date < out[j].Date })
	if f.Limit > 0 && len(out) > f.Limit {
		return out[len(out)-f.Limit:]
	}
	return out
}

func (s *Store) Stats(team, competition string, season int, homeOnly bool) TeamStats {
	st := TeamStats{Team: team, Competition: competition, Season: season}
	key := teamKey(team)
	for _, m := range s.Matches {
		if season != 0 && m.Season != season || competition != "" && !contains(m.Competition, competition) {
			continue
		}
		isHome := teamKey(m.Home) == key
		isAway := teamKey(m.Away) == key
		if !isHome && !isAway {
			continue
		}
		if homeOnly && !isHome {
			continue
		}
		st.Matches++
		if isHome {
			st.GoalsFor += m.HomeGoals
			st.GoalsAgainst += m.AwayGoals
			if m.HomeGoals > m.AwayGoals {
				st.Wins++
				st.Points += 3
			} else if m.HomeGoals == m.AwayGoals {
				st.Draws++
				st.Points++
			} else {
				st.Losses++
			}
		} else {
			st.GoalsFor += m.AwayGoals
			st.GoalsAgainst += m.HomeGoals
			if m.AwayGoals > m.HomeGoals {
				st.Wins++
				st.Points += 3
			} else if m.HomeGoals == m.AwayGoals {
				st.Draws++
				st.Points++
			} else {
				st.Losses++
			}
		}
	}
	if st.Matches > 0 {
		st.WinRate = float64(st.Wins) / float64(st.Matches) * 100
	}
	return st
}
func (s *Store) Standings(competition string, season int) []Standing {
	tab := map[string]*Standing{}
	for _, m := range s.Matches {
		if season != 0 && m.Season != season || competition != "" && !contains(m.Competition, competition) {
			continue
		}
		h, a := teamKey(m.Home), teamKey(m.Away)
		if tab[h] == nil {
			tab[h] = &Standing{Team: m.Home}
		}
		if tab[a] == nil {
			tab[a] = &Standing{Team: m.Away}
		}
		x, y := tab[h], tab[a]
		x.Played++
		y.Played++
		x.GoalsFor += m.HomeGoals
		x.GoalsAgainst += m.AwayGoals
		y.GoalsFor += m.AwayGoals
		y.GoalsAgainst += m.HomeGoals
		if m.HomeGoals > m.AwayGoals {
			x.Wins++
			x.Points += 3
			y.Losses++
		} else if m.HomeGoals < m.AwayGoals {
			y.Wins++
			y.Points += 3
			x.Losses++
		} else {
			x.Draws++
			y.Draws++
			x.Points++
			y.Points++
		}
	}
	out := []Standing{}
	for _, v := range tab {
		out = append(out, *v)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Points != out[j].Points {
			return out[i].Points > out[j].Points
		}
		return out[i].GoalsFor-out[i].GoalsAgainst > out[j].GoalsFor-out[j].GoalsAgainst
	})
	return out
}
func (s *Store) SearchPlayers(f PlayerFilter) []Player {
	out := []Player{}
	for _, p := range s.Players {
		if !contains(p.Name, f.Name) || !contains(p.Nationality, f.Nationality) || !contains(p.Club, f.Club) || !contains(p.Position, f.Position) || p.Overall < f.MinOverall {
			continue
		}
		out = append(out, p)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Overall > out[j].Overall })
	if f.Limit > 0 && len(out) > f.Limit {
		return out[:f.Limit]
	}
	return out
}
func (s *Store) AverageGoals(competition string, season int) float64 {
	total, n := 0, 0
	for _, m := range s.Matches {
		if season != 0 && m.Season != season || competition != "" && !contains(m.Competition, competition) {
			continue
		}
		total += m.HomeGoals + m.AwayGoals
		n++
	}
	if n == 0 {
		return 0
	}
	return float64(total) / float64(n)
}

var _ = utf8.RuneCountInString
