package api_test

import (
	"encoding/json"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"testing"
	"unicode"
	"unicode/utf8"

	"bookapi/internal/book"
)

// Both fuzz targets check one property: nothing a client sends may cause a 5xx.
// `go test` runs the seed corpus below as ordinary tests; explore further with
//
//	go test ./internal/api -run '^$' -fuzz FuzzBookBody -fuzztime 1m

func jsonOf(v any) string {
	b, err := json.Marshal(v)
	if err != nil {
		panic(err)
	}
	return string(b)
}

// checkAccepted verifies that a book the API stored obeys the documented rules.
func checkAccepted(t testing.TB, b bookJSON) {
	t.Helper()
	text := func(field, s string, max int) {
		switch {
		case s == "" || strings.TrimSpace(s) != s:
			t.Errorf("stored %s %q is empty or not trimmed", field, s)
		case !utf8.ValidString(s):
			t.Errorf("stored %s %q is not valid UTF-8", field, s)
		case utf8.RuneCountInString(s) > max:
			t.Errorf("stored %s is %d characters, over the limit of %d", field, utf8.RuneCountInString(s), max)
		case strings.IndexFunc(s, unicode.IsControl) >= 0:
			t.Errorf("stored %s %q contains a control character", field, s)
		}
	}
	text("title", b.Title, book.MaxTextLen)
	text("author", b.Author, book.MaxTextLen)
	if b.Year != nil && (*b.Year < book.MinYear || *b.Year > book.MaxYear) {
		t.Errorf("stored year %d is out of range", *b.Year)
	}
	if b.ISBN != nil {
		text("isbn", *b.ISBN, book.MaxISBNLen)
	}
}

// FuzzBookBody sends arbitrary request bodies to POST and PUT. A body is either
// refused with a JSON client error or stored, and a stored book must satisfy the
// rules and come back identically from GET and from an idempotent PUT.
func FuzzBookBody(f *testing.F) {
	h := newHandler(f)

	for _, seed := range []string{
		dune,
		`{"title":"T","author":"A"}`,
		`{"title":"  padded  ","author":"\tA\n","isbn":"   "}`,
		`{"title":"T","author":"A","year":0,"isbn":"x"}`,
		`{"title":"T","author":"A","year":-1}`,
		`{"title":"T","author":"A","year":10000}`,
		`{"title":"T","author":"A","year":1e2}`,
		`{"title":"T","author":"A","year":"1965"}`,
		`{"id":7,"title":"T","author":"A","unknown":[1,2,3]}`,
		`{"title":"Tom & Jerry <3 — 吾輩は猫である","author":"夏目 漱石"}`,
		"{\"title\":\"\xff\xfe\",\"author\":\"A\"}", // invalid UTF-8 inside a string
		jsonOf(map[string]any{"title": "\x00x", "author": "A"}),
		jsonOf(map[string]any{"title": "\x00", "author": "\x00"}),
		jsonOf(map[string]any{"title": "a\nb", "author": "A"}),
		jsonOf(map[string]any{"title": "\x1b[31mred", "author": "A"}),
		jsonOf(map[string]any{"title": strings.Repeat("x", 501), "author": "A"}),
		`{}`, `null`, `[]`, `""`, `42`, `{"title":`, ``, `{"title":"T","author":"A"}{}`, `{"title":"T","author":"A"} x`,
	} {
		f.Add(seed)
	}

	f.Fuzz(func(t *testing.T, body string) {
		rec := do(t, h, http.MethodPost, "/books", body)
		switch {
		case rec.Code == http.StatusCreated:
			b := decode[bookJSON](t, rec)
			checkAccepted(t, b)

			path := "/books/" + strconv.FormatInt(b.ID, 10)
			if got := do(t, h, http.MethodGet, path, ""); got.Code != http.StatusOK || got.Body.String() != rec.Body.String() {
				t.Fatalf("GET %s = %d %q, want the stored book %q", path, got.Code, got.Body, rec.Body)
			}
			if put := do(t, h, http.MethodPut, path, body); put.Code != http.StatusOK || put.Body.String() != rec.Body.String() {
				t.Fatalf("PUT %s = %d %q, want 200 and the same book %q", path, put.Code, put.Body, rec.Body)
			}
		case rec.Code >= 400 && rec.Code < 500:
			if got := decode[errorJSON](t, rec).Error; got == "" {
				t.Fatalf("POST %q was refused with %d but no error message", body, rec.Code)
			}
		default:
			t.Fatalf("POST %q = %d %s, want 201 or a client error", body, rec.Code, rec.Body)
		}

		// The same body aimed at a book that does not exist must not blow up either.
		if rec := do(t, h, http.MethodPut, "/books/999999999", body); rec.Code >= 500 {
			t.Fatalf("PUT of %q to a missing book = %d %s", body, rec.Code, rec.Body)
		}
	})
}

// ensureBooks tops the table up so that filters and ids have books to match even
// after an earlier iteration deleted them.
func ensureBooks(t testing.TB, h http.Handler) {
	t.Helper()
	if len(decode[[]bookJSON](t, do(t, h, http.MethodGet, "/books", ""))) >= 3 {
		return
	}
	for _, body := range []string{
		dune,
		`{"title":"Emma","author":"Jane Austen"}`,
		`{"title":"吾輩は猫である","author":"夏目 漱石","year":1905}`,
	} {
		create(t, h, body)
	}
}

// FuzzQueryAndPath uses arbitrary text as the ?author= filter and as the {id}
// path segment, with every method that accepts them.
func FuzzQueryAndPath(f *testing.F) {
	h := newHandler(f)
	ensureBooks(f, h)

	for _, seed := range []string{
		"", "1", "2", "0", "-1", "abc", "+1", "01", "1e3", "99999999999999999999",
		"Frank Herbert", "frank herbert", " Frank Herbert ", "Herbert",
		"%", "_", "' OR '1'='1", "x'; DROP TABLE books; --", " ", "1/2", "..", ".", "é", "\x00", "\xff",
	} {
		f.Add(seed)
	}

	f.Fuzz(func(t *testing.T, s string) {
		ensureBooks(t, h)
		for _, target := range []string{
			"/books?" + url.Values{"author": {s}}.Encode(),
			"/books/" + url.PathEscape(s),
		} {
			for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
				body := ""
				if method == http.MethodPut {
					body = dune
				}
				rec := do(t, h, method, target, body)
				if rec.Code >= 500 {
					t.Fatalf("%s %s = %d %s", method, target, rec.Code, rec.Body)
				}

				// Everything is JSON except empty 204s and the standard library's
				// own redirects for non-canonical paths such as "/books/..".
				if rec.Code == http.StatusNoContent || (rec.Code >= 300 && rec.Code < 400) {
					continue
				}
				if ct := rec.Header().Get("Content-Type"); ct != "application/json" || !json.Valid(rec.Body.Bytes()) {
					t.Fatalf("%s %s = %d with Content-Type %q and body %q, want JSON", method, target, rec.Code, ct, rec.Body)
				}
			}
		}
	})
}
