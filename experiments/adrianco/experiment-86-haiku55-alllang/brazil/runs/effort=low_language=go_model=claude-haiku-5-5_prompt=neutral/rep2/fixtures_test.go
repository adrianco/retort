// Shared test fixtures: a small, hand-checked copy of each dataset format.
// Tests write these to a temp directory so they never depend on the real data.

package main

import (
	"os"
	"path/filepath"
	"testing"
)

const brasileiraoFixture = `"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
2019-05-01 16:00:00,"Flamengo-RJ","RJ","Fluminense-RJ","RJ",2,1,2019,5
2019-09-01 16:00:00,"Fluminense-RJ","RJ","Flamengo-RJ","RJ",0,0,2019,22
2019-06-10 16:00:00,"Palmeiras-SP","SP","Corinthians-SP","SP",3,0,2019,8
2019-07-10 16:00:00,"Corinthians-SP","SP","Palmeiras-SP","SP",1,1,2019,15
2019-08-10 16:00:00,"Atlético-MG","MG","Flamengo-RJ","RJ",1,0,2019,16
2019-08-11 16:00:00,"Atlético-PR","PR","Santos-SP","SP",2,2,2019,16
2019-08-12 16:00:00,"Atlético-MG","MG","Santos-SP","SP",4,0,2019,17
2022-05-01 16:00:00,"Palmeiras-SP","SP","Santos-SP","SP",NA,NA,2022,3
`

const cupFixture = `"round","datetime","home_team","away_team","home_goal","away_goal","season"
"1",2019-03-01 20:00:00,"Flamengo - RJ","Vila Nova - GO",2,0,2019
"8",2019-11-20 20:00:00,"Flamengo - RJ","Athletico - PR",1,0,2019
"8",2019-11-27 20:00:00,"Athletico - PR","Flamengo - RJ",0,0,2019
`

const libertadoresFixture = `datetime,home_team,away_team,home_goal,away_goal,season,stage
2019-02-14 19:00:00,"Flamengo","Boca Juniors","2","0",2019,"group stage"
2019-11-23 19:00:00,"Flamengo","River Plate","2","1",2019,"final"
`

// The historical file has 2019 rows that duplicate the Brasileirão file, and
// 2003 rows that appear nowhere else.
const historicalFixture = `ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
2019.01.0001,01/05/2019,2019,5,Flamengo,Fluminense,2,1,RJ,RJ,Mandante,Maracanã,
2003.01.0001,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco de Ouro,
`

// BR-Football has no season column and uses a different label for every club.
// It covers 2023 for Serie A, which no other file does.
const brFootballFixture = `tournament,home,home_goal,away_goal,away,date
Serie A,Flamengo,2.0,1.0,Fluminense,2019-05-01
Serie A,Atletico Mineiro,0.0,1.0,Flamengo,2023-06-01
Copa do Brasil,Sao Paulo,1.0,1.0,Flamengo,2023-09-24
`

// The FIFA file starts with a UTF-8 byte-order mark, as the real export does.
const fifaFixture = "\ufeffID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number,Value,Wage,Preferred Foot,Height,Weight\n" +
	`158023,L. Messi,31,Argentina,94,94,FC Barcelona,RF,10,€110.5M,€565K,Left,5'7,159lbs` + "\n" +
	`1,Neymar Jr,27,Brazil,92,92,Paris Saint-Germain,LW,10,€128.1M,€280K,Right,5'9,150lbs` + "\n" +
	`2,Gabriel Barbosa,22,Brazil,84,85,CR Flamengo,ST,9,€30M,€40K,Right,5'9,160lbs` + "\n" +
	`3,Diego Ribas,33,Brazil,80,80,CR Flamengo,CAM,10,€8M,€30K,Right,5'9,150lbs` + "\n" +
	`4,Alisson,26,Brazil,89,91,Liverpool,GK,1,€70M,€120K,Right,6'3,176lbs` + "\n" +
	`5,Vitoria Player,24,Brazil,70,72,Vitória Guimarães,ST,9,€1M,€5K,Right,5'11,160lbs` + "\n" +
	`6,Santos Player,25,Brazil,68,70,Santos Laguna,CB,4,€1M,€5K,Right,6'0,170lbs` + "\n"

// writeFixtures writes the six fixture files into a fresh temp directory.
func writeFixtures(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	files := map[string]string{
		fileBrasileirao:  brasileiraoFixture,
		fileCup:          cupFixture,
		fileLibertadores: libertadoresFixture,
		fileHistorical:   historicalFixture,
		fileBRFootball:   brFootballFixture,
		fileFIFA:         fifaFixture,
	}
	for name, content := range files {
		if err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0o600); err != nil {
			t.Fatal(err)
		}
	}
	return dir
}

// fixtureStore loads the fixture dataset.
func fixtureStore(t *testing.T) *Store {
	t.Helper()
	st, err := LoadStore(writeFixtures(t))
	if err != nil {
		t.Fatalf("loading fixtures: %v", err)
	}
	return st
}
