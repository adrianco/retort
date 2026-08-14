package main

import (
	"regexp"
	"sort"
	"strings"
	"unicode"
)

type teamName struct {
	base  string
	state string
}

var brazilianStateSuffix = regexp.MustCompile(`(?i)\s*-\s*(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\s*$`)
var brazilianStateWordSuffix = regexp.MustCompile(`(?i)\s+(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\s*$`)

// normalizeText makes comparisons accent-, punctuation-, case-, and whitespace-
// insensitive while retaining words needed to distinguish similarly named clubs.
func normalizeText(value string) string {
	value = strings.TrimPrefix(value, "\ufeff")
	value = strings.ToLower(strings.TrimSpace(value))
	value = strings.Map(func(r rune) rune {
		switch r {
		case 'á', 'à', 'â', 'ã', 'ä', 'å':
			return 'a'
		case 'é', 'è', 'ê', 'ë':
			return 'e'
		case 'í', 'ì', 'î', 'ï':
			return 'i'
		case 'ó', 'ò', 'ô', 'õ', 'ö':
			return 'o'
		case 'ú', 'ù', 'û', 'ü':
			return 'u'
		case 'ç':
			return 'c'
		case 'ñ':
			return 'n'
		}
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			return r
		}
		return ' '
	}, value)
	return strings.Join(strings.Fields(value), " ")
}

func parseTeamName(value string) teamName {
	trimmed := strings.TrimSpace(strings.ToLower(strings.TrimPrefix(value, "\ufeff")))
	state := ""
	if parts := brazilianStateSuffix.FindStringSubmatch(trimmed); len(parts) == 2 {
		state = strings.ToUpper(parts[1])
		trimmed = brazilianStateSuffix.ReplaceAllString(trimmed, "")
	} else if parts := brazilianStateWordSuffix.FindStringSubmatch(trimmed); len(parts) == 2 {
		state = strings.ToUpper(parts[1])
		trimmed = brazilianStateWordSuffix.ReplaceAllString(trimmed, "")
	}
	base := normalizeText(trimmed)
	base = removeTeamSuffixes(base)
	parsed := teamName{base: base, state: state}
	return applyTeamAlias(parsed)
}

func removeTeamSuffixes(value string) string {
	words := strings.Fields(value)
	for len(words) > 1 {
		last := words[len(words)-1]
		if last != "fc" && last != "f" && last != "c" {
			break
		}
		words = words[:len(words)-1]
	}
	return strings.Join(words, " ")
}

func applyTeamAlias(team teamName) teamName {
	switch team.base {
	case "athletico paranaense", "atletico paranaense":
		team.base = "atletico"
		if team.state == "" {
			team.state = "PR"
		}
	case "atletico mineiro":
		team.base = "atletico"
		if team.state == "" {
			team.state = "MG"
		}
	case "atletico goianiense":
		team.base = "atletico"
		if team.state == "" {
			team.state = "GO"
		}
	case "ec bahia", "esporte clube bahia":
		team.base = "bahia"
		if team.state == "" {
			team.state = "BA"
		}
	case "red bull bragantino", "bragantino":
		team.base = "bragantino"
		if team.state == "" {
			team.state = "SP"
		}
	case "sport recife":
		team.base = "sport"
		if team.state == "" {
			team.state = "PE"
		}
	case "ec juventude", "esporte clube juventude":
		team.base = "juventude"
		if team.state == "" {
			team.state = "RS"
		}
	case "america mineiro":
		team.base = "america"
		if team.state == "" {
			team.state = "MG"
		}
	case "club de regatas do flamengo":
		team.base = "flamengo"
	case "sport club corinthians paulista", "sc corinthians paulista":
		team.base = "corinthians"
	case "sao paulo futebol clube":
		team.base = "sao paulo"
	case "gremio foot ball porto alegrense":
		team.base = "gremio"
	}
	return team
}

func teamMatches(candidate, query string) bool {
	candidateName := parseTeamName(candidate)
	queryName := parseTeamName(query)
	if candidateName.base == "" || queryName.base == "" {
		return false
	}
	// A supplied state is a disambiguator when both datasets provide one. A
	// source without state information remains compatible rather than silently
	// disappearing from a cross-file query.
	if queryName.state != "" {
		if candidateName.state != "" && queryName.state != candidateName.state {
			return false
		}
		// A state-qualified short name (for example Atlético-PR) must not
		// expand to a longer, state-less but differently named club (such as
		// Atlético Mineiro). Exact base-name matches remain compatible with
		// sources that simply omit state information (for example Flamengo).
		if candidateName.state == "" && candidateName.base != queryName.base {
			return false
		}
	}
	if candidateName.base == queryName.base {
		return true
	}
	if strings.Contains(candidateName.base, queryName.base) || strings.Contains(queryName.base, candidateName.base) {
		return true
	}
	return tokenSubset(queryName.base, candidateName.base)
}

func tokenSubset(needle, haystack string) bool {
	needleWords := strings.Fields(needle)
	if len(needleWords) == 0 {
		return false
	}
	haystackWords := make(map[string]struct{}, len(strings.Fields(haystack)))
	for _, word := range strings.Fields(haystack) {
		haystackWords[word] = struct{}{}
	}
	for _, word := range needleWords {
		if _, ok := haystackWords[word]; !ok {
			return false
		}
	}
	return true
}

func displayTeam(value string) string {
	// Keep the source display name intact. State suffixes distinguish real clubs
	// such as Atlético-MG and Atlético-PR; normalization belongs in matching, not
	// in an outward-facing result that could otherwise become ambiguous.
	return strings.TrimSpace(value)
}

func normalizedCompetition(value string) string {
	key := normalizeText(value)
	switch {
	case strings.Contains(key, "libertadores"):
		return "libertadores"
	case strings.Contains(key, "copa do brasil"):
		return "copa do brasil"
	case strings.Contains(key, "serie b"):
		return "serie b"
	case strings.Contains(key, "serie c"):
		return "serie c"
	case strings.Contains(key, "brasileirao"), key == "serie a", key == "serie a brasil", strings.Contains(key, "campeonato brasileiro serie a"):
		return "brasileirao"
	default:
		return key
	}
}

func canonicalCompetition(value string) string {
	switch normalizedCompetition(value) {
	case "brasileirao":
		return "Brasileirão"
	case "copa do brasil":
		return "Copa do Brasil"
	case "libertadores":
		return "Copa Libertadores"
	default:
		return strings.TrimSpace(value)
	}
}

func sourceKey(value string) string {
	value = strings.TrimSpace(value)
	if strings.HasSuffix(strings.ToLower(value), ".csv") {
		value = value[:len(value)-len(".csv")]
	}
	return normalizeText(value)
}

func uniqueStrings(values []string) []string {
	seen := make(map[string]struct{}, len(values))
	for _, value := range values {
		if value != "" {
			seen[value] = struct{}{}
		}
	}
	result := make([]string, 0, len(seen))
	for value := range seen {
		result = append(result, value)
	}
	sort.Strings(result)
	return result
}
