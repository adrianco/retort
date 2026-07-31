// rivalry.go encodes the classic Brazilian derbies ("clássicos"). The datasets
// carry no notion of a rivalry, so this is curated domain knowledge that lets
// the server answer questions such as "show me all derbies in 2023".
package soccer

import "sort"

// Rivalry names a traditional fixture between two clubs.
type Rivalry struct {
	Name    string `json:"name"`
	TeamAID string `json:"-"`
	TeamBID string `json:"-"`
	TeamA   string `json:"team_a"`
	TeamB   string `json:"team_b"`
	Region  string `json:"region"`
	Note    string `json:"note,omitempty"`
}

var rivalries = []Rivalry{
	{Name: "Fla-Flu", TeamAID: "flamengo-rj", TeamBID: "fluminense-rj", Region: "Rio de Janeiro"},
	{Name: "Clássico dos Milhões", TeamAID: "flamengo-rj", TeamBID: "vascogama-rj", Region: "Rio de Janeiro"},
	{Name: "Clássico da Rivalidade", TeamAID: "flamengo-rj", TeamBID: "botafogo-rj", Region: "Rio de Janeiro"},
	{Name: "Clássico Vovô", TeamAID: "botafogo-rj", TeamBID: "fluminense-rj", Region: "Rio de Janeiro"},
	{Name: "Clássico da Amizade", TeamAID: "botafogo-rj", TeamBID: "vascogama-rj", Region: "Rio de Janeiro"},
	{Name: "Clássico dos Gigantes", TeamAID: "fluminense-rj", TeamBID: "vascogama-rj", Region: "Rio de Janeiro"},
	{Name: "Derby Paulista", TeamAID: "corinthians-sp", TeamBID: "palmeiras-sp", Region: "São Paulo"},
	{Name: "Majestoso", TeamAID: "corinthians-sp", TeamBID: "saopaulo-sp", Region: "São Paulo"},
	{Name: "Clássico Alvinegro", TeamAID: "corinthians-sp", TeamBID: "santos-sp", Region: "São Paulo"},
	{Name: "Choque-Rei", TeamAID: "palmeiras-sp", TeamBID: "saopaulo-sp", Region: "São Paulo"},
	{Name: "Clássico da Saudade", TeamAID: "palmeiras-sp", TeamBID: "santos-sp", Region: "São Paulo"},
	{Name: "San-São", TeamAID: "santos-sp", TeamBID: "saopaulo-sp", Region: "São Paulo"},
	{Name: "Gre-Nal", TeamAID: "gremio-rs", TeamBID: "internacional-rs", Region: "Rio Grande do Sul"},
	{Name: "Clássico Mineiro", TeamAID: "atletico-mg", TeamBID: "cruzeiro-mg", Region: "Minas Gerais"},
	{Name: "Atletiba", TeamAID: "atletico-pr", TeamBID: "coritiba-pr", Region: "Paraná"},
	{Name: "Clássico-Rei", TeamAID: "ceara-ce", TeamBID: "fortaleza-ce", Region: "Ceará"},
	{Name: "Ba-Vi", TeamAID: "bahia-ba", TeamBID: "vitoria-ba", Region: "Bahia"},
	{Name: "Clássico dos Clássicos", TeamAID: "nautico-pe", TeamBID: "sport-pe", Region: "Pernambuco"},
	{Name: "Clássico das Multidões", TeamAID: "nautico-pe", TeamBID: "santacruz-pe", Region: "Pernambuco"},
	{Name: "Clássico das Emoções", TeamAID: "santacruz-pe", TeamBID: "sport-pe", Region: "Pernambuco"},
}

var rivalryByPair = func() map[string]Rivalry {
	m := make(map[string]Rivalry, len(rivalries))
	for _, r := range rivalries {
		m[pairKey(r.TeamAID, r.TeamBID)] = r
	}
	return m
}()

// RivalryFor returns the derby name for a pair of clubs, if there is one.
func RivalryFor(a, b string) (Rivalry, bool) {
	r, ok := rivalryByPair[pairKey(a, b)]
	return r, ok
}

// Rivalries lists the curated derbies, annotated with the clubs' display names
// and how many meetings the datasets contain.
func (g *Graph) Rivalries() []Rivalry {
	out := make([]Rivalry, 0, len(rivalries))
	for _, r := range rivalries {
		a, aok := g.Teams[r.TeamAID]
		b, bok := g.Teams[r.TeamBID]
		if !aok || !bok {
			continue
		}
		r.TeamA, r.TeamB = a.Name, b.Name
		out = append(out, r)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Region != out[j].Region {
			return out[i].Region < out[j].Region
		}
		return out[i].Name < out[j].Name
	})
	return out
}
