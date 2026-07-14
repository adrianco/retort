package main

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
)

// LoadStore reads all six source CSVs from dataDir and returns a populated,
// indexed Store. It never fails on individual malformed rows -- those are
// collected as warnings on the returned Store -- but returns an error if a
// required file is missing or unreadable.
func LoadStore(dataDir string) (*Store, error) {
	store := newStore()
	warn := func(format string, args ...any) {
		store.LoadWarnings = append(store.LoadWarnings, fmt.Sprintf(format, args...))
	}

	brasileirao, err := loadFile(dataDir, "Brasileirao_Matches.csv", warn, loadBrasileirao)
	if err != nil {
		return nil, err
	}
	minBrasileiraoSeason, maxBrasileiraoSeason := seasonRange(brasileirao)
	for _, m := range brasileirao {
		store.addMatch(m)
	}

	cup, err := loadFile(dataDir, "Brazilian_Cup_Matches.csv", warn, loadCup)
	if err != nil {
		return nil, err
	}
	_, maxCupSeason := seasonRange(cup)
	for _, m := range cup {
		store.addMatch(m)
	}

	libertadores, err := loadFile(dataDir, "Libertadores_Matches.csv", warn, loadLibertadores)
	if err != nil {
		return nil, err
	}
	for _, m := range libertadores {
		store.addMatch(m)
	}

	// BR-Football-Dataset.csv overlaps in real-world coverage with
	// Brasileirao_Matches.csv (Serie A) and Brazilian_Cup_Matches.csv (Copa
	// do Brasil) for the seasons those primary sources already cover, so
	// those overlapping seasons are skipped here to avoid double-counting
	// the same real matches under two competition tags. Serie B/C have no
	// primary source and are always kept, as are seasons past the primary
	// sources' coverage (e.g. 2023).
	brFootball, err := loadFile(dataDir, "BR-Football-Dataset.csv", warn, loadBRFootball)
	if err != nil {
		return nil, err
	}
	skippedExtendedOverlap := 0
	for _, m := range brFootball {
		if m.Competition == "Serie A (Extended Stats)" && m.Season <= maxBrasileiraoSeason {
			skippedExtendedOverlap++
			continue
		}
		if m.Competition == "Copa do Brasil (Extended Stats)" && m.Season <= maxCupSeason {
			skippedExtendedOverlap++
			continue
		}
		store.addMatch(m)
	}
	if skippedExtendedOverlap > 0 {
		warn("BR-Football-Dataset.csv: skipped %d matches already covered by Brasileirao_Matches.csv (<=%d) or Brazilian_Cup_Matches.csv (<=%d)",
			skippedExtendedOverlap, maxBrasileiraoSeason, maxCupSeason)
	}

	novo, err := loadFile(dataDir, "novo_campeonato_brasileiro.csv", warn, loadNovoCampeonato)
	if err != nil {
		return nil, err
	}
	skippedOverlap := 0
	for _, m := range novo {
		if minBrasileiraoSeason != 0 && m.Season >= minBrasileiraoSeason {
			skippedOverlap++
			continue
		}
		store.addMatch(m)
	}
	if skippedOverlap > 0 {
		warn("novo_campeonato_brasileiro.csv: skipped %d matches from seasons >= %d already covered by Brasileirao_Matches.csv", skippedOverlap, minBrasileiraoSeason)
	}

	players, err := loadFile(dataDir, "fifa_data.csv", warn, loadFIFA)
	if err != nil {
		return nil, err
	}
	for _, p := range players {
		store.addPlayer(p)
	}

	return store, nil
}

func seasonRange(matches []Match) (min, max int) {
	for _, m := range matches {
		if min == 0 || m.Season < min {
			min = m.Season
		}
		if m.Season > max {
			max = m.Season
		}
	}
	return min, max
}

func loadFile[T any](dataDir, name string, warn warnFunc, loader func(r io.Reader, warn warnFunc) ([]T, error)) ([]T, error) {
	path := filepath.Join(dataDir, name)
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("opening %s: %w", path, err)
	}
	defer f.Close()
	return loader(f, warn)
}
