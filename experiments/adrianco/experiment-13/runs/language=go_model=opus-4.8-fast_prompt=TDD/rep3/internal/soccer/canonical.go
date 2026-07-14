// Context: Brazilian Soccer MCP Server.
// File: canonical.go
// Purpose: Canonicalize the major Brazilian clubs to a single display name.
// The datasets spell the same club many ways — state suffixes ("Gremio-RS"),
// space-separated state codes ("Botafogo RJ"), club-type tags ("Fortaleza
// FC"), and long forms ("Vasco da Gama", "Atletico Mineiro"). A token-rule
// table resolves the well-known top-flight clubs while leaving ambiguous cases
// (the two Atléticos) distinct. Unknown clubs fall back to a plain clean.
package soccer

import "strings"

// matchForm lowercases, strips accents and turns separators into spaces so a
// club's distinctive tokens (including its state code) can be tested by
// substring, regardless of how the source punctuated the name.
func matchForm(raw string) string {
	s := strings.ToLower(removeAccents(strings.TrimSpace(raw)))
	repl := strings.NewReplacer("-", " ", "(", " ", ")", " ", ".", " ", "/", " ")
	s = repl.Replace(s)
	return strings.TrimSpace(spacePattern.ReplaceAllString(s, " "))
}

// clubRule maps a set of required tokens to a canonical club name. A rule
// matches when every token in must is present in a name's match form.
type clubRule struct {
	canonical string
	must      []string
}

// clubRules are evaluated in order; the first match wins. Ambiguous clubs are
// listed with their state qualifier before any broader rule so they are never
// merged with a same-named club from another state.
var clubRules = []clubRule{
	// The two Atléticos: distinguished by spelling ("athletico") and state.
	{"Athletico-PR", []string{"athletico"}},
	{"Athletico-PR", []string{"atletico", "pr"}},
	{"Athletico-PR", []string{"atletico", "paranaense"}},
	{"Atlético-MG", []string{"atletico", "mg"}},
	{"Atlético-MG", []string{"atletico", "mineiro"}},
	{"Atlético-GO", []string{"atletico", "go"}},
	{"Atlético-GO", []string{"atletico", "goianiense"}},
	{"América-MG", []string{"america", "mg"}},
	{"América-MG", []string{"america", "mineiro"}},
	{"Botafogo-RJ", []string{"botafogo", "rj"}},

	// Unambiguous top-flight clubs (single distinctive token).
	{"Flamengo", []string{"flamengo"}},
	{"Fluminense", []string{"fluminense"}},
	{"Vasco", []string{"vasco"}},
	{"Palmeiras", []string{"palmeiras"}},
	{"Santos", []string{"santos"}},
	{"Corinthians", []string{"corinthians"}},
	{"São Paulo", []string{"sao paulo"}},
	{"Grêmio", []string{"gremio"}},
	{"Internacional", []string{"internacional"}},
	{"Cruzeiro", []string{"cruzeiro"}},
	{"Bahia", []string{"bahia"}},
	{"Fortaleza", []string{"fortaleza"}},
	{"Ceará", []string{"ceara"}},
	{"Goiás", []string{"goias"}},
	{"Avaí", []string{"avai"}},
	{"Chapecoense", []string{"chapecoense"}},
	{"Coritiba", []string{"coritiba"}},
	{"Bragantino", []string{"bragantino"}},
	{"Cuiabá", []string{"cuiaba"}},
	{"Vitória", []string{"vitoria"}},
	{"Ponte Preta", []string{"ponte preta"}},
	{"Figueirense", []string{"figueirense"}},
	{"Juventude", []string{"juventude"}},
	{"Sport Recife", []string{"sport", "recife"}},
	{"CSA", []string{"csa"}},
}

// CanonicalName returns the canonical display name for a raw team string,
// collapsing known spelling variants. Unknown clubs are returned via
// CleanTeamName so nothing is lost.
func CanonicalName(raw string) string {
	form := matchForm(raw)
	for _, rule := range clubRules {
		if allContained(form, rule.must) {
			return rule.canonical
		}
	}
	return CleanTeamName(raw)
}

func allContained(form string, tokens []string) bool {
	for _, tok := range tokens {
		if !strings.Contains(form, tok) {
			return false
		}
	}
	return true
}
