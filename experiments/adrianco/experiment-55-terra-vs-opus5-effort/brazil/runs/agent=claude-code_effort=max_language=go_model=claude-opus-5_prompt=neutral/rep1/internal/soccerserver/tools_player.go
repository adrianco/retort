// tools_player.go: player centred tools over fifa_data.csv, including the
// cross-file link from a FIFA club to the club in the match data.
package soccerserver

import (
	"fmt"
	"strings"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcp"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

func (a *api) searchPlayersTool() *mcp.Tool {
	return &mcp.Tool{
		Name:        "search_players",
		Title:       "Search players",
		Description: "Search the FIFA player database by name, nationality, club, position and rating. Answers \"Find all Brazilian players in the dataset\", \"Who are the top Brazilian players?\" and \"Show me all forwards from São Paulo FC\".",
		InputSchema: mcp.Object(map[string]*mcp.Prop{
			"name":        mcp.Str("Player name or part of it."),
			"nationality": mcp.Str("Exact nationality, e.g. \"Brazil\", \"Argentina\"."),
			"club":        mcp.Str("Club name as written in the player file, or a Brazilian club known to the match data."),
			"position":    mcp.Str("Position code (ST, GK, CAM, ...) or group (forward, midfielder, defender, goalkeeper)."),
			"min_overall": mcp.IntRange("Minimum FIFA overall rating.", 1, 99),
			"max_overall": mcp.IntRange("Maximum FIFA overall rating.", 1, 99),
			"min_age":     mcp.Int("Minimum age."),
			"max_age":     mcp.Int("Maximum age."),
			"sort":        mcp.Enum("Ordering (default overall_desc).", "overall_desc", "potential_desc", "age_asc", "age_desc", "name"),
			"limit":       mcp.IntRange("Maximum players to return (default 20, max 200).", 1, maxLimit),
			"offset":      mcp.Int("Number of players to skip, for paging."),
		}),
		Handler: a.searchPlayers,
	}
}

func (a *api) searchPlayers(args mcp.Args) (*mcp.ToolResult, error) {
	f := soccer.PlayerFilter{
		Name:        args.String("name"),
		Nationality: args.String("nationality"),
		Position:    args.String("position"),
		Sort:        args.String("sort"),
	}
	var err error
	if f.MinOverall, err = args.Int("min_overall", 0); err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	if f.MaxOverall, err = args.Int("max_overall", 0); err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	if f.MinAge, err = args.Int("min_age", 0); err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	if f.MaxAge, err = args.Int("max_age", 0); err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	if f.Offset, err = args.Int("offset", 0); err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	limit, res := limitArg(args, defaultLimit)
	if res != nil {
		return res, nil
	}
	f.Limit = limit

	var linkedTeam *soccer.Team
	if club := args.String("club"); club != "" {
		// Prefer the canonical club link so that "Atletico Mineiro",
		// "Atlético-MG" and "atletico-mg" all find the same squad.
		if team, _, err := a.store.ResolveTeam(club); err == nil && len(a.store.PlayersForTeam(team.ID)) > 0 {
			linkedTeam = team
			f.TeamID = team.ID
		} else {
			f.Club = club
		}
	}

	page := a.store.FindPlayers(f)
	title := playerSearchTitle(f, linkedTeam)
	text := soccer.FormatPlayers(title, page.Players, page.Total, f.Offset)
	if page.Total == 0 {
		text += a.emptyPlayerHint(f, args.String("club"))
	}
	return mcp.TextWithData(text, map[string]any{
		"total":   page.Total,
		"shown":   len(page.Players),
		"players": playersJSON(page.Players),
	}), nil
}

func playerSearchTitle(f soccer.PlayerFilter, team *soccer.Team) string {
	var parts []string
	if f.Name != "" {
		parts = append(parts, fmt.Sprintf("name matching %q", f.Name))
	}
	if f.Nationality != "" {
		parts = append(parts, f.Nationality)
	}
	if team != nil {
		parts = append(parts, "at "+team.Name)
	} else if f.Club != "" {
		parts = append(parts, "at clubs matching "+f.Club)
	}
	if f.Position != "" {
		parts = append(parts, "position "+f.Position)
	}
	if f.MinOverall > 0 {
		parts = append(parts, fmt.Sprintf("rated %d+", f.MinOverall))
	}
	if len(parts) == 0 {
		return "Players (FIFA dataset), best rated first:"
	}
	return "Players: " + strings.Join(parts, ", ") + ":"
}

// emptyPlayerHint explains why a player search came back empty. The FIFA file
// is a single 2019 snapshot and several big Brazilian clubs are missing from
// it, which is the most common surprise.
func (a *api) emptyPlayerHint(f soccer.PlayerFilter, clubArg string) string {
	var b strings.Builder
	if f.Name != "" {
		if sug := a.store.SuggestPlayers(f.Name, 5); len(sug) > 0 {
			fmt.Fprintf(&b, "Closest names in the player file: %s.\n", strings.Join(sug, ", "))
		} else {
			fmt.Fprintf(&b, "No player name close to %q exists in fifa_data.csv (a single 2019 snapshot of 18,207 players).\n", f.Name)
		}
	}
	if clubArg != "" {
		clubs := a.store.ClubSummaries(soccer.ClubFilter{Country: "BRA", MinPlayers: 1})
		names := make([]string, 0, len(clubs))
		for _, c := range clubs {
			names = append(names, c.Club)
		}
		fmt.Fprintf(&b, "The player file contains no squad for %q. Brazilian clubs it does contain: %s.\n",
			clubArg, strings.Join(names, ", "))
	}
	return b.String()
}

func (a *api) playerProfileTool() *mcp.Tool {
	return &mcp.Tool{
		Name:        "player_profile",
		Title:       "Player profile",
		Description: "Full detail for one player: ratings, position, club (linked to the match data when possible), physical attributes, contract and best skill ratings. Answers \"Who is Gabriel Barbosa?\".",
		InputSchema: mcp.Object(map[string]*mcp.Prop{
			"name":      mcp.Str("Player name or part of it."),
			"player_id": mcp.Int("FIFA player id, as returned by search_players."),
		}),
		Handler: a.playerProfile,
	}
}

func (a *api) playerProfile(args mcp.Args) (*mcp.ToolResult, error) {
	id, err := args.Int("player_id", 0)
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	var player *soccer.Player
	if id != 0 {
		player = a.store.Player(id)
		if player == nil {
			return mcp.ErrorResult("no player with FIFA id %d", id), nil
		}
	} else {
		name := args.String("name")
		if name == "" {
			return mcp.ErrorResult("give name or player_id"), nil
		}
		page := a.store.FindPlayers(soccer.PlayerFilter{Name: name, Limit: 10})
		if len(page.Players) == 0 {
			hint := a.emptyPlayerHint(soccer.PlayerFilter{Name: name}, "")
			return mcp.ErrorResult("no player called %q in fifa_data.csv.\n%s", name, hint), nil
		}
		player = page.Players[0]
		if page.Total > 1 {
			var others []string
			for _, p := range page.Players[1:] {
				others = append(others, fmt.Sprintf("%s (%d, %s)", p.Name, p.Overall, p.Club))
			}
			text := soccer.FormatPlayerProfile(player, a.store.Teams.Team(player.TeamID))
			text += fmt.Sprintf("\n%d other players match %q: %s\n", page.Total-1, name, strings.Join(others, "; "))
			return mcp.TextWithData(text, playersJSON([]*soccer.Player{player})[0]), nil
		}
	}
	team := a.store.Teams.Team(player.TeamID)
	text := soccer.FormatPlayerProfile(player, team)
	data := playersJSON([]*soccer.Player{player})[0]
	data["skills"] = player.Skills()
	data["node"] = string(soccer.PlayerNode(player.ID))
	if team != nil {
		rec := a.store.TeamRecord(team.ID, soccer.MatchFilter{})
		text += fmt.Sprintf("\nHis club %s has %d matches in the match data (%dW %dD %dL).\n",
			team.Name, rec.Matches, rec.Wins, rec.Draws, rec.Losses)
		data["club_record"] = rec
	}
	return mcp.TextWithData(text, data), nil
}

func (a *api) clubSquadsTool() *mcp.Tool {
	return &mcp.Tool{
		Name:        "club_squads",
		Title:       "Club squads",
		Description: "Aggregate the FIFA squads by club: squad size, average and best rating. With brazilian_only (the default) it lists the Brazilian clubs that the player file and the match data have in common.",
		InputSchema: mcp.Object(map[string]*mcp.Prop{
			"brazilian_only": mcp.Bool("Only clubs linked to the Brazilian match data (default true)."),
			"clubs":          mcp.StrArray("Specific clubs to report on."),
			"min_players":    mcp.Int("Ignore clubs with fewer players than this (default 1)."),
			"limit":          mcp.IntRange("Maximum clubs to list (default 30, max 200).", 1, maxLimit),
		}),
		Handler: a.clubSquads,
	}
}

func (a *api) clubSquads(args mcp.Args) (*mcp.ToolResult, error) {
	brazilianOnly, err := args.Bool("brazilian_only", true)
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	minPlayers, err := args.Int("min_players", 1)
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	limit, res := limitArg(args, 30)
	if res != nil {
		return res, nil
	}
	wanted := args.Strings("clubs")
	filter := soccer.ClubFilter{MinPlayers: minPlayers}
	if brazilianOnly && len(wanted) == 0 {
		filter.Country = "BRA"
	}
	summaries := a.store.ClubSummaries(filter)
	if len(wanted) > 0 {
		var filtered []soccer.ClubSummary
		taken := map[string]bool{} // overlapping patterns must not list a club twice
		for _, want := range wanted {
			var team *soccer.Team
			if t, _, err := a.store.ResolveTeam(want); err == nil {
				team = t
			}
			for _, c := range summaries {
				if taken[c.Club] {
					continue
				}
				if strings.Contains(soccer.Fold(c.Club), soccer.Fold(want)) || (team != nil && c.TeamID == team.ID) {
					taken[c.Club] = true
					filtered = append(filtered, c)
				}
			}
		}
		summaries = filtered
	}
	total := len(summaries)
	if len(summaries) > limit {
		summaries = summaries[:limit]
	}
	title := "Squads in the FIFA player file"
	if brazilianOnly && len(wanted) == 0 {
		title = "Brazilian clubs in the FIFA player file (linked to the match data)"
	}
	text := soccer.FormatClubSummaries(fmt.Sprintf("%s (%d of %d):", title, len(summaries), total), summaries)
	if brazilianOnly {
		text += "\nNote: FIFA 19 did not license the Brazilian league, so these squads use placeholder\n" +
			"player names, and clubs such as Flamengo, Palmeiras, Corinthians, São Paulo and Vasco\n" +
			"are absent from the player file entirely.\n"
	}
	return mcp.TextWithData(text, map[string]any{"clubs": summaries, "total": total}), nil
}
