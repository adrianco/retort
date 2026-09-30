package api_test

import (
	"encoding/json"
	"log/slog"
	"maps"
	"net/http"
	"net/http/httptest"
	"net/url"
	"path/filepath"
	"strconv"
	"strings"
	"testing"

	"bookapi/internal/api"
	"bookapi/internal/book"
	"bookapi/internal/store"
)

// errorResponse mirrors the JSON error body the API returns.
type errorResponse struct {
	Error   string            `json:"error"`
	Details map[string]string `json:"details"`
}

var discardLogger = slog.New(slog.DiscardHandler)

// newStore opens a real SQLite database in a temporary directory.
func newStore(t *testing.T) *store.Store {
	t.Helper()
	st, err := store.Open(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("store.Open: %v", err)
	}
	t.Cleanup(func() { st.Close() })
	return st
}

// newAPI returns the API backed by a real database, so these tests exercise
// routing, validation and storage together.
func newAPI(t *testing.T) http.Handler {
	t.Helper()
	return api.New(newStore(t), discardLogger)
}

// send performs one request against h. Every response except 204 must be JSON.
func send(t *testing.T, h http.Handler, method, target, body string) *httptest.ResponseRecorder {
	t.Helper()
	var r *http.Request
	if body == "" {
		r = httptest.NewRequest(method, target, nil)
	} else {
		r = httptest.NewRequest(method, target, strings.NewReader(body))
		r.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, r)

	if rec.Code != http.StatusNoContent {
		if got := rec.Header().Get("Content-Type"); got != "application/json" {
			t.Errorf("%s %s: Content-Type = %q, want application/json (status %d, body %q)",
				method, target, got, rec.Code, rec.Body.String())
		}
	}
	return rec
}

func wantStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d; body: %s", rec.Code, want, rec.Body.String())
	}
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("response is not valid JSON for %T: %v\nbody: %s", v, err, rec.Body.String())
	}
	return v
}

// mustCreate posts a book and returns it as stored.
func mustCreate(t *testing.T, h http.Handler, title, author string, year int, isbn string) book.Book {
	t.Helper()
	body, _ := json.Marshal(book.Input{Title: title, Author: author, Year: year, ISBN: isbn})
	rec := send(t, h, http.MethodPost, "/books", string(body))
	wantStatus(t, rec, http.StatusCreated)
	return decode[book.Book](t, rec)
}

func bookURL(id int64) string { return "/books/" + strconv.FormatInt(id, 10) }

func TestHealth(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	rec := send(t, h, http.MethodGet, "/health", "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[map[string]string](t, rec); got["status"] != "ok" {
		t.Errorf("body = %v, want status ok", got)
	}
}

func TestCreateBook(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	rec := send(t, h, http.MethodPost, "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}`)
	wantStatus(t, rec, http.StatusCreated)

	got := decode[book.Book](t, rec)
	want := book.Book{ID: got.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0441013593"}
	if got.ID <= 0 {
		t.Errorf("ID = %d, want a positive server-assigned ID", got.ID)
	}
	if got != want {
		t.Errorf("created = %+v, want %+v", got, want)
	}
	if loc := rec.Header().Get("Location"); loc != bookURL(got.ID) {
		t.Errorf("Location = %q, want %q", loc, bookURL(got.ID))
	}

	// The book is really stored, not just echoed back.
	fetched := send(t, h, http.MethodGet, bookURL(got.ID), "")
	wantStatus(t, fetched, http.StatusOK)
	if stored := decode[book.Book](t, fetched); stored != want {
		t.Errorf("stored = %+v, want %+v", stored, want)
	}
}

func TestBookJSONShape(t *testing.T) {
	t.Parallel()
	h := newAPI(t)
	b := mustCreate(t, h, "Dune", "Frank Herbert", 1965, "978")

	rec := send(t, h, http.MethodGet, bookURL(b.ID), "")
	wantStatus(t, rec, http.StatusOK)

	var raw map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &raw); err != nil {
		t.Fatal(err)
	}
	want := map[string]any{"id": float64(b.ID), "title": "Dune", "author": "Frank Herbert", "year": float64(1965), "isbn": "978"}
	if !maps.Equal(raw, want) {
		t.Errorf("JSON = %v, want exactly the fields %v", raw, want)
	}
}

func TestCreateBookOptionalFieldsMayBeOmitted(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	rec := send(t, h, http.MethodPost, "/books", `{"title":"Untitled","author":"Anon"}`)
	wantStatus(t, rec, http.StatusCreated)
	got := decode[book.Book](t, rec)
	if got.Year != 0 || got.ISBN != "" {
		t.Errorf("year = %d, isbn = %q; want 0 and empty when omitted", got.Year, got.ISBN)
	}
}

func TestCreateBookTrimsWhitespace(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	rec := send(t, h, http.MethodPost, "/books", `{"title":"  Dune \n","author":"\tFrank Herbert  "}`)
	wantStatus(t, rec, http.StatusCreated)
	got := decode[book.Book](t, rec)
	if got.Title != "Dune" || got.Author != "Frank Herbert" {
		t.Errorf("stored title %q, author %q; want surrounding whitespace trimmed", got.Title, got.Author)
	}
}

func TestCreateBookAcceptsRequestWithoutContentType(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	// curl -d sends application/x-www-form-urlencoded; the body is JSON regardless.
	r := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader(`{"title":"T","author":"A"}`))
	r.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, r)
	wantStatus(t, rec, http.StatusCreated)
}

func TestCreateBookIgnoresClientSuppliedID(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	rec := send(t, h, http.MethodPost, "/books", `{"id":99,"title":"T","author":"A"}`)
	wantStatus(t, rec, http.StatusCreated)
	if got := decode[book.Book](t, rec); got.ID == 99 {
		t.Errorf("ID = 99: a client-supplied id must be ignored")
	}
	wantStatus(t, send(t, h, http.MethodGet, "/books/99", ""), http.StatusNotFound)
}

func TestCreateBookValidation(t *testing.T) {
	t.Parallel()
	longTitle := strings.Repeat("x", book.MaxTextLength+1)

	tests := []struct {
		name        string
		body        string
		wantError   string
		wantDetails map[string]string
	}{
		{
			name:        "title missing",
			body:        `{"author":"Frank Herbert"}`,
			wantError:   "validation failed",
			wantDetails: map[string]string{"title": "is required"},
		},
		{
			name:        "author missing",
			body:        `{"title":"Dune"}`,
			wantError:   "validation failed",
			wantDetails: map[string]string{"author": "is required"},
		},
		{
			name:        "both empty",
			body:        `{"title":"","author":""}`,
			wantError:   "validation failed",
			wantDetails: map[string]string{"title": "is required", "author": "is required"},
		},
		{
			name:        "title is only whitespace",
			body:        `{"title":"   ","author":"A"}`,
			wantError:   "validation failed",
			wantDetails: map[string]string{"title": "is required"},
		},
		{
			name:        "title is null",
			body:        `{"title":null,"author":"A"}`,
			wantError:   "validation failed",
			wantDetails: map[string]string{"title": "is required"},
		},
		{
			name:        "empty object",
			body:        `{}`,
			wantError:   "validation failed",
			wantDetails: map[string]string{"title": "is required", "author": "is required"},
		},
		{
			name:        "title too long",
			body:        `{"title":"` + longTitle + `","author":"A"}`,
			wantError:   "validation failed",
			wantDetails: map[string]string{"title": "must be at most 255 characters"},
		},
		{
			name:        "year negative",
			body:        `{"title":"T","author":"A","year":-1}`,
			wantError:   "validation failed",
			wantDetails: map[string]string{"year": "must be between 0 and 9999"},
		},
		{
			name:        "year too large",
			body:        `{"title":"T","author":"A","year":10000}`,
			wantError:   "validation failed",
			wantDetails: map[string]string{"year": "must be between 0 and 9999"},
		},
		{
			name:        "isbn too long",
			body:        `{"title":"T","author":"A","isbn":"` + strings.Repeat("9", book.MaxISBNLength+1) + `"}`,
			wantError:   "validation failed",
			wantDetails: map[string]string{"isbn": "must be at most 32 characters"},
		},
		{name: "year is a string", body: `{"title":"T","author":"A","year":"1999"}`, wantError: `field "year": expected int but got string`},
		{name: "year is fractional", body: `{"title":"T","author":"A","year":1999.5}`, wantError: `field "year": expected int but got number 1999.5`},
		{name: "title is a number", body: `{"title":42,"author":"A"}`, wantError: `field "title": expected string but got number`},
		{name: "malformed JSON", body: `{"title":`, wantError: "request body is not valid JSON"},
		{name: "not JSON at all", body: `title=Dune&author=Herbert`, wantError: "request body is not valid JSON"},
		{name: "array instead of object", body: `[{"title":"T","author":"A"}]`, wantError: "request body must be a single JSON object"},
		{name: "scalar instead of object", body: `"Dune"`, wantError: "request body must be a single JSON object"},
		{name: "two objects", body: `{"title":"T","author":"A"}{"title":"U","author":"B"}`, wantError: "request body must be a single JSON object"},
		{name: "object followed by garbage", body: `{"title":"T","author":"A"} nope`, wantError: "request body is not valid JSON"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			h := newAPI(t)

			rec := send(t, h, http.MethodPost, "/books", tt.body)
			wantStatus(t, rec, http.StatusBadRequest)

			got := decode[errorResponse](t, rec)
			if got.Error != tt.wantError {
				t.Errorf("error = %q, want %q", got.Error, tt.wantError)
			}
			if !maps.Equal(got.Details, tt.wantDetails) {
				t.Errorf("details = %v, want %v", got.Details, tt.wantDetails)
			}

			// A rejected request must not leave anything behind.
			if body := send(t, h, http.MethodGet, "/books", "").Body.String(); strings.TrimSpace(body) != "[]" {
				t.Errorf("GET /books after rejected create = %s, want []", body)
			}
		})
	}
}

func TestCreateBookEmptyBody(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	rec := send(t, h, http.MethodPost, "/books", "")
	wantStatus(t, rec, http.StatusBadRequest)
	if got := decode[errorResponse](t, rec); got.Error != "request body must not be empty" {
		t.Errorf("error = %q", got.Error)
	}
}

func TestCreateBookRejectsOversizedBody(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	huge := `{"title":"` + strings.Repeat("x", 2<<20) + `","author":"A"}`
	wantStatus(t, send(t, h, http.MethodPost, "/books", huge), http.StatusRequestEntityTooLarge)
}

func TestListBooksWhenEmptyReturnsEmptyArray(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	rec := send(t, h, http.MethodGet, "/books", "")
	wantStatus(t, rec, http.StatusOK)
	if body := strings.TrimSpace(rec.Body.String()); body != "[]" {
		t.Errorf("body = %s, want [] (not null)", body)
	}
}

func TestListBooks(t *testing.T) {
	t.Parallel()
	h := newAPI(t)
	first := mustCreate(t, h, "Dune", "Frank Herbert", 1965, "")
	second := mustCreate(t, h, "Emma", "Jane Austen", 1815, "")
	third := mustCreate(t, h, "Children of Dune", "Frank Herbert", 1976, "")

	rec := send(t, h, http.MethodGet, "/books", "")
	wantStatus(t, rec, http.StatusOK)

	got := decode[[]book.Book](t, rec)
	want := []book.Book{first, second, third}
	if len(got) != len(want) {
		t.Fatalf("got %d books, want %d: %+v", len(got), len(want), got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Errorf("book[%d] = %+v, want %+v", i, got[i], want[i])
		}
	}
}

func TestListBooksFiltersByAuthor(t *testing.T) {
	t.Parallel()
	h := newAPI(t)
	mustCreate(t, h, "1984", "George Orwell", 1949, "")
	mustCreate(t, h, "Emma", "Jane Austen", 1815, "")
	mustCreate(t, h, "Animal Farm", "George Orwell", 1945, "")

	tests := []struct {
		name  string
		query string
		want  []string // titles, in order
	}{
		{"exact author", "George Orwell", []string{"1984", "Animal Farm"}},
		{"other author", "Jane Austen", []string{"Emma"}},
		{"case-insensitive", "george ORWELL", []string{"1984", "Animal Farm"}},
		{"surrounding whitespace ignored", "  Jane Austen ", []string{"Emma"}},
		{"unknown author", "Nobody", []string{}},
		{"partial name does not match", "Orwell", []string{}},
		{"empty filter lists everything", "", []string{"1984", "Emma", "Animal Farm"}},
		{"blank filter lists everything", "   ", []string{"1984", "Emma", "Animal Farm"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			rec := send(t, h, http.MethodGet, "/books?author="+url.QueryEscape(tt.query), "")
			wantStatus(t, rec, http.StatusOK)

			var titles []string
			for _, b := range decode[[]book.Book](t, rec) {
				titles = append(titles, b.Title)
			}
			if titles == nil {
				titles = []string{}
			}
			if strings.Join(titles, "|") != strings.Join(tt.want, "|") || len(titles) != len(tt.want) {
				t.Errorf("?author=%q returned %v, want %v", tt.query, titles, tt.want)
			}
		})
	}
}

func TestGetBook(t *testing.T) {
	t.Parallel()
	h := newAPI(t)
	want := mustCreate(t, h, "Dune", "Frank Herbert", 1965, "978")
	mustCreate(t, h, "Other", "Someone", 2000, "")

	rec := send(t, h, http.MethodGet, bookURL(want.ID), "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[book.Book](t, rec); got != want {
		t.Errorf("got %+v, want %+v", got, want)
	}
}

func TestGetBookNotFound(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	for _, id := range []string{"1", "999", "0", "-1"} {
		rec := send(t, h, http.MethodGet, "/books/"+id, "")
		wantStatus(t, rec, http.StatusNotFound)
		if got := decode[errorResponse](t, rec); got.Error != "book not found" {
			t.Errorf("GET /books/%s error = %q, want %q", id, got.Error, "book not found")
		}
	}
}

func TestBookIDMustBeAnInteger(t *testing.T) {
	t.Parallel()
	h := newAPI(t)
	mustCreate(t, h, "T", "A", 0, "")

	for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
		for _, id := range []string{"abc", "1.5", "1e3", "99999999999999999999", "0x10"} {
			body := ""
			if method == http.MethodPut {
				body = `{"title":"T","author":"A"}`
			}
			rec := send(t, h, method, "/books/"+id, body)
			wantStatus(t, rec, http.StatusBadRequest)
			if got := decode[errorResponse](t, rec); got.Error != "book id must be an integer" {
				t.Errorf("%s /books/%s error = %q", method, id, got.Error)
			}
		}
	}
}

func TestUpdateBook(t *testing.T) {
	t.Parallel()
	h := newAPI(t)
	target := mustCreate(t, h, "Old Title", "Old Author", 1999, "old")
	other := mustCreate(t, h, "Untouched", "Someone", 2000, "keep")

	rec := send(t, h, http.MethodPut, bookURL(target.ID),
		`{"title":"New Title","author":"New Author","year":2024,"isbn":"new"}`)
	wantStatus(t, rec, http.StatusOK)

	want := book.Book{ID: target.ID, Title: "New Title", Author: "New Author", Year: 2024, ISBN: "new"}
	if got := decode[book.Book](t, rec); got != want {
		t.Errorf("PUT response = %+v, want %+v", got, want)
	}

	if got := decode[book.Book](t, send(t, h, http.MethodGet, bookURL(target.ID), "")); got != want {
		t.Errorf("stored after PUT = %+v, want %+v", got, want)
	}
	if got := decode[book.Book](t, send(t, h, http.MethodGet, bookURL(other.ID), "")); got != other {
		t.Errorf("other book changed: %+v, want %+v", got, other)
	}
}

func TestUpdateBookIsIdempotent(t *testing.T) {
	t.Parallel()
	h := newAPI(t)
	b := mustCreate(t, h, "Title", "Author", 1999, "isbn")

	// Sending the book's current values again changes nothing, but must still
	// succeed: some databases report "0 rows affected" for a no-op update.
	body := `{"title":"Title","author":"Author","year":1999,"isbn":"isbn"}`
	for range 2 {
		rec := send(t, h, http.MethodPut, bookURL(b.ID), body)
		wantStatus(t, rec, http.StatusOK)
		if got := decode[book.Book](t, rec); got != b {
			t.Errorf("PUT response = %+v, want %+v", got, b)
		}
	}
}

func TestUpdateBookReplacesTheWholeBook(t *testing.T) {
	t.Parallel()
	h := newAPI(t)
	b := mustCreate(t, h, "Title", "Author", 1999, "isbn")

	rec := send(t, h, http.MethodPut, bookURL(b.ID), `{"title":"Title","author":"Author"}`)
	wantStatus(t, rec, http.StatusOK)
	got := decode[book.Book](t, rec)
	if got.Year != 0 || got.ISBN != "" {
		t.Errorf("year = %d, isbn = %q; PUT must clear fields it omits", got.Year, got.ISBN)
	}
}

func TestUpdateBookKeepsPathIDWhenBodyHasAnother(t *testing.T) {
	t.Parallel()
	h := newAPI(t)
	first := mustCreate(t, h, "First", "A", 0, "")
	second := mustCreate(t, h, "Second", "B", 0, "")

	rec := send(t, h, http.MethodPut, bookURL(first.ID), `{"id":`+strconv.FormatInt(second.ID, 10)+`,"title":"Changed","author":"A"}`)
	wantStatus(t, rec, http.StatusOK)
	if got := decode[book.Book](t, rec); got.ID != first.ID || got.Title != "Changed" {
		t.Errorf("PUT response = %+v, want book %d updated", got, first.ID)
	}
	if got := decode[book.Book](t, send(t, h, http.MethodGet, bookURL(second.ID), "")); got != second {
		t.Errorf("second book changed: %+v, want %+v", got, second)
	}
}

func TestUpdateBookValidation(t *testing.T) {
	t.Parallel()
	h := newAPI(t)
	original := mustCreate(t, h, "Title", "Author", 1999, "isbn")

	tests := []struct {
		name        string
		body        string
		wantStatus  int
		wantDetails map[string]string
	}{
		{"title missing", `{"author":"A"}`, http.StatusBadRequest, map[string]string{"title": "is required"}},
		{"author missing", `{"title":"T"}`, http.StatusBadRequest, map[string]string{"author": "is required"}},
		{"blank title", `{"title":" ","author":"A"}`, http.StatusBadRequest, map[string]string{"title": "is required"}},
		{"bad year", `{"title":"T","author":"A","year":-3}`, http.StatusBadRequest, map[string]string{"year": "must be between 0 and 9999"}},
		{"malformed JSON", `{`, http.StatusBadRequest, nil},
		{"empty body", ``, http.StatusBadRequest, nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := send(t, h, http.MethodPut, bookURL(original.ID), tt.body)
			wantStatus(t, rec, tt.wantStatus)
			if got := decode[errorResponse](t, rec); !maps.Equal(got.Details, tt.wantDetails) {
				t.Errorf("details = %v, want %v", got.Details, tt.wantDetails)
			}
		})
	}

	// None of the rejected updates may have modified the book.
	if got := decode[book.Book](t, send(t, h, http.MethodGet, bookURL(original.ID), "")); got != original {
		t.Errorf("book after rejected updates = %+v, want %+v", got, original)
	}
}

func TestUpdateBookNotFound(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	rec := send(t, h, http.MethodPut, "/books/999", `{"title":"T","author":"A"}`)
	wantStatus(t, rec, http.StatusNotFound)
	if got := decode[errorResponse](t, rec); got.Error != "book not found" {
		t.Errorf("error = %q", got.Error)
	}
	// PUT must not create the book.
	wantStatus(t, send(t, h, http.MethodGet, "/books/999", ""), http.StatusNotFound)
}

func TestDeleteBook(t *testing.T) {
	t.Parallel()
	h := newAPI(t)
	doomed := mustCreate(t, h, "Doomed", "A", 0, "")
	survivor := mustCreate(t, h, "Survivor", "B", 0, "")

	rec := send(t, h, http.MethodDelete, bookURL(doomed.ID), "")
	wantStatus(t, rec, http.StatusNoContent)
	if rec.Body.Len() != 0 {
		t.Errorf("204 response has a body: %q", rec.Body.String())
	}

	wantStatus(t, send(t, h, http.MethodGet, bookURL(doomed.ID), ""), http.StatusNotFound)
	wantStatus(t, send(t, h, http.MethodDelete, bookURL(doomed.ID), ""), http.StatusNotFound)

	list := decode[[]book.Book](t, send(t, h, http.MethodGet, "/books", ""))
	if len(list) != 1 || list[0] != survivor {
		t.Errorf("books after delete = %+v, want only %+v", list, survivor)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	rec := send(t, h, http.MethodDelete, "/books/999", "")
	wantStatus(t, rec, http.StatusNotFound)
	if got := decode[errorResponse](t, rec); got.Error != "book not found" {
		t.Errorf("error = %q", got.Error)
	}
}

func TestCompleteBookLifecycle(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	created := mustCreate(t, h, "Draft", "Writer", 2020, "")
	wantStatus(t, send(t, h, http.MethodPut, bookURL(created.ID),
		`{"title":"Final","author":"Writer","year":2021,"isbn":"978-1"}`), http.StatusOK)

	got := decode[book.Book](t, send(t, h, http.MethodGet, bookURL(created.ID), ""))
	if got.Title != "Final" || got.Year != 2021 || got.ISBN != "978-1" {
		t.Errorf("after update = %+v", got)
	}

	wantStatus(t, send(t, h, http.MethodDelete, bookURL(created.ID), ""), http.StatusNoContent)
	wantStatus(t, send(t, h, http.MethodGet, bookURL(created.ID), ""), http.StatusNotFound)
	if body := send(t, h, http.MethodGet, "/books", "").Body.String(); strings.TrimSpace(body) != "[]" {
		t.Errorf("collection not empty after delete: %s", body)
	}
}

func TestMethodNotAllowed(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	tests := []struct {
		method, path, allow string
	}{
		{http.MethodPatch, "/books/1", "DELETE, GET, HEAD, PUT"},
		{http.MethodPost, "/books/1", "DELETE, GET, HEAD, PUT"},
		{http.MethodDelete, "/books", "GET, HEAD, POST"},
		{http.MethodPut, "/books", "GET, HEAD, POST"},
		{http.MethodPost, "/health", "GET, HEAD"},
		{http.MethodDelete, "/health", "GET, HEAD"},
	}
	for _, tt := range tests {
		rec := send(t, h, tt.method, tt.path, "")
		wantStatus(t, rec, http.StatusMethodNotAllowed)
		if got := rec.Header().Get("Allow"); got != tt.allow {
			t.Errorf("%s %s: Allow = %q, want %q", tt.method, tt.path, got, tt.allow)
		}
		if got := decode[errorResponse](t, rec); got.Error != "method not allowed" {
			t.Errorf("%s %s: error = %q", tt.method, tt.path, got.Error)
		}
	}
}

func TestUnknownRouteReturnsJSON404(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	for _, path := range []string{"/", "/nope", "/books/1/extra", "/book/1", "/books/"} {
		rec := send(t, h, http.MethodGet, path, "")
		wantStatus(t, rec, http.StatusNotFound)
		if got := decode[errorResponse](t, rec); got.Error == "" {
			t.Errorf("GET %s: empty error message", path)
		}
	}
}
