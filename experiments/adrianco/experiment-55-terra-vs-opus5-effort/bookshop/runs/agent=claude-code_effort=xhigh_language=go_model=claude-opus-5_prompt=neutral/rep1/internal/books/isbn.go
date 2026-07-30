package books

import (
	"errors"
	"strings"
)

// errBadISBN is returned by NormalizeISBN for anything that is neither empty
// nor a well-formed ISBN. The text is user-facing: it ends up in the "details"
// map of a 422 response.
var errBadISBN = errors.New("isbn must be a valid ISBN-10 or ISBN-13")

// NormalizeISBN canonicalises an ISBN by stripping the separators publishers
// print it with (hyphens and spaces) and upper-casing an ISBN-10 check digit
// of "x". It then verifies the check digit.
//
// A blank string is valid and normalises to the empty string: the ISBN is
// optional. Storing the canonical form is what makes the uniqueness constraint
// meaningful — "0-306-40615-2" and "0306406152" are the same book.
func NormalizeISBN(raw string) (string, error) {
	// Blank means "not supplied". Note this is checked before the separators
	// are stripped, so a string of nothing but hyphens still fails below
	// rather than quietly becoming "no ISBN".
	if strings.TrimSpace(raw) == "" {
		return "", nil
	}

	var b strings.Builder
	b.Grow(len(raw))
	for _, r := range raw {
		switch {
		case r == '-' || r == ' ':
			// Separator, drop it.
		case r >= '0' && r <= '9':
			b.WriteRune(r)
		case r == 'x' || r == 'X':
			b.WriteRune('X')
		default:
			return "", errBadISBN
		}
	}

	isbn := b.String()
	switch len(isbn) {
	case 10:
		if !validISBN10(isbn) {
			return "", errBadISBN
		}
	case 13:
		if !validISBN13(isbn) {
			return "", errBadISBN
		}
	default:
		return "", errBadISBN
	}
	return isbn, nil
}

// validISBN10 reports whether isbn, already stripped to 10 characters, has a
// correct check digit: the weighted sum with weights 10..1 must be a multiple
// of 11. Only the final character may be the value-10 digit "X".
func validISBN10(isbn string) bool {
	sum := 0
	for i, r := range isbn {
		var digit int
		switch {
		case r >= '0' && r <= '9':
			digit = int(r - '0')
		case r == 'X' && i == 9:
			digit = 10
		default:
			return false
		}
		sum += (10 - i) * digit
	}
	return sum%11 == 0
}

// validISBN13 reports whether isbn, already stripped to 13 characters, has a
// correct check digit: the sum with alternating weights 1 and 3 must be a
// multiple of 10. "X" is not a legal ISBN-13 digit.
func validISBN13(isbn string) bool {
	sum := 0
	for i, r := range isbn {
		if r < '0' || r > '9' {
			return false
		}
		weight := 1
		if i%2 == 1 {
			weight = 3
		}
		sum += weight * int(r-'0')
	}
	return sum%10 == 0
}
