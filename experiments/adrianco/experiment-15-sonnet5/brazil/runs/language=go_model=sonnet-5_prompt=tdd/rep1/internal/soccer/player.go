package soccer

import "io"

// Player represents a FIFA player record.
type Player struct {
	ID           int
	Name         string
	Age          int
	Nationality  string
	Overall      int
	Potential    int
	Club         string
	Position     string
	JerseyNumber int
	Height       string
	Weight       string
}

// LoadFIFAPlayers parses the fifa_data.csv dataset.
func LoadFIFAPlayers(r io.Reader) ([]Player, error) {
	header, rows, err := readCSVRecords(r)
	if err != nil {
		return nil, err
	}
	col := columnIndex(header)
	players := make([]Player, 0, len(rows))
	for _, row := range rows {
		players = append(players, Player{
			ID:           parseIntField(row[col["ID"]]),
			Name:         row[col["Name"]],
			Age:          parseIntField(row[col["Age"]]),
			Nationality:  row[col["Nationality"]],
			Overall:      parseIntField(row[col["Overall"]]),
			Potential:    parseIntField(row[col["Potential"]]),
			Club:         row[col["Club"]],
			Position:     row[col["Position"]],
			JerseyNumber: parseIntField(row[col["Jersey Number"]]),
			Height:       row[col["Height"]],
			Weight:       row[col["Weight"]],
		})
	}
	return players, nil
}
