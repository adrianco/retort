package datautil

import "strings"

// NormalizeTeam removes state suffixes, lowercases, and trims for consistent comparison.
func NormalizeTeam(name string) string {
	if name == "" {
		return ""
	}
	n := strings.ToLower(strings.TrimSpace(name))
	stateSuffs := []string{
		"-sp", "-rj", "-mg", "-pr", "-rs", "-ba", "-ce", "-pe",
		"-es", "-go", "-ma", "-pa", "-mt", "-ms", "-df", "-ac",
		"-am", "-rr", "-ro", "-to", "-ap",
	}
	for _, s := range stateSuffs {
		if strings.HasSuffix(n, s) {
			n = strings.TrimSuffix(n, s)
		}
	}
	n = strings.Join(strings.Fields(n), " ")
	return n
}

func MustContain(normalizedHaystack, normalizedNeedle string) bool {
	return strings.Contains(normalizedHaystack, normalizedNeedle)
}
