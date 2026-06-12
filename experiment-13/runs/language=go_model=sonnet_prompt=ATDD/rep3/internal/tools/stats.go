package tools

import (
	"context"
	"encoding/json"
	"sort"
	"strings"

	"brazilian-soccer-mcp/internal/data"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

func GetStatisticsTool(matches []data.Match) server.ServerTool {
	tool := mcp.NewTool("get_statistics",
		mcp.WithDescription("Get various statistics from match data"),
		mcp.WithString("stat_type", mcp.Required(), mcp.Description("Type of statistic: biggest_wins, avg_goals, best_home_record, best_away_record")),
		mcp.WithString("competition", mcp.Description("Competition filter: brasileirao, copa, libertadores")),
		mcp.WithNumber("season", mcp.Description("Season year")),
		mcp.WithNumber("limit", mcp.Description("Number of results to return (default 10)")),
	)

	handler := func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		args := req.GetArguments()
		statType, _ := args["stat_type"].(string)
		competitionParam, _ := args["competition"].(string)
		seasonFloat, _ := args["season"].(float64)
		season := int(seasonFloat)
		limitF, _ := args["limit"].(float64)
		limit := int(limitF)
		if limit <= 0 {
			limit = 10
		}

		// Filter matches
		var filtered []data.Match
		for _, m := range matches {
			if competitionParam != "" && !matchesCompetition(competitionParam, m.Competition) {
				continue
			}
			if season != 0 && m.Season != season {
				continue
			}
			filtered = append(filtered, m)
		}

		var result interface{}
		var b []byte

		switch strings.ToLower(statType) {
		case "biggest_wins":
			result = biggestWins(filtered, limit)
		case "avg_goals":
			result = avgGoals(filtered, limit)
		case "best_home_record":
			result = bestHomeRecord(filtered, limit)
		case "best_away_record":
			result = bestAwayRecord(filtered, limit)
		default:
			result = map[string]string{"error": "unknown stat_type: " + statType}
		}

		b, _ = json.Marshal(result)
		return mcp.NewToolResultText(string(b)), nil
	}

	return server.ServerTool{Tool: tool, Handler: handler}
}

type biggestWinEntry struct {
	Date        string `json:"date"`
	HomeTeam    string `json:"home_team"`
	AwayTeam    string `json:"away_team"`
	HomeGoal    int    `json:"home_goal"`
	AwayGoal    int    `json:"away_goal"`
	GoalDiff    int    `json:"goal_diff"`
	Competition string `json:"competition"`
	Season      int    `json:"season"`
}

func biggestWins(matches []data.Match, limit int) map[string]interface{} {
	var entries []biggestWinEntry
	for _, m := range matches {
		diff := m.HomeGoal - m.AwayGoal
		if diff < 0 {
			diff = -diff
		}
		entries = append(entries, biggestWinEntry{
			Date:        m.Date,
			HomeTeam:    m.HomeTeam,
			AwayTeam:    m.AwayTeam,
			HomeGoal:    m.HomeGoal,
			AwayGoal:    m.AwayGoal,
			GoalDiff:    diff,
			Competition: m.Competition,
			Season:      m.Season,
		})
	}
	sort.Slice(entries, func(i, j int) bool {
		return entries[i].GoalDiff > entries[j].GoalDiff
	})
	if len(entries) > limit {
		entries = entries[:limit]
	}
	if entries == nil {
		entries = []biggestWinEntry{}
	}
	return map[string]interface{}{
		"stat_type": "biggest_wins",
		"results":   entries,
	}
}

type avgGoalsEntry struct {
	Competition string  `json:"competition"`
	Season      int     `json:"season"`
	Matches     int     `json:"matches"`
	TotalGoals  int     `json:"total_goals"`
	AvgGoals    float64 `json:"avg_goals"`
}

func avgGoals(matches []data.Match, limit int) map[string]interface{} {
	type key struct {
		Competition string
		Season      int
	}
	type stat struct {
		TotalGoals int
		Matches    int
	}
	statsMap := map[key]*stat{}
	for _, m := range matches {
		k := key{Competition: m.Competition, Season: m.Season}
		if _, ok := statsMap[k]; !ok {
			statsMap[k] = &stat{}
		}
		statsMap[k].TotalGoals += m.HomeGoal + m.AwayGoal
		statsMap[k].Matches++
	}

	var entries []avgGoalsEntry
	for k, st := range statsMap {
		avg := 0.0
		if st.Matches > 0 {
			avg = float64(st.TotalGoals) / float64(st.Matches)
		}
		entries = append(entries, avgGoalsEntry{
			Competition: k.Competition,
			Season:      k.Season,
			Matches:     st.Matches,
			TotalGoals:  st.TotalGoals,
			AvgGoals:    avg,
		})
	}
	sort.Slice(entries, func(i, j int) bool {
		return entries[i].AvgGoals > entries[j].AvgGoals
	})
	if len(entries) > limit {
		entries = entries[:limit]
	}
	if entries == nil {
		entries = []avgGoalsEntry{}
	}
	return map[string]interface{}{
		"stat_type": "avg_goals",
		"results":   entries,
	}
}

type recordEntry struct {
	Team         string  `json:"team"`
	Matches      int     `json:"matches"`
	Wins         int     `json:"wins"`
	Draws        int     `json:"draws"`
	Losses       int     `json:"losses"`
	GoalsFor     int     `json:"goals_for"`
	GoalsAgainst int     `json:"goals_against"`
	WinRate      float64 `json:"win_rate"`
}

func bestHomeRecord(matches []data.Match, limit int) map[string]interface{} {
	statsMap := map[string]*recordEntry{}
	for _, m := range matches {
		key := strings.ToLower(m.HomeTeam)
		if _, ok := statsMap[key]; !ok {
			statsMap[key] = &recordEntry{Team: m.HomeTeam}
		}
		st := statsMap[key]
		st.Matches++
		st.GoalsFor += m.HomeGoal
		st.GoalsAgainst += m.AwayGoal
		if m.HomeGoal > m.AwayGoal {
			st.Wins++
		} else if m.HomeGoal == m.AwayGoal {
			st.Draws++
		} else {
			st.Losses++
		}
	}

	var entries []recordEntry
	for _, st := range statsMap {
		if st.Matches > 0 {
			st.WinRate = float64(st.Wins) / float64(st.Matches)
		}
		entries = append(entries, *st)
	}
	sort.Slice(entries, func(i, j int) bool {
		if entries[i].WinRate != entries[j].WinRate {
			return entries[i].WinRate > entries[j].WinRate
		}
		return entries[i].Matches > entries[j].Matches
	})
	if len(entries) > limit {
		entries = entries[:limit]
	}
	if entries == nil {
		entries = []recordEntry{}
	}
	return map[string]interface{}{
		"stat_type": "best_home_record",
		"results":   entries,
	}
}

func bestAwayRecord(matches []data.Match, limit int) map[string]interface{} {
	statsMap := map[string]*recordEntry{}
	for _, m := range matches {
		key := strings.ToLower(m.AwayTeam)
		if _, ok := statsMap[key]; !ok {
			statsMap[key] = &recordEntry{Team: m.AwayTeam}
		}
		st := statsMap[key]
		st.Matches++
		st.GoalsFor += m.AwayGoal
		st.GoalsAgainst += m.HomeGoal
		if m.AwayGoal > m.HomeGoal {
			st.Wins++
		} else if m.AwayGoal == m.HomeGoal {
			st.Draws++
		} else {
			st.Losses++
		}
	}

	var entries []recordEntry
	for _, st := range statsMap {
		if st.Matches > 0 {
			st.WinRate = float64(st.Wins) / float64(st.Matches)
		}
		entries = append(entries, *st)
	}
	sort.Slice(entries, func(i, j int) bool {
		if entries[i].WinRate != entries[j].WinRate {
			return entries[i].WinRate > entries[j].WinRate
		}
		return entries[i].Matches > entries[j].Matches
	})
	if len(entries) > limit {
		entries = entries[:limit]
	}
	if entries == nil {
		entries = []recordEntry{}
	}
	return map[string]interface{}{
		"stat_type": "best_away_record",
		"results":   entries,
	}
}
