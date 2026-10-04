package drivers

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

// RecordsStub writes the records a spec describes into the same files, in
// the same formats, as the provided Kaggle datasets, and starts a private
// instance of the system over them. It translates; it does not simulate.
type RecordsStub struct {
	t       *testing.T
	dir     string
	matches []MatchRecord
	players []PlayerRecord
}

func NewRecordsStub(t *testing.T) *RecordsStub {
	return &RecordsStub{t: t, dir: t.TempDir()}
}

func (r *RecordsStub) AddMatch(m MatchRecord)   { r.matches = append(r.matches, m) }
func (r *RecordsStub) AddPlayer(p PlayerRecord) { r.players = append(r.players, p) }

// StartSystem writes the datasets and starts the system over them.
func (r *RecordsStub) StartSystem(t *testing.T) *Connection {
	t.Helper()
	if err := r.writeDatasets(); err != nil {
		t.Fatalf("could not write the records: %v", err)
	}
	conn, err := StartConnection(r.dir)
	if err != nil {
		t.Fatalf("the soccer knowledge system did not start: %v", err)
	}
	t.Cleanup(conn.Close)
	return conn
}

// datasetFiles maps the domain name of each dataset to its file.
var datasetFiles = map[string]string{
	"brasileirão results":    "Brasileirao_Matches.csv",
	"copa do brasil results": "Brazilian_Cup_Matches.csv",
	"libertadores results":   "Libertadores_Matches.csv",
	"extended statistics":    "BR-Football-Dataset.csv",
	"historical brasileirão": "novo_campeonato_brasileiro.csv",
	"fifa player ratings":    "fifa_data.csv",
}

func datasetFile(name string) string {
	return datasetFiles[strings.ToLower(strings.TrimSpace(name))]
}

func (r *RecordsStub) writeDatasets() error {
	rows := map[string][][]string{}
	for _, m := range r.matches {
		file := datasetFile(m.Source)
		if file == "" {
			return fmt.Errorf("no dataset called %q", m.Source)
		}
		rows[file] = append(rows[file], matchRow(file, m, len(rows[file])+1))
	}
	for _, p := range r.players {
		rows["fifa_data.csv"] = append(rows["fifa_data.csv"], playerRow(p, len(rows["fifa_data.csv"])))
	}
	for file, header := range headers {
		if err := writeCSV(filepath.Join(r.dir, file), header, rows[file]); err != nil {
			return err
		}
	}
	return nil
}

var headers = map[string][]string{
	"Brasileirao_Matches.csv":        {"datetime", "home_team", "home_team_state", "away_team", "away_team_state", "home_goal", "away_goal", "season", "round"},
	"Brazilian_Cup_Matches.csv":      {"round", "datetime", "home_team", "away_team", "home_goal", "away_goal", "season"},
	"Libertadores_Matches.csv":       {"datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "stage"},
	"BR-Football-Dataset.csv":        {"tournament", "home", "home_goal", "away_goal", "away", "home_corner", "away_corner", "home_attack", "away_attack", "home_shots", "away_shots", "time", "date", "ht_diff", "at_diff", "ht_result", "at_result", "total_corners"},
	"novo_campeonato_brasileiro.csv": {"ID", "Data", "Ano", "Rodada", "Equipe_mandante", "Equipe_visitante", "Gols_mandante", "Gols_visitante", "Mandante_UF", "Visitante_UF", "Vencedor", "Arena", "OBS"},
	"fifa_data.csv":                  strings.Split(",ID,Name,Age,Photo,Nationality,Flag,Overall,Potential,Club,Club Logo,Value,Wage,Special,Preferred Foot,International Reputation,Weak Foot,Skill Moves,Work Rate,Body Type,Real Face,Position,Jersey Number,Joined,Loaned From,Contract Valid Until,Height,Weight,LS,ST,RS,LW,LF,CF,RF,RW,LAM,CAM,RAM,LM,LCM,CM,RCM,RM,LWB,LDM,CDM,RDM,RWB,LB,LCB,CB,RCB,RB,Crossing,Finishing,HeadingAccuracy,ShortPassing,Volleys,Dribbling,Curve,FKAccuracy,LongPassing,BallControl,Acceleration,SprintSpeed,Agility,Reactions,Balance,ShotPower,Jumping,Stamina,Strength,LongShots,Aggression,Interceptions,Positioning,Vision,Penalties,Composure,Marking,StandingTackle,SlidingTackle,GKDiving,GKHandling,GKKicking,GKPositioning,GKReflexes,Release Clause", ","),
}

func matchRow(file string, m MatchRecord, seq int) []string {
	hg, ag := strconv.Itoa(m.HomeGoals), strconv.Itoa(m.AwayGoals)
	if !m.ScoreKnown {
		hg, ag = "NA", "NA"
	}
	datetime := m.Date.Format("2006-01-02") + " 16:00:00"
	season := strconv.Itoa(m.Season)
	switch file {
	case "Brasileirao_Matches.csv":
		return []string{datetime, m.Home, stateOf(m.Home), m.Away, stateOf(m.Away), hg, ag, season, strconv.Itoa(m.Round)}
	case "Brazilian_Cup_Matches.csv":
		return []string{strconv.Itoa(m.Round), datetime, m.Home, m.Away, hg, ag, season}
	case "Libertadores_Matches.csv":
		return []string{datetime, m.Home, m.Away, hg, ag, season, m.Stage}
	case "BR-Football-Dataset.csv":
		tournament := map[string]string{"Brasileirão": "Serie A", "Série B": "Serie B", "Série C": "Serie C", "Copa do Brasil": "Copa do Brasil"}[m.Competition]
		f := func(n int) string { return strconv.Itoa(n) + ".0" }
		hgf, agf := f(m.HomeGoals), f(m.AwayGoals)
		if !m.ScoreKnown {
			hgf, agf = "", ""
		}
		stat := func(n int) string {
			if !m.HasStats {
				return ""
			}
			return f(n)
		}
		total := ""
		if m.HasStats {
			total = f(m.Corners[0] + m.Corners[1])
		}
		return []string{tournament, m.Home, hgf, agf, m.Away, stat(m.Corners[0]), stat(m.Corners[1]), "", "", stat(m.Shots[0]), stat(m.Shots[1]),
			"16:00:00", m.Date.Format("2006-01-02"), "", "", "", "", total}
	default: // historical Brasileirão
		winner := "Empate"
		if m.HomeGoals > m.AwayGoals {
			winner = "Mandante"
		} else if m.AwayGoals > m.HomeGoals {
			winner = "Visitante"
		}
		return []string{fmt.Sprintf("%d.01.%04d", m.Season, seq), m.Date.Format("02/01/2006"), season, strconv.Itoa(m.Round),
			m.Home, m.Away, hg, ag, stateOf(m.Home), stateOf(m.Away), winner, "Estádio de Teste", ""}
	}
}

func playerRow(p PlayerRecord, index int) []string {
	row := make([]string, len(headers["fifa_data.csv"]))
	set := func(col, v string) {
		for i, h := range headers["fifa_data.csv"] {
			if h == col {
				row[i] = v
			}
		}
	}
	set("", strconv.Itoa(index))
	set("ID", strconv.Itoa(p.ID))
	set("Name", p.Name)
	set("Age", strconv.Itoa(p.Age))
	set("Nationality", p.Nationality)
	set("Overall", strconv.Itoa(p.Overall))
	set("Potential", strconv.Itoa(p.Overall))
	set("Club", p.Club)
	set("Position", p.Position)
	set("Jersey Number", "10")
	set("Height", "5'10")
	set("Weight", "165lbs")
	set("Preferred Foot", "Right")
	set("Value", "€1M")
	return row
}

func stateOf(team string) string {
	if i := strings.LastIndex(team, "-"); i >= 0 && len(team)-i == 3 {
		return team[i+1:]
	}
	return ""
}

func writeCSV(path string, header []string, rows [][]string) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()
	w := csv.NewWriter(f)
	w.Write(header)
	w.WriteAll(rows)
	return w.Error()
}
