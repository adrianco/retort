package soccer

import (
	"fmt"
	"os"
	"path/filepath"
)

// LoadStoreFromDir loads all six provided datasets from dataDir (typically
// data/kaggle) and returns a queryable Store.
func LoadStoreFromDir(dataDir string) (*Store, error) {
	var matches []Match

	matchLoaders := []struct {
		file string
		load func(*os.File) ([]Match, error)
	}{
		{"Brasileirao_Matches.csv", func(f *os.File) ([]Match, error) { return LoadBrasileiraoMatches(f) }},
		{"Brazilian_Cup_Matches.csv", func(f *os.File) ([]Match, error) { return LoadCopaDoBrasilMatches(f) }},
		{"Libertadores_Matches.csv", func(f *os.File) ([]Match, error) { return LoadLibertadoresMatches(f) }},
		{"BR-Football-Dataset.csv", func(f *os.File) ([]Match, error) { return LoadBRFootballMatches(f) }},
		{"novo_campeonato_brasileiro.csv", func(f *os.File) ([]Match, error) { return LoadHistoricalBrasileiraoMatches(f) }},
	}

	for _, ml := range matchLoaders {
		loaded, err := loadFile(dataDir, ml.file, ml.load)
		if err != nil {
			return nil, err
		}
		matches = append(matches, loaded...)
	}

	players, err := loadFile(dataDir, "fifa_data.csv", func(f *os.File) ([]Player, error) { return LoadFIFAPlayers(f) })
	if err != nil {
		return nil, err
	}

	return NewStore(matches, players), nil
}

func loadFile[T any](dataDir, name string, load func(*os.File) ([]T, error)) ([]T, error) {
	path := filepath.Join(dataDir, name)
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("soccer: opening %s: %w", name, err)
	}
	defer f.Close()
	records, err := load(f)
	if err != nil {
		return nil, fmt.Errorf("soccer: loading %s: %w", name, err)
	}
	return records, nil
}
