package query

import (
	"sort"
	"strings"

	"soccer-mcp/models"
)

// PlayerQuery handles player-related queries
type PlayerQuery struct {
	store *models.DataStore
}

// NewPlayerQuery creates a new PlayerQuery instance
func NewPlayerQuery(store *models.DataStore) *PlayerQuery {
	return &PlayerQuery{store: store}
}

// FindPlayersByName searches for players by name
func (q *PlayerQuery) FindPlayersByName(name string, limit int) ([]models.Player, error) {
	var players []models.Player
	name = strings.ToLower(name)

	for _, player := range q.store.Players {
		if strings.Contains(strings.ToLower(player.Name), name) {
			players = append(players, player)
		}
	}

	// Sort by overall rating (descending)
	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})

	if limit > 0 && len(players) > limit {
		players = players[:limit]
	}

	return players, nil
}

// FindPlayersByNationality finds players by nationality
func (q *PlayerQuery) FindPlayersByNationality(nationality string, limit int) ([]models.Player, error) {
	var players []models.Player
	nationality = strings.ToLower(nationality)

	for _, player := range q.store.Players {
		if strings.Contains(strings.ToLower(player.Nationality), nationality) {
			players = append(players, player)
		}
	}

	// Sort by overall rating (descending)
	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})

	if limit > 0 && len(players) > limit {
		players = players[:limit]
	}

	return players, nil
}

// FindPlayersByClub finds players by club
func (q *PlayerQuery) FindPlayersByClub(club string, limit int) ([]models.Player, error) {
	var players []models.Player
	club = normalizeTeamName(club)

	for _, player := range q.store.Players {
		if strings.Contains(strings.ToLower(player.Club), club) {
			players = append(players, player)
		}
	}

	// Sort by overall rating (descending)
	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})

	if limit > 0 && len(players) > limit {
		players = players[:limit]
	}

	return players, nil
}

// FindPlayersByPosition finds players by position
func (q *PlayerQuery) FindPlayersByPosition(position string, limit int) ([]models.Player, error) {
	var players []models.Player
	position = strings.ToLower(position)

	for _, player := range q.store.Players {
		if strings.Contains(strings.ToLower(player.Position), position) {
			players = append(players, player)
		}
	}

	// Sort by overall rating (descending)
	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})

	if limit > 0 && len(players) > limit {
		players = players[:limit]
	}

	return players, nil
}

// FindTopBrazilianPlayers finds top Brazilian players
func (q *PlayerQuery) FindTopBrazilianPlayers(limit int) ([]models.Player, error) {
	var players []models.Player

	for _, player := range q.store.Players {
		if strings.Contains(strings.ToLower(player.Nationality), "brazil") ||
			strings.Contains(strings.ToLower(player.Nationality), "brasil") ||
			strings.Contains(strings.ToLower(player.Nationality), "brazillian") {
			players = append(players, player)
		}
	}

	// Sort by overall rating (descending)
	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})

	if limit > 0 && len(players) > limit {
		players = players[:limit]
	}

	return players, nil
}

// FindPlayersByClubAndPosition finds players at a club in a specific position
func (q *PlayerQuery) FindPlayersByClubAndPosition(club, position string, limit int) ([]models.Player, error) {
	var players []models.Player
	club = normalizeTeamName(club)
	position = strings.ToLower(position)

	for _, player := range q.store.Players {
		if strings.Contains(strings.ToLower(player.Club), club) &&
			strings.Contains(strings.ToLower(player.Position), position) {
			players = append(players, player)
		}
	}

	// Sort by overall rating (descending)
	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})

	if limit > 0 && len(players) > limit {
		players = players[:limit]
	}

	return players, nil
}

// GetClubStats calculates average rating for players at a club
func (q *PlayerQuery) GetClubStats(club string) (*models.TeamStats, error) {
	club = normalizeTeamName(club)
	stats := &models.TeamStats{
		TeamName: club,
	}

	var ratings []int
	for _, player := range q.store.Players {
		if strings.Contains(strings.ToLower(player.Club), club) {
			ratings = append(ratings, player.Overall)
			stats.Matches++ // Using Matches to count players
		}
	}

	if len(ratings) == 0 {
		return stats, nil
	}

	// Calculate average rating
	var total int
	for _, r := range ratings {
		total += r
	}
	avg := float64(total) / float64(len(ratings))

	// Estimate stats from average rating
	stats.Wins = int(avg / 30)  // Rough estimation
	stats.Draws = int(avg / 30)
	stats.Losses = int(avg / 30)
	stats.Points = stats.Wins*3 + stats.Draws

	return stats, nil
}

// GetTopScorers finds players with highest shooting skills
func (q *PlayerQuery) GetTopScorers(limit int) ([]models.Player, error) {
	// Create a copy of players sorted by shooting
	players := make([]models.Player, len(q.store.Players))
	copy(players, q.store.Players)

	sort.Slice(players, func(i, j int) bool {
		return players[i].Shooting > players[j].Shooting
	})

	if limit > 0 && len(players) > limit {
		players = players[:limit]
	}

	return players, nil
}

// GetTopPlayersByPosition finds top players by position
func (q *PlayerQuery) GetTopPlayersByPosition(position string, limit int) ([]models.Player, error) {
	var players []models.Player
	position = strings.ToLower(position)

	for _, player := range q.store.Players {
		if strings.Contains(strings.ToLower(player.Position), position) {
			players = append(players, player)
		}
	}

	// Sort by overall rating (descending)
	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})

	if limit > 0 && len(players) > limit {
		players = players[:limit]
	}

	return players, nil
}

// GetHighestPotentialPlayers finds players with highest potential
func (q *PlayerQuery) GetHighestPotentialPlayers(limit int) ([]models.Player, error) {
	players := make([]models.Player, len(q.store.Players))
	copy(players, q.store.Players)

	sort.Slice(players, func(i, j int) bool {
		return players[i].Potential > players[j].Potential
	})

	if limit > 0 && len(players) > limit {
		players = players[:limit]
	}

	return players, nil
}
