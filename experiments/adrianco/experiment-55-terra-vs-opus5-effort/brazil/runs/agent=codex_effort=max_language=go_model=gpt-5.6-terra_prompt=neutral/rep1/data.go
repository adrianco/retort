package main

import (
	"bufio"
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

const (
	brasileiraoFile  = "Brasileirao_Matches.csv"
	cupFile          = "Brazilian_Cup_Matches.csv"
	libertadoresFile = "Libertadores_Matches.csv"
	extendedFile     = "BR-Football-Dataset.csv"
	historicalFile   = "novo_campeonato_brasileiro.csv"
	fifaFile         = "fifa_data.csv"
)

// DataStore keeps normalized rows in memory. The supplied data is modest in
// size (about 42k rows), making startup indexing faster and simpler than a
// database while keeping lookups well below the requested latency targets.
type DataStore struct {
	Matches        []Match
	Players        []Player
	Sources        []DataSource
	teamName       map[string]string
	cupFinalRounds map[string]int
}

// LoadData reads all six required CSV files from dataDir. A missing or invalid
// file is reported explicitly instead of silently returning partial results.
func LoadData(dataDir string) (*DataStore, error) {
	if strings.TrimSpace(dataDir) == "" {
		return nil, errors.New("data directory is required")
	}
	d := &DataStore{teamName: make(map[string]string), cupFinalRounds: make(map[string]int)}
	loaders := []struct {
		file        string
		kind        string
		description string
		load        func(string) (int, error)
	}{
		{brasileiraoFile, "matches", "Brasileirão Série A match results", d.loadBrasileirao},
		{cupFile, "matches", "Copa do Brasil match results", d.loadBrazilianCup},
		{libertadoresFile, "matches", "Copa Libertadores match results", d.loadLibertadores},
		{extendedFile, "matches", "Extended Brazilian match statistics", d.loadExtendedMatches},
		{historicalFile, "matches", "Historical Brasileirão match results (2003-2019)", d.loadHistoricalMatches},
		{fifaFile, "players", "FIFA player database", d.loadPlayers},
	}
	for _, spec := range loaders {
		count, err := spec.load(filepath.Join(dataDir, spec.file))
		if err != nil {
			return nil, fmt.Errorf("load %s: %w", spec.file, err)
		}
		d.Sources = append(d.Sources, DataSource{
			File: spec.file, Kind: spec.kind, RecordCount: count, Description: spec.description,
		})
	}
	if len(d.Matches) == 0 || len(d.Players) == 0 {
		return nil, errors.New("datasets loaded but did not contain both matches and players")
	}
	d.indexCupFinalRounds()
	return d, nil
}

type csvRow struct {
	headers map[string]int
	values  []string
}

func (r csvRow) get(names ...string) string {
	for _, name := range names {
		if index, ok := r.headers[normalizeHeader(name)]; ok && index < len(r.values) {
			return strings.TrimSpace(r.values[index])
		}
	}
	return ""
}

func normalizeHeader(value string) string {
	value = strings.TrimPrefix(value, "\ufeff")
	value = strings.ToLower(strings.TrimSpace(value))
	value = strings.ReplaceAll(value, " ", "_")
	value = strings.ReplaceAll(value, "-", "_")
	return value
}

func readCSV(path string, handle func(csvRow) error) (int, error) {
	f, err := os.Open(path)
	if err != nil {
		return 0, err
	}
	defer f.Close()

	reader := csv.NewReader(bufio.NewReader(f))
	reader.FieldsPerRecord = -1
	reader.TrimLeadingSpace = true
	headers, err := reader.Read()
	if err != nil {
		return 0, fmt.Errorf("read header: %w", err)
	}
	headerIndex := make(map[string]int, len(headers))
	for i, header := range headers {
		headerIndex[normalizeHeader(header)] = i
	}
	count := 0
	for rowNumber := 2; ; rowNumber++ {
		values, err := reader.Read()
		if err != nil {
			if errors.Is(err, io.EOF) {
				break
			}
			if errors.Is(err, csv.ErrFieldCount) {
				return count, fmt.Errorf("row %d: %w", rowNumber, err)
			}
			return count, fmt.Errorf("row %d: %w", rowNumber, err)
		}
		if err := handle(csvRow{headers: headerIndex, values: values}); err != nil {
			return count, fmt.Errorf("row %d: %w", rowNumber, err)
		}
		count++
	}
	return count, nil
}

func parseInteger(value string) (int, bool) {
	value = strings.TrimSpace(strings.Trim(value, `"`))
	if value == "" || strings.EqualFold(value, "nan") || strings.EqualFold(value, "n/a") {
		return 0, false
	}
	if integer, err := strconv.Atoi(value); err == nil {
		return integer, true
	}
	decimal, err := strconv.ParseFloat(strings.ReplaceAll(value, ",", "."), 64)
	if err != nil || math.IsNaN(decimal) {
		return 0, false
	}
	return int(math.Round(decimal)), true
}

func optionalInteger(value string) *int {
	if number, ok := parseInteger(value); ok {
		return &number
	}
	return nil
}

func parseDate(value string) (time.Time, bool) {
	value = strings.TrimSpace(value)
	if value == "" {
		return time.Time{}, false
	}
	formats := []string{
		"2006-01-02 15:04:05", time.RFC3339, "2006-01-02", "02/01/2006", "2/1/2006",
	}
	for _, layout := range formats {
		if parsed, err := time.ParseInLocation(layout, value, time.UTC); err == nil {
			return parsed, true
		}
	}
	return time.Time{}, false
}

func parseDateBound(value string, end bool) (*time.Time, error) {
	value = strings.TrimSpace(value)
	if value == "" {
		return nil, nil
	}
	if len(value) == 4 {
		if year, err := strconv.Atoi(value); err == nil && year >= 1800 && year <= 3000 {
			date := time.Date(year, time.January, 1, 0, 0, 0, 0, time.UTC)
			if end {
				date = time.Date(year, time.December, 31, 23, 59, 59, 999999999, time.UTC)
			}
			return &date, nil
		}
	}
	date, ok := parseDate(value)
	if !ok {
		return nil, fmt.Errorf("invalid date %q; use YYYY-MM-DD, DD/MM/YYYY, or a year", value)
	}
	if end && len(value) <= len("2006-01-02") {
		date = date.Add(24*time.Hour - time.Nanosecond)
	}
	return &date, nil
}

func makeMatch(id string, date time.Time, rawDate, home, away string, homeGoals, awayGoals int, hasScore bool, competition string, season int, round, stage, source string) Match {
	if season == 0 && !date.IsZero() {
		season = date.Year()
	}
	dateText := strings.TrimSpace(rawDate)
	if !date.IsZero() {
		dateText = date.Format("2006-01-02")
	}
	return Match{
		ID: id, Date: date, DateText: dateText, HomeTeam: strings.TrimSpace(home), AwayTeam: strings.TrimSpace(away),
		HomeKey: normalizeTeam(home), AwayKey: normalizeTeam(away), HomeGoals: homeGoals, AwayGoals: awayGoals,
		HasScore: hasScore, Competition: normalizeCompetition(competition), Season: season, Round: strings.TrimSpace(round),
		Stage: strings.TrimSpace(stage), Source: source,
	}
}

func (d *DataStore) addMatch(match Match) {
	d.Matches = append(d.Matches, match)
	d.rememberTeam(match.HomeKey, match.HomeTeam)
	d.rememberTeam(match.AwayKey, match.AwayTeam)
}

func (d *DataStore) indexCupFinalRounds() {
	for _, match := range d.Matches {
		if normalizeCompetition(match.Competition) != "Copa do Brasil" {
			continue
		}
		round, ok := parseInteger(match.Round)
		if !ok {
			continue
		}
		key := match.Source + "|" + strconv.Itoa(match.Season)
		if round > d.cupFinalRounds[key] {
			d.cupFinalRounds[key] = round
		}
	}
}

func normalizeStage(stage string) string {
	stage = normalizeText(stage)
	switch stage {
	case "finals":
		return "final"
	case "semifinal", "semi final", "semi finals":
		return "semifinals"
	case "quarterfinal", "quarter final", "quarter finals":
		return "quarterfinals"
	case "round 16", "round of sixteen":
		return "round of 16"
	default:
		return stage
	}
}

func stageMatches(candidate, requested string) bool {
	requested = normalizeStage(requested)
	if requested == "" {
		return true
	}
	candidate = normalizeStage(candidate)
	if candidate == requested {
		return true
	}
	// "group" is a helpful shorthand for the source's "group stage".
	return requested == "group" && strings.Contains(candidate, "group")
}

func (d *DataStore) isFinalMatch(match Match) bool {
	if normalizeStage(match.Stage) == "final" {
		return true
	}
	if normalizeCompetition(match.Competition) != "Copa do Brasil" {
		return false
	}
	round, ok := parseInteger(match.Round)
	if !ok {
		return false
	}
	finalRound := d.cupFinalRounds[match.Source+"|"+strconv.Itoa(match.Season)]
	// Copa do Brasil finals in the supplied historical coverage occur at round
	// six or later. A lower terminal round signals an incomplete in-progress
	// extract (not a final), such as the scoreless 2021 rows.
	return finalRound >= 6 && round == finalRound
}

func (d *DataStore) rememberTeam(key, display string) {
	if key == "" || strings.TrimSpace(display) == "" {
		return
	}
	if existing, ok := d.teamName[key]; !ok || len(display) < len(existing) {
		d.teamName[key] = strings.TrimSpace(display)
	}
}

func (d *DataStore) loadBrasileirao(path string) (int, error) {
	return readCSV(path, func(row csvRow) error {
		date, _ := parseDate(row.get("datetime"))
		homeGoals, homeOK := parseInteger(row.get("home_goal"))
		awayGoals, awayOK := parseInteger(row.get("away_goal"))
		season, _ := parseInteger(row.get("season"))
		match := makeMatch("brasileirao-"+strconv.Itoa(len(d.Matches)+1), date, row.get("datetime"), row.get("home_team"), row.get("away_team"), homeGoals, awayGoals, homeOK && awayOK, "Brasileirão Série A", season, row.get("round"), "", brasileiraoFile)
		match.HomeState = row.get("home_team_state")
		match.AwayState = row.get("away_team_state")
		match.KickoffTime = timePart(row.get("datetime"))
		d.addMatch(match)
		return nil
	})
}

func (d *DataStore) loadBrazilianCup(path string) (int, error) {
	return readCSV(path, func(row csvRow) error {
		date, _ := parseDate(row.get("datetime"))
		homeGoals, homeOK := parseInteger(row.get("home_goal"))
		awayGoals, awayOK := parseInteger(row.get("away_goal"))
		season, _ := parseInteger(row.get("season"))
		match := makeMatch("cup-"+strconv.Itoa(len(d.Matches)+1), date, row.get("datetime"), row.get("home_team"), row.get("away_team"), homeGoals, awayGoals, homeOK && awayOK, "Copa do Brasil", season, row.get("round"), "", cupFile)
		match.KickoffTime = timePart(row.get("datetime"))
		d.addMatch(match)
		return nil
	})
}

func (d *DataStore) loadLibertadores(path string) (int, error) {
	return readCSV(path, func(row csvRow) error {
		date, _ := parseDate(row.get("datetime"))
		homeGoals, homeOK := parseInteger(row.get("home_goal"))
		awayGoals, awayOK := parseInteger(row.get("away_goal"))
		season, _ := parseInteger(row.get("season"))
		match := makeMatch("libertadores-"+strconv.Itoa(len(d.Matches)+1), date, row.get("datetime"), row.get("home_team"), row.get("away_team"), homeGoals, awayGoals, homeOK && awayOK, "Copa Libertadores", season, "", row.get("stage"), libertadoresFile)
		match.KickoffTime = timePart(row.get("datetime"))
		d.addMatch(match)
		return nil
	})
}

func (d *DataStore) loadExtendedMatches(path string) (int, error) {
	return readCSV(path, func(row csvRow) error {
		dateValue := row.get("date")
		if clock := row.get("time"); clock != "" && len(dateValue) == len("2006-01-02") {
			dateValue += " " + clock
		}
		date, _ := parseDate(dateValue)
		homeGoals, homeOK := parseInteger(row.get("home_goal"))
		awayGoals, awayOK := parseInteger(row.get("away_goal"))
		stats := &MatchStats{
			HomeCorners: optionalInteger(row.get("home_corner")), AwayCorners: optionalInteger(row.get("away_corner")),
			HomeAttacks: optionalInteger(row.get("home_attack")), AwayAttacks: optionalInteger(row.get("away_attack")),
			HomeShots: optionalInteger(row.get("home_shots")), AwayShots: optionalInteger(row.get("away_shots")),
			TotalCorners: optionalInteger(row.get("total_corners")), HomeHalfTime: row.get("ht_result"), AwayHalfTime: row.get("at_result"),
		}
		match := makeMatch("extended-"+strconv.Itoa(len(d.Matches)+1), date, row.get("date"), row.get("home"), row.get("away"), homeGoals, awayGoals, homeOK && awayOK, row.get("tournament"), 0, "", "", extendedFile)
		match.Statistics = stats
		match.KickoffTime = row.get("time")
		d.addMatch(match)
		return nil
	})
}

func (d *DataStore) loadHistoricalMatches(path string) (int, error) {
	return readCSV(path, func(row csvRow) error {
		date, _ := parseDate(row.get("data"))
		homeGoals, homeOK := parseInteger(row.get("gols_mandante"))
		awayGoals, awayOK := parseInteger(row.get("gols_visitante"))
		season, _ := parseInteger(row.get("ano"))
		id := row.get("id")
		if id == "" {
			id = "historical-" + strconv.Itoa(len(d.Matches)+1)
		}
		match := makeMatch(id, date, row.get("data"), row.get("equipe_mandante"), row.get("equipe_visitante"), homeGoals, awayGoals, homeOK && awayOK, "Brasileirão Série A", season, row.get("rodada"), "", historicalFile)
		match.HomeState = row.get("mandante_uf")
		match.AwayState = row.get("visitante_uf")
		match.Venue = row.get("arena")
		d.addMatch(match)
		return nil
	})
}

func timePart(value string) string {
	value = strings.TrimSpace(value)
	if len(value) >= len("2006-01-02 15:04:05") {
		return value[len(value)-len("15:04:05"):]
	}
	return ""
}

func (d *DataStore) loadPlayers(path string) (int, error) {
	return readCSV(path, func(row csvRow) error {
		id, _ := parseInteger(row.get("id"))
		age, _ := parseInteger(row.get("age"))
		overall, _ := parseInteger(row.get("overall"))
		potential, _ := parseInteger(row.get("potential"))
		jersey, _ := parseInteger(row.get("jersey_number"))
		player := Player{
			ID: id, Name: row.get("name"), Age: age, Nationality: row.get("nationality"), Overall: overall,
			Potential: potential, Club: row.get("club"), Position: row.get("position"), JerseyNumber: jersey,
			Height: row.get("height"), Weight: row.get("weight"), PreferredFoot: row.get("preferred_foot"),
			Skills: map[string]int{},
		}
		for _, skill := range []string{"crossing", "finishing", "dribbling", "short_passing", "long_passing", "ball_control", "acceleration", "sprint_speed", "agility", "reactions", "shot_power", "stamina", "strength", "long_shots", "vision", "composure", "standing_tackle"} {
			if score, ok := parseInteger(row.get(skill)); ok {
				player.Skills[skill] = score
			}
		}
		d.Players = append(d.Players, player)
		return nil
	})
}

func sourceMatches(candidate, requested string) bool {
	requested = normalizeText(requested)
	if requested == "" || requested == "all" || requested == "any" {
		return true
	}
	candidateKey := normalizeText(candidate)
	aliases := map[string]string{
		"brasileirao": "brasileirao matches csv", "serie a": "brasileirao matches csv",
		"cup": "brazilian cup matches csv", "brazilian cup": "brazilian cup matches csv",
		"libertadores": "libertadores matches csv", "extended": "br football dataset csv",
		"statistics": "br football dataset csv", "historical": "novo campeonato brasileiro csv",
	}
	if mapped, ok := aliases[requested]; ok {
		requested = mapped
	}
	return candidateKey == requested || strings.Contains(candidateKey, requested) || strings.Contains(requested, candidateKey)
}

var derbyPairs = map[string]bool{
	"atletico mineiro|cruzeiro": true,
	"corinthians|palmeiras":     true,
	"corinthians|santos":        true,
	"corinthians|sao paulo":     true,
	"flamengo|fluminense":       true,
	"flamengo|vasco da gama":    true,
	"fluminense|vasco da gama":  true,
	"gremio|internacional":      true,
	"palmeiras|santos":          true,
	"palmeiras|sao paulo":       true,
	"santos|sao paulo":          true,
	"sport recife|nautico":      true,
}

func derbyKey(one, two string) string {
	if one > two {
		one, two = two, one
	}
	return one + "|" + two
}

func isDerby(match Match) bool {
	return derbyPairs[derbyKey(match.HomeKey, match.AwayKey)]
}

func (d *DataStore) matchFilter(filter MatchFilter) []Match {
	// Choose a preferred source from the shared query scope before applying team
	// predicates. That keeps a season's standings and every individual team
	// statistic on the same source rather than mixing sources club by club.
	scoped := make([]Match, 0)
	for _, match := range d.Matches {
		if !competitionMatches(match.Competition, filter.Competition) {
			continue
		}
		if filter.Season != 0 && match.Season != filter.Season {
			continue
		}
		if filter.StartDate != nil && (match.Date.IsZero() || match.Date.Before(*filter.StartDate)) {
			continue
		}
		if filter.EndDate != nil && (match.Date.IsZero() || match.Date.After(*filter.EndDate)) {
			continue
		}
		if filter.Round != "" && !strings.Contains(normalizeText(match.Round), normalizeText(filter.Round)) {
			continue
		}
		if !stageMatches(match.Stage, filter.Stage) {
			continue
		}
		if !sourceMatches(match.Source, filter.Source) {
			continue
		}
		if filter.FinalsOnly && !d.isFinalMatch(match) {
			continue
		}
		scoped = append(scoped, match)
	}
	if !filter.IncludeDuplicates && strings.TrimSpace(filter.Source) == "" {
		scoped = selectPreferredSources(scoped)
	}
	matched := make([]Match, 0, len(scoped))
	for _, match := range scoped {
		if strings.TrimSpace(filter.Team) != "" && !teamNameMatches(match.HomeKey, filter.Team) && !teamNameMatches(match.AwayKey, filter.Team) {
			continue
		}
		if filter.Opponent != "" && !teamNameMatches(match.HomeKey, filter.Opponent) && !teamNameMatches(match.AwayKey, filter.Opponent) {
			continue
		}
		if filter.HomeTeam != "" && !teamNameMatches(match.HomeKey, filter.HomeTeam) {
			continue
		}
		if filter.AwayTeam != "" && !teamNameMatches(match.AwayKey, filter.AwayTeam) {
			continue
		}
		if filter.DerbiesOnly && !isDerby(match) {
			continue
		}
		matched = append(matched, match)
	}
	if !filter.IncludeDuplicates && strings.TrimSpace(filter.Source) == "" {
		matched = deduplicateMatches(matched)
	}
	sortMatches(matched, filter.Descending)
	return matched
}

// selectPreferredSources prevents one physical season from being counted two
// or three times when the supplied CSVs overlap. For each competition/season,
// it uses the source with the most scored matching rows; total rows and source
// priority break ties. This avoids selecting a larger but incomplete extract.
// A caller can still inspect every raw source with an explicit Source filter
// or IncludeDuplicates=true.
func selectPreferredSources(matches []Match) []Match {
	type sourceCount struct {
		source string
		count  int
		scored int
	}
	bySeason := make(map[string]map[string]sourceCount)
	for _, match := range matches {
		key := normalizeCompetition(match.Competition) + "|" + strconv.Itoa(match.Season)
		if bySeason[key] == nil {
			bySeason[key] = make(map[string]sourceCount)
		}
		current := bySeason[key][match.Source]
		current.source = match.Source
		current.count++
		if match.HasScore {
			current.scored++
		}
		bySeason[key][match.Source] = current
	}
	chosen := make(map[string]string, len(bySeason))
	for key, counts := range bySeason {
		best := sourceCount{count: -1}
		for source, count := range counts {
			if count.scored > best.scored || (count.scored == best.scored && (count.count > best.count || (count.count == best.count && sourcePriority(source) < sourcePriority(best.source)))) {
				best = sourceCount{source: source, count: count.count, scored: count.scored}
			}
		}
		chosen[key] = best.source
	}
	result := make([]Match, 0, len(matches))
	for _, match := range matches {
		key := normalizeCompetition(match.Competition) + "|" + strconv.Itoa(match.Season)
		if chosen[key] == match.Source {
			result = append(result, match)
		}
	}
	return result
}

func sourcePriority(source string) int {
	switch source {
	case brasileiraoFile, cupFile, libertadoresFile:
		return 0
	case historicalFile:
		return 1
	case extendedFile:
		return 2
	default:
		return 3
	}
}

func matchDedupKey(match Match) string {
	date := match.DateText
	if !match.Date.IsZero() {
		date = match.Date.Format("2006-01-02")
	}
	return strings.Join([]string{normalizeCompetition(match.Competition), date, match.HomeKey, match.AwayKey, strconv.Itoa(match.HomeGoals), strconv.Itoa(match.AwayGoals)}, "|")
}

func deduplicateMatches(matches []Match) []Match {
	best := make(map[string]Match, len(matches))
	for _, match := range matches {
		key := matchDedupKey(match)
		current, found := best[key]
		if !found || sourcePriority(match.Source) < sourcePriority(current.Source) {
			best[key] = match
		}
	}
	result := make([]Match, 0, len(best))
	for _, match := range best {
		result = append(result, match)
	}
	return result
}

func sortMatches(matches []Match, descending bool) {
	sort.Slice(matches, func(i, j int) bool {
		left, right := matches[i], matches[j]
		if !left.Date.Equal(right.Date) {
			if descending {
				return left.Date.After(right.Date)
			}
			return left.Date.Before(right.Date)
		}
		if left.Season != right.Season {
			if descending {
				return left.Season > right.Season
			}
			return left.Season < right.Season
		}
		if left.HomeTeam != right.HomeTeam {
			return left.HomeTeam < right.HomeTeam
		}
		return left.AwayTeam < right.AwayTeam
	})
}

// SearchMatches returns the matching set in date order, capped only when a
// positive Limit is supplied. It is useful to direct callers as well as MCP.
func (d *DataStore) SearchMatches(filter MatchFilter) []Match {
	matched := d.matchFilter(filter)
	if filter.Limit > 0 && len(matched) > filter.Limit {
		return matched[:filter.Limit]
	}
	return matched
}

func (d *DataStore) DisplayTeam(team string) string {
	key := normalizeTeam(team)
	if display, ok := d.teamName[key]; ok {
		return display
	}
	return strings.TrimSpace(team)
}
