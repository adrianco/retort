package driver

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
)

// The server reads the six provided CSV files from a data directory. For
// synthetic specs the driver writes those files itself, in the same
// layout as the provided data, holding only the facts the spec established.

const (
	serieAFile     = "Brasileirao_Matches.csv"
	cupFile        = "Brazilian_Cup_Matches.csv"
	libertadores   = "Libertadores_Matches.csv"
	extendedFile   = "BR-Football-Dataset.csv"
	historicalFile = "novo_campeonato_brasileiro.csv"
	playersFile    = "fifa_data.csv"
)

var fifaColumns = []string{"", "ID", "Name", "Age", "Photo", "Nationality", "Flag", "Overall", "Potential", "Club", "Club Logo", "Value", "Wage", "Special", "Preferred Foot", "International Reputation", "Weak Foot", "Skill Moves", "Work Rate", "Body Type", "Real Face", "Position", "Jersey Number", "Joined", "Loaned From", "Contract Valid Until", "Height", "Weight", "LS", "ST", "RS", "LW", "LF", "CF", "RF", "RW", "LAM", "CAM", "RAM", "LM", "LCM", "CM", "RCM", "RM", "LWB", "LDM", "CDM", "RDM", "RWB", "LB", "LCB", "CB", "RCB", "RB", "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance", "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression", "Interceptions", "Positioning", "Vision", "Penalties", "Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes", "Release Clause"}

var stateSuffix = regexp.MustCompile(`[\s-]+([A-Z]{2})$`)

func stateOf(team string) string {
	if m := stateSuffix.FindStringSubmatch(team); m != nil {
		return m[1]
	}
	return ""
}

type competitionKind int

const (
	serieA competitionKind = iota
	serieB
	serieC
	copaDoBrasil
	copaLibertadores
)

func kindOf(competition string) competitionKind {
	c := fold(competition)
	switch {
	case contains(c, "libertadores"):
		return copaLibertadores
	case contains(c, "copa do brasil"), contains(c, "brazil cup"):
		return copaDoBrasil
	case contains(c, "serie b"):
		return serieB
	case contains(c, "serie c"):
		return serieC
	}
	return serieA
}

// fileFor decides which provided file would hold a match.
func fileFor(m MatchFixture) string {
	source := fold(m.Source)
	kind := kindOf(m.Competition)
	switch {
	case contains(source, "historical"):
		return historicalFile
	case contains(source, "extended"):
		return extendedFile
	case contains(source, "serie a"):
		return serieAFile
	}
	if m.Corners != nil || m.Shots != nil {
		return extendedFile
	}
	switch kind {
	case copaDoBrasil:
		return cupFile
	case copaLibertadores:
		return libertadores
	case serieB, serieC:
		return extendedFile
	}
	return serieAFile
}

func cupRound(m MatchFixture) string {
	switch fold(m.Stage) {
	case "final":
		return "8"
	case "semifinals", "semifinal", "semi-final":
		return "7"
	case "quarterfinals", "quarterfinal":
		return "6"
	case "round of 16":
		return "5"
	}
	return "1"
}

func tournamentName(kind competitionKind) string {
	return map[competitionKind]string{serieA: "Serie A", serieB: "Serie B", serieC: "Serie C", copaDoBrasil: "Copa do Brasil", copaLibertadores: "Libertadores"}[kind]
}

func resultFor(own, other int) string {
	switch {
	case own > other:
		return "WON"
	case own < other:
		return "LOST"
	}
	return "DRAW"
}

func writeDataFiles(dir string, matches []MatchFixture, players []PlayerFixture) error {
	rows := map[string][][]string{
		serieAFile:     {{"datetime", "home_team", "home_team_state", "away_team", "away_team_state", "home_goal", "away_goal", "season", "round"}},
		cupFile:        {{"round", "datetime", "home_team", "away_team", "home_goal", "away_goal", "season"}},
		libertadores:   {{"datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "stage"}},
		extendedFile:   {{"tournament", "home", "home_goal", "away_goal", "away", "home_corner", "away_corner", "home_attack", "away_attack", "home_shots", "away_shots", "time", "date", "ht_diff", "at_diff", "ht_result", "at_result", "total_corners"}},
		historicalFile: {{"ID", "Data", "Ano", "Rodada", "Equipe_mandante", "Equipe_visitante", "Gols_mandante", "Gols_visitante", "Mandante_UF", "Visitante_UF", "Vencedor", "Arena", "OBS"}},
		playersFile:    {fifaColumns},
	}
	itoa := strconv.Itoa
	for i, m := range matches {
		datetime := m.Date.Format("2006-01-02") + " 16:00:00"
		hg, ag := itoa(m.HomeGoals), itoa(m.AwayGoals)
		file := fileFor(m)
		var row []string
		switch file {
		case serieAFile:
			row = []string{datetime, m.Home, stateOf(m.Home), m.Away, stateOf(m.Away), hg, ag, itoa(m.Season), itoa(m.Round)}
		case cupFile:
			row = []string{cupRound(m), datetime, m.Home, m.Away, hg, ag, itoa(m.Season)}
		case libertadores:
			stage := m.Stage
			if stage == "" {
				stage = "group stage"
			}
			row = []string{datetime, m.Home, m.Away, hg, ag, itoa(m.Season), stage}
		case historicalFile:
			winner := "Empate"
			if m.HomeGoals > m.AwayGoals {
				winner = "Mandante"
			} else if m.AwayGoals > m.HomeGoals {
				winner = "Visitante"
			}
			row = []string{fmt.Sprintf("%d.%02d.%04d", m.Season, m.Round, i+1), m.Date.Format("02/01/2006"), itoa(m.Season), itoa(m.Round),
				m.Home, m.Away, hg, ag, stateOf(m.Home), stateOf(m.Away), winner, "Estádio Teste", ""}
		case extendedFile:
			decimal := func(n int) string { return itoa(n) + ".0" }
			hc, ac, hs, as, total := "", "", "", "", ""
			if m.Corners != nil {
				hc, ac, total = decimal(m.Corners[0]), decimal(m.Corners[1]), decimal(m.Corners[0]+m.Corners[1])
			}
			if m.Shots != nil {
				hs, as = decimal(m.Shots[0]), decimal(m.Shots[1])
			}
			row = []string{tournamentName(kindOf(m.Competition)), m.Home, decimal(m.HomeGoals), decimal(m.AwayGoals), m.Away,
				hc, ac, "", "", hs, as, "16:00:00", m.Date.Format("2006-01-02"),
				decimal(m.HomeGoals - m.AwayGoals), decimal(m.AwayGoals - m.HomeGoals),
				resultFor(m.HomeGoals, m.AwayGoals), resultFor(m.AwayGoals, m.HomeGoals), total}
		}
		rows[file] = append(rows[file], row)
	}
	for i, p := range players {
		values := map[string]string{
			"": itoa(i), "ID": itoa(p.ID), "Name": p.Name, "Age": itoa(p.Age), "Nationality": p.Nationality,
			"Overall": itoa(p.Overall), "Potential": itoa(p.Potential), "Club": p.Club, "Position": p.Position,
			"Jersey Number": itoa(p.Jersey), "Preferred Foot": "Right", "Height": "5'10", "Weight": "165lbs",
			"Value": "€1M", "Wage": "€10K",
		}
		row := make([]string, len(fifaColumns))
		for c, name := range fifaColumns {
			row[c] = values[name]
		}
		rows[playersFile] = append(rows[playersFile], row)
	}
	for file, content := range rows {
		f, err := os.Create(filepath.Join(dir, file))
		if err != nil {
			return err
		}
		w := csv.NewWriter(f)
		if err := w.WriteAll(content); err != nil {
			f.Close()
			return err
		}
		if err := f.Close(); err != nil {
			return err
		}
	}
	return nil
}
