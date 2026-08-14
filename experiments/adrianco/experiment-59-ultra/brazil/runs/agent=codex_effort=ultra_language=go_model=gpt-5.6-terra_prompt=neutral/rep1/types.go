package main

import (
	"encoding/json"
	"time"
)

// Match is one fixture or result from a supplied match data source. Scores are
// meaningful only when ScoreKnown is true; some of the supplied sources also
// contain future or otherwise unplayed fixtures.
type Match struct {
	ID           string    `json:"id,omitempty"`
	SourceRow    int       `json:"sourceRow,omitempty"`
	ExternalID   string    `json:"externalId,omitempty"`
	Source       string    `json:"source"`
	Competition  string    `json:"competition"`
	Date         time.Time `json:"-"`
	DateText     string    `json:"date"`
	Season       int       `json:"season,omitempty"`
	Round        string    `json:"round,omitempty"`
	Stage        string    `json:"stage,omitempty"`
	Kickoff      string    `json:"kickoff,omitempty"`
	HomeTeam     string    `json:"homeTeam"`
	AwayTeam     string    `json:"awayTeam"`
	HomeKey      string    `json:"-"`
	AwayKey      string    `json:"-"`
	HomeState    string    `json:"homeState,omitempty"`
	AwayState    string    `json:"awayState,omitempty"`
	HomeGoals    int       `json:"homeGoals,omitempty"`
	AwayGoals    int       `json:"awayGoals,omitempty"`
	ScoreKnown   bool      `json:"scoreKnown"`
	ResultStatus string    `json:"resultStatus"`
	Venue        string    `json:"venue,omitempty"`
	HomeCorners  *int      `json:"homeCorners,omitempty"`
	AwayCorners  *int      `json:"awayCorners,omitempty"`
	HomeShots    *int      `json:"homeShots,omitempty"`
	AwayShots    *int      `json:"awayShots,omitempty"`
	HomeAttacks  *int      `json:"homeAttacks,omitempty"`
	AwayAttacks  *int      `json:"awayAttacks,omitempty"`
	TotalCorners *int      `json:"totalCorners,omitempty"`
	// The BR-Football dataset labels these fields ht_* and at_*. Despite those
	// labels, they describe the home/away final-result difference and outcome,
	// not half-time data, so expose them with unambiguous names.
	HomeGoalDifference *int   `json:"homeGoalDifference,omitempty"`
	AwayGoalDifference *int   `json:"awayGoalDifference,omitempty"`
	HomeResult         string `json:"homeResult,omitempty"`
	AwayResult         string `json:"awayResult,omitempty"`
}

// MarshalJSON keeps unknown scores genuinely nullable on the protocol surface.
// Internally we use ints plus ScoreKnown for efficient aggregation; exposing a
// literal null prevents a scheduled fixture from being mistaken for a 0-0 draw.
func (match Match) MarshalJSON() ([]byte, error) {
	type matchOutput struct {
		ID                 string `json:"id,omitempty"`
		SourceRow          int    `json:"sourceRow,omitempty"`
		ExternalID         string `json:"externalId,omitempty"`
		Source             string `json:"source"`
		Competition        string `json:"competition"`
		Date               string `json:"date"`
		Season             int    `json:"season,omitempty"`
		Round              string `json:"round,omitempty"`
		Stage              string `json:"stage,omitempty"`
		Kickoff            string `json:"kickoff,omitempty"`
		HomeTeam           string `json:"homeTeam"`
		AwayTeam           string `json:"awayTeam"`
		HomeState          string `json:"homeState,omitempty"`
		AwayState          string `json:"awayState,omitempty"`
		HomeGoals          *int   `json:"homeGoals"`
		AwayGoals          *int   `json:"awayGoals"`
		ScoreKnown         bool   `json:"scoreKnown"`
		ResultStatus       string `json:"resultStatus"`
		Venue              string `json:"venue,omitempty"`
		HomeCorners        *int   `json:"homeCorners,omitempty"`
		AwayCorners        *int   `json:"awayCorners,omitempty"`
		HomeShots          *int   `json:"homeShots,omitempty"`
		AwayShots          *int   `json:"awayShots,omitempty"`
		HomeAttacks        *int   `json:"homeAttacks,omitempty"`
		AwayAttacks        *int   `json:"awayAttacks,omitempty"`
		TotalCorners       *int   `json:"totalCorners,omitempty"`
		HomeGoalDifference *int   `json:"homeGoalDifference,omitempty"`
		AwayGoalDifference *int   `json:"awayGoalDifference,omitempty"`
		HomeResult         string `json:"homeResult,omitempty"`
		AwayResult         string `json:"awayResult,omitempty"`
	}
	output := matchOutput{
		ID: match.ID, SourceRow: match.SourceRow, ExternalID: match.ExternalID, Source: match.Source, Competition: match.Competition, Date: match.DateText, Season: match.Season,
		Round: match.Round, Stage: match.Stage, Kickoff: match.Kickoff, HomeTeam: match.HomeTeam, AwayTeam: match.AwayTeam,
		HomeState: match.HomeState, AwayState: match.AwayState, ScoreKnown: match.ScoreKnown, ResultStatus: match.ResultStatus,
		Venue: match.Venue, HomeCorners: match.HomeCorners, AwayCorners: match.AwayCorners, HomeShots: match.HomeShots, AwayShots: match.AwayShots, HomeAttacks: match.HomeAttacks, AwayAttacks: match.AwayAttacks, TotalCorners: match.TotalCorners,
		HomeGoalDifference: match.HomeGoalDifference, AwayGoalDifference: match.AwayGoalDifference, HomeResult: match.HomeResult, AwayResult: match.AwayResult,
	}
	if match.ScoreKnown {
		homeGoals, awayGoals := match.HomeGoals, match.AwayGoals
		output.HomeGoals, output.AwayGoals = &homeGoals, &awayGoals
	}
	return json.Marshal(output)
}

// Player is the subset of the FIFA dataset that is useful for discovery and
// comparison. The raw CSV has many additional skill attributes; retaining the
// core searchable fields keeps server start-up and tool results small.
type Player struct {
	ID          string         `json:"id,omitempty"`
	Name        string         `json:"name"`
	NameKey     string         `json:"-"`
	Age         int            `json:"age,omitempty"`
	Nationality string         `json:"nationality,omitempty"`
	Overall     int            `json:"overall,omitempty"`
	Potential   int            `json:"potential,omitempty"`
	Club        string         `json:"club,omitempty"`
	ClubKey     string         `json:"-"`
	Position    string         `json:"position,omitempty"`
	Jersey      string         `json:"jerseyNumber,omitempty"`
	Height      string         `json:"height,omitempty"`
	Weight      string         `json:"weight,omitempty"`
	Attributes  map[string]int `json:"attributes,omitempty"`
}

// LoadReport documents that every required input was read, including rows kept
// with an unknown score rather than silently converting them to a 0-0 result.
type LoadReport struct {
	Sources map[string]SourceReport `json:"sources"`
}

type SourceReport struct {
	Path    string `json:"path"`
	Loaded  int    `json:"loaded"`
	Skipped int    `json:"skipped"`
}

type MatchFilter struct {
	Team            string
	Opponent        string
	HomeTeam        string
	AwayTeam        string
	Competition     string
	Source          string
	Season          int
	DateFrom        *time.Time
	DateTo          *time.Time
	Round           string
	Stage           string
	IncludeUnplayed bool
	Limit           int
	Offset          int
}

type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	MaxOverall  int
	MinAge      int
	MaxAge      int
	SortBy      string
	SortOrder   string
	Limit       int
	Offset      int
}

type TeamStats struct {
	Team                    string   `json:"team"`
	Competition             string   `json:"competition,omitempty"`
	Season                  int      `json:"season,omitempty"`
	Venue                   string   `json:"venue"`
	SourceScope             string   `json:"sourceScope,omitempty"`
	DataSources             []string `json:"dataSources,omitempty"`
	Matches                 int      `json:"matches"`
	Wins                    int      `json:"wins"`
	Draws                   int      `json:"draws"`
	Losses                  int      `json:"losses"`
	GoalsFor                int      `json:"goalsFor"`
	GoalsAgainst            int      `json:"goalsAgainst"`
	WinRate                 float64  `json:"winRate"`
	UnknownFixturesExcluded int      `json:"unknownFixturesExcluded"`
}

type HeadToHead struct {
	TeamA       string   `json:"teamA"`
	TeamB       string   `json:"teamB"`
	SourceScope string   `json:"sourceScope,omitempty"`
	DataSources []string `json:"dataSources,omitempty"`
	Matches     int      `json:"matches"`
	TeamAWins   int      `json:"teamAWins"`
	TeamBWins   int      `json:"teamBWins"`
	Draws       int      `json:"draws"`
	TeamAGoals  int      `json:"teamAGoals"`
	TeamBGoals  int      `json:"teamBGoals"`
}

type Standing struct {
	Position     int    `json:"position"`
	Team         string `json:"team"`
	Played       int    `json:"played"`
	Wins         int    `json:"wins"`
	Draws        int    `json:"draws"`
	Losses       int    `json:"losses"`
	GoalsFor     int    `json:"goalsFor"`
	GoalsAgainst int    `json:"goalsAgainst"`
	GoalDiff     int    `json:"goalDifference"`
	Points       int    `json:"points"`
}

type StatisticsResult struct {
	Metric                  string      `json:"metric"`
	Competition             string      `json:"competition,omitempty"`
	Season                  int         `json:"season,omitempty"`
	SourceScope             string      `json:"sourceScope,omitempty"`
	DataSources             []string    `json:"dataSources,omitempty"`
	Matches                 int         `json:"matches"`
	UnknownFixturesExcluded int         `json:"unknownFixturesExcluded"`
	Value                   interface{} `json:"value"`
}

type MatchSearchResult struct {
	Matches    []Match `json:"matches"`
	Total      int     `json:"total"`
	NextOffset *int    `json:"nextOffset,omitempty"`
}
