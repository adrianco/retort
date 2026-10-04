package soccer

import "strings"

// Competition names as shown to the fan.
const (
	SerieA       = "Brasileirão Série A"
	SerieB       = "Brasileirão Série B"
	SerieC       = "Brasileirão Série C"
	CopaDoBrasil = "Copa do Brasil"
	Libertadores = "Copa Libertadores"
)

// AllCompetitions in the order they are usually listed.
var AllCompetitions = []string{SerieA, SerieB, SerieC, CopaDoBrasil, Libertadores}

// ParseCompetition understands the many ways a fan or a dataset names a
// competition. It returns "" when the text names none of them.
func ParseCompetition(s string) string {
	f := Fold(s)
	switch {
	case f == "":
		return ""
	case strings.Contains(f, "libertadores"):
		return Libertadores
	case strings.Contains(f, "copa do brasil"), strings.Contains(f, "brazil cup"), strings.Contains(f, "brazilian cup"),
		f == "cup", strings.Contains(f, "copa brasil"):
		return CopaDoBrasil
	case strings.Contains(f, "serie b"), strings.Contains(f, "série b"), f == "b":
		return SerieB
	case strings.Contains(f, "serie c"), f == "c":
		return SerieC
	case strings.Contains(f, "serie a"), strings.Contains(f, "brasileir"), strings.Contains(f, "campeonato brasileiro"),
		strings.Contains(f, "league"), f == "a":
		return SerieA
	}
	return ""
}
