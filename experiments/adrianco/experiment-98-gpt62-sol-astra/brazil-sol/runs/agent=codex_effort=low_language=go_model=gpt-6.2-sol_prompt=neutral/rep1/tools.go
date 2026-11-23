package main

import (
	"bytes"
	"cmp"
	"encoding/json"
	"fmt"
	"maps"
	"slices"
)

type object = map[string]any

type Tool struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	InputSchema object `json:"inputSchema"`
	run         func(*Store, json.RawMessage) (object, error)
}

type Page struct {
	Offset int `json:"offset"`
	Limit  int `json:"limit"`
}

func paginate[T any](p Page, key string, rows []T) (object, error) {
	if p.Offset < 0 || p.Limit < 0 || p.Limit > 500 {
		return nil, fmt.Errorf("offset must be nonnegative and limit must be between 1 and 500 when supplied")
	}
	if p.Limit == 0 {
		p.Limit = 25
	}
	start := min(p.Offset, len(rows))
	end := start + min(p.Limit, len(rows)-start)
	result := object{"total": len(rows), "offset": p.Offset, key: rows[start:end]}
	if end < len(rows) {
		result["next_offset"] = end
	}
	return result, nil
}

type MatchArgs struct {
	Filter
	Page
}
type PlayerArgs struct {
	PlayerFilter
	Page
	GroupByClub bool `json:"group_by_club"`
}
type AnalysisArgs struct {
	Filter
	Page
	Metric         string `json:"metric"`
	MinimumMatches int    `json:"minimum_matches"`
}
type StandingArgs struct {
	Season      int    `json:"season"`
	Competition string `json:"competition"`
}
type ProfileArgs struct {
	Filter
	Page
}

func defineTool[A any](name, description string, properties object, required []string, run func(*Store, A) (object, error)) Tool {
	schema := object{"type": "object", "properties": properties, "additionalProperties": false}
	if len(required) > 0 {
		schema["required"] = required
	}
	return Tool{name, description, schema, func(s *Store, raw json.RawMessage) (object, error) {
		var args A
		if len(raw) != 0 {
			raw = bytes.TrimSpace(raw)
			if len(raw) == 0 || raw[0] != '{' {
				return nil, fmt.Errorf("arguments must be an object")
			}
			decoder := json.NewDecoder(bytes.NewReader(raw))
			decoder.DisallowUnknownFields()
			if err := decoder.Decode(&args); err != nil {
				return nil, err
			}
		}
		return run(s, args)
	}}
}

func property(kind, description string) object {
	return object{"type": kind, "description": description}
}

func withProperties(base, extra object) object {
	result := maps.Clone(base)
	maps.Copy(result, extra)
	return result
}

func soccerTools() []Tool {
	filters := object{
		"team":        property("string", "Club name, with or without recognized state suffixes and aliases."),
		"opponent":    property("string", "Other club in a head-to-head search. Requires team."),
		"side":        object{"type": "string", "enum": []string{"home", "away", "either"}, "description": "Venue relative to team. Defaults to either."},
		"competition": property("string", "Brasileirão Série A, Série B, Série C, Copa do Brasil, or Copa Libertadores."),
		"season":      property("integer", "Competition edition year."),
		"season_from": property("integer", "Inclusive first season, when comparing seasons."),
		"season_to":   property("integer", "Inclusive last season, when comparing seasons."),
		"date_from":   property("string", "Inclusive calendar start, YYYY-MM-DD or DD/MM/YYYY."),
		"date_to":     property("string", "Inclusive calendar end, YYYY-MM-DD or DD/MM/YYYY."),
		"round":       property("string", "Source round number as text."),
		"stage":       property("string", "Stage such as final, semifinals, quarterfinals, round of 16, group stage, or knockout (Libertadores)."),
		"source":      object{"type": "string", "enum": []string{leagueFile, cupFile, libertadoresFile, extendedFile, historyFile}, "description": "Optional dataset filename. Defaults to reconciled matches from all five sources."},
		"derby":       property("boolean", "Restrict to the traditional rivalries covered by the server."),
		"status":      object{"type": "string", "enum": []string{"played", "unscored"}, "description": "Played results or fixtures with missing scores."},
	}
	pages := object{
		"offset": object{"type": "integer", "minimum": 0, "default": 0},
		"limit":  object{"type": "integer", "minimum": 1, "maximum": 500, "default": 25},
	}
	playerFields := object{
		"name":               property("string", "Case- and accent-insensitive name or substring as recorded in FIFA."),
		"nationality":        property("string", "Country such as Brazil."),
		"club":               property("string", "FIFA club name, common alias, or substring."),
		"position":           property("string", "FIFA position code or forwards, midfielders, defenders, goalkeepers."),
		"brazilian_clubs":    property("boolean", "Restrict to clubs identified in Brazilian domestic match files."),
		"min_overall":        object{"type": "integer", "minimum": 0, "maximum": 100},
		"include_attributes": property("boolean", "Include available skill ratings, physical attributes, and other FIFA fields."),
		"group_by_club":      property("boolean", "Return counts and average FIFA overall by club."),
	}
	return []Tool{
		defineTool("search_matches", "Find fixtures and scores newest first, including match date, round/stage, teams, source, stadium and extended statistics when available. Use limit 1 for the latest meeting. Filter Libertadores by season and stage for bracket results.", withProperties(filters, pages), nil,
			func(s *Store, a MatchArgs) (object, error) {
				rows, err := s.findMatches(a.Filter)
				if err != nil {
					return nil, err
				}
				return paginate(a.Page, "matches", rows)
			}),
		defineTool("team_stats", "Compute a club's results, goals, win rate, competition history and season trends, including home and away splits. Supply opponent for head-to-head, with wins and losses relative to team.", filters, []string{"team"},
			func(s *Store, a Filter) (object, error) {
				if words(a.Team) == "" {
					return nil, fmt.Errorf("team is required")
				}
				rows, err := s.findMatches(a)
				if err != nil {
					return nil, err
				}
				result := teamStats(rows, a.Team)
				if a.Opponent != "" {
					result["opponent"] = clubName(a.Opponent)
					for i := range rows {
						if rows[i].played() {
							result["latest_played_match"] = rows[i]
							break
						}
					}
				}
				return result, nil
			}),
		defineTool("search_players", "Search the supplied FIFA player snapshot, ordered by overall rating. Includes club, nationality, position and potential. FIFA club affiliations and name spellings reflect this snapshot.", withProperties(playerFields, pages), nil,
			func(s *Store, a PlayerArgs) (object, error) {
				if a.MinOverall < 0 || a.MinOverall > 100 {
					return nil, fmt.Errorf("min_overall must be between 0 and 100")
				}
				rows := s.findPlayers(a.PlayerFilter)
				if a.GroupByClub {
					return paginate(a.Page, "clubs", clubRatings(rows))
				}
				return paginate(a.Page, "players", rows)
			}),
		defineTool("competition_standings", "Calculate Série A or Série B standings, leader and relegation places from recorded fixtures in a season. Includes a coverage flag. For knockout stages, use search_matches. Individual goal scorers are unavailable in the supplied files.", object{
			"season":      property("integer", "Season year."),
			"competition": property("string", "Defaults to Brasileirão Série A."),
		}, []string{"season"}, func(s *Store, a StandingArgs) (object, error) {
			if a.Season <= 0 {
				return nil, fmt.Errorf("a positive season is required")
			}
			competition := competitionName(a.Competition)
			if competition == "" {
				competition = serieA
			}
			if competition != serieA && competition != serieB {
				return nil, fmt.Errorf("standings are available for Brasileirão Série A and Série B; use search_matches for other competitions")
			}
			rows, err := s.findMatches(Filter{Season: a.Season, Competition: competition})
			if err != nil {
				return nil, err
			}
			return standings(rows, a.Season, competition), nil
		}),
		defineTool("analyze_matches", "Calculate goals per match, outcome rates and season comparisons, or rank teams by goals or win rate, or list the biggest wins. For best home or away record across clubs, supply side and use win_rate.", withProperties(withProperties(filters, pages), object{
			"metric":          object{"type": "string", "enum": []string{"summary", "goals_for", "win_rate", "biggest_wins"}, "default": "summary"},
			"minimum_matches": object{"type": "integer", "minimum": 1, "description": "Minimum played matches per team for a ranking."},
		}), nil, analyzeMatches),
		defineTool("club_profile", "Join a club's match record and competitions to the FIFA snapshot roster for the same club. Match filters affect the match record. The roster represents the FIFA snapshot.", withProperties(filters, pages), []string{"team"},
			func(s *Store, a ProfileArgs) (object, error) {
				if words(a.Team) == "" {
					return nil, fmt.Errorf("team is required")
				}
				rows, err := s.findMatches(a.Filter)
				if err != nil {
					return nil, err
				}
				players := s.findPlayers(PlayerFilter{Club: a.Team})
				key := words(clubName(a.Team))
				players = slices.DeleteFunc(players, func(p Player) bool { return p.clubKey != key })
				roster, err := paginate(a.Page, "players", players)
				if err != nil {
					return nil, err
				}
				return object{"matches": teamStats(rows, a.Team), "fifa_roster": roster}, nil
			}),
	}
}

type Victory struct {
	Margin int    `json:"margin"`
	Winner string `json:"winner"`
	Match
}

func analyzeMatches(s *Store, a AnalysisArgs) (object, error) {
	if a.MinimumMatches < 0 {
		return nil, fmt.Errorf("minimum_matches must be positive")
	}
	filter := a.Filter
	if filter.Team == "" && (filter.Side == "home" || filter.Side == "away") &&
		(a.Metric == "goals_for" || a.Metric == "win_rate") {
		filter.Side = ""
	}
	rows, err := s.findMatches(filter)
	if err != nil {
		return nil, err
	}
	switch a.Metric {
	case "", "summary":
		return summarize(rows), nil
	case "biggest_wins":
		wins := make([]Victory, 0)
		for _, m := range rows {
			if !m.played() {
				continue
			}
			margin, winner := *m.HomeGoals-*m.AwayGoals, m.Home
			if margin < 0 {
				margin, winner = -margin, m.Away
			}
			if margin > 0 {
				wins = append(wins, Victory{margin, winner, m})
			}
		}
		slices.SortStableFunc(wins, func(a, b Victory) int { return cmp.Compare(b.Margin, a.Margin) })
		return paginate(a.Page, "victories", wins)
	case "goals_for", "win_rate":
		records := teamRecords(rows, a.Side)
		team := words(clubName(a.Team))
		records = slices.DeleteFunc(records, func(r TeamRecord) bool {
			return r.Played < a.MinimumMatches || (team != "" && words(r.Team) != team)
		})
		slices.SortFunc(records, func(left, right TeamRecord) int {
			order := cmp.Compare(right.GoalsFor, left.GoalsFor)
			if a.Metric == "win_rate" {
				// Compare the exact win fractions without rounding.
				order = cmp.Compare(right.Wins*left.Played, left.Wins*right.Played)
			}
			return cmp.Or(order, cmp.Compare(right.Played, left.Played), cmp.Compare(left.Team, right.Team))
		})
		return paginate(a.Page, "teams", records)
	default:
		return nil, fmt.Errorf("unknown metric %q", a.Metric)
	}
}
