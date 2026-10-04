package main

import (
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// newTestServer returns the API handler backed by a fresh on-disk SQLite
// database that is removed when the test finishes.
func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store, slog.New(slog.NewTextHandler(io.Discard, nil)))
}

func do(t *testing.T, h http.Handler, method, target, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, target, strings.NewReader(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	if ct := rec.Header().Get("Content-Type"); !strings.HasPrefix(ct, "application/json") {
		t.Fatalf("Content-Type = %q, want application/json", ct)
	}
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode response %q: %v", rec.Body.String(), err)
	}
	return v
}

func wantStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d (body: %s)", rec.Code, want, rec.Body.String())
	}
}

func createBook(t *testing.T, h http.Handler, body string) Book {
	t.Helper()
	rec := do(t, h, http.MethodPost, "/books", body)
	wantStatus(t, rec, http.StatusCreated)
	return decode[Book](t, rec)
}

func TestHealth(t *testing.T) {
	h := newTestServer(t)

	rec := do(t, h, http.MethodGet, "/health", "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[map[string]string](t, rec); got["status"] != "ok" {
		t.Errorf("status = %q, want ok", got["status"])
	}
}

func TestCreateAndGetBook(t *testing.T) {
	h := newTestServer(t)

	rec := do(t, h, http.MethodPost, "/books",
		`{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}`)
	wantStatus(t, rec, http.StatusCreated)

	created := decode[Book](t, rec)
	want := Book{ID: created.ID, Title: "The Go Programming Language", Author: "Alan Donovan", Year: 2015, ISBN: "978-0134190440"}
	if created.ID < 1 {
		t.Errorf("id = %d, want a positive id", created.ID)
	}
	if created != want {
		t.Errorf("created = %+v, want %+v", created, want)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}

	rec = do(t, h, http.MethodGet, "/books/1", "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[Book](t, rec); got != want {
		t.Errorf("fetched = %+v, want %+v", got, want)
	}
}

func TestCreateBookOptionalFields(t *testing.T) {
	h := newTestServer(t)

	got := createBook(t, h, `{"title":"  Untitled  ","author":" Anon "}`)
	want := Book{ID: got.ID, Title: "Untitled", Author: "Anon"}
	if got != want {
		t.Errorf("created = %+v, want %+v", got, want)
	}
}

func TestCreateBookValidation(t *testing.T) {
	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantFields []string
	}{
		{"missing title", `{"author":"A"}`, http.StatusBadRequest, []string{"title"}},
		{"missing author", `{"title":"T"}`, http.StatusBadRequest, []string{"author"}},
		{"missing both", `{}`, http.StatusBadRequest, []string{"title", "author"}},
		{"blank title", `{"title":"   ","author":"A"}`, http.StatusBadRequest, []string{"title"}},
		{"null title", `{"title":null,"author":"A"}`, http.StatusBadRequest, []string{"title"}},
		{"negative year", `{"title":"T","author":"A","year":-1}`, http.StatusBadRequest, []string{"year"}},
		{"year too large", `{"title":"T","author":"A","year":10000}`, http.StatusBadRequest, []string{"year"}},
		{"title too long", `{"title":"` + strings.Repeat("x", maxTextLen+1) + `","author":"A"}`, http.StatusBadRequest, []string{"title"}},
		{"isbn too long", `{"title":"T","author":"A","isbn":"` + strings.Repeat("1", maxISBNLen+1) + `"}`, http.StatusBadRequest, []string{"isbn"}},
		{"year wrong type", `{"title":"T","author":"A","year":"1999"}`, http.StatusBadRequest, nil},
		{"title wrong type", `{"title":42,"author":"A"}`, http.StatusBadRequest, nil},
		{"malformed json", `{"title":`, http.StatusBadRequest, nil},
		{"empty body", ``, http.StatusBadRequest, nil},
		{"json array", `[]`, http.StatusBadRequest, nil},
		{"trailing data", `{"title":"T","author":"A"}{"title":"U","author":"B"}`, http.StatusBadRequest, nil},
		{"body too large", `{"title":"T","author":"` + strings.Repeat("a", maxBodyBytes) + `"}`, http.StatusRequestEntityTooLarge, nil},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h := newTestServer(t)

			rec := do(t, h, http.MethodPost, "/books", tt.body)
			wantStatus(t, rec, tt.wantStatus)

			resp := decode[errorResponse](t, rec)
			if resp.Error == "" {
				t.Errorf("error message is empty")
			}
			if len(resp.Fields) != len(tt.wantFields) {
				t.Errorf("fields = %v, want exactly %v", resp.Fields, tt.wantFields)
			}
			for _, f := range tt.wantFields {
				if resp.Fields[f] == "" {
					t.Errorf("fields = %v, want an error for %q", resp.Fields, f)
				}
			}

			// A rejected request must not have stored anything.
			rec = do(t, h, http.MethodGet, "/books", "")
			if books := decode[[]Book](t, rec); len(books) != 0 {
				t.Errorf("books after rejected create = %+v, want none", books)
			}
		})
	}
}

func TestListBooks(t *testing.T) {
	h := newTestServer(t)

	// An empty collection is an empty JSON array, not null.
	rec := do(t, h, http.MethodGet, "/books", "")
	wantStatus(t, rec, http.StatusOK)
	if body := strings.TrimSpace(rec.Body.String()); body != "[]" {
		t.Errorf("empty list body = %q, want []", body)
	}

	createBook(t, h, `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	createBook(t, h, `{"title":"Emma","author":"Jane Austen","year":1815}`)
	createBook(t, h, `{"title":"Children of Dune","author":"Frank Herbert","year":1976}`)

	tests := []struct {
		name       string
		target     string
		wantTitles []string
	}{
		{"all", "/books", []string{"Dune", "Emma", "Children of Dune"}},
		{"author filter", "/books?author=Frank+Herbert", []string{"Dune", "Children of Dune"}},
		{"author filter is case-insensitive", "/books?author=jane%20austen", []string{"Emma"}},
		{"author filter is an exact match", "/books?author=Frank", nil},
		{"unknown author", "/books?author=Nobody", nil},
		{"empty author filter lists all", "/books?author=", []string{"Dune", "Emma", "Children of Dune"}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, h, http.MethodGet, tt.target, "")
			wantStatus(t, rec, http.StatusOK)

			books := decode[[]Book](t, rec)
			if books == nil {
				t.Fatalf("body = %q, want a JSON array", rec.Body.String())
			}
			var titles []string
			for _, b := range books {
				titles = append(titles, b.Title)
			}
			if strings.Join(titles, "|") != strings.Join(tt.wantTitles, "|") {
				t.Errorf("titles = %v, want %v", titles, tt.wantTitles)
			}
		})
	}
}

func TestAuthorFilterIsNotInjectable(t *testing.T) {
	h := newTestServer(t)
	createBook(t, h, `{"title":"Dune","author":"Frank Herbert"}`)

	rec := do(t, h, http.MethodGet, "/books?author=x'+OR+'1'='1", "")
	wantStatus(t, rec, http.StatusOK)
	if books := decode[[]Book](t, rec); len(books) != 0 {
		t.Errorf("books = %+v, want none", books)
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestServer(t)
	createBook(t, h, `{"title":"Dune","author":"F. Herbert","year":1965,"isbn":"111"}`)
	other := createBook(t, h, `{"title":"Emma","author":"Jane Austen","year":1815}`)

	rec := do(t, h, http.MethodPut, "/books/1", `{"title":"Dune (Revised)","author":"Frank Herbert","year":1966}`)
	wantStatus(t, rec, http.StatusOK)

	// PUT replaces the whole resource, so the omitted isbn is cleared.
	want := Book{ID: 1, Title: "Dune (Revised)", Author: "Frank Herbert", Year: 1966}
	if got := decode[Book](t, rec); got != want {
		t.Errorf("updated = %+v, want %+v", got, want)
	}

	rec = do(t, h, http.MethodGet, "/books/1", "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[Book](t, rec); got != want {
		t.Errorf("fetched after update = %+v, want %+v", got, want)
	}

	rec = do(t, h, http.MethodGet, "/books/2", "")
	if got := decode[Book](t, rec); got != other {
		t.Errorf("unrelated book = %+v, want it unchanged as %+v", got, other)
	}
}

func TestUpdateBookErrors(t *testing.T) {
	h := newTestServer(t)
	original := createBook(t, h, `{"title":"Dune","author":"Frank Herbert","year":1965}`)

	tests := []struct {
		name       string
		target     string
		body       string
		wantStatus int
	}{
		{"not found", "/books/999", `{"title":"T","author":"A"}`, http.StatusNotFound},
		{"invalid id", "/books/abc", `{"title":"T","author":"A"}`, http.StatusBadRequest},
		{"missing title", "/books/1", `{"author":"A"}`, http.StatusBadRequest},
		{"missing author", "/books/1", `{"title":"T"}`, http.StatusBadRequest},
		{"malformed json", "/books/1", `not json`, http.StatusBadRequest},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, h, http.MethodPut, tt.target, tt.body)
			wantStatus(t, rec, tt.wantStatus)
			if resp := decode[errorResponse](t, rec); resp.Error == "" {
				t.Errorf("error message is empty")
			}
		})
	}

	rec := do(t, h, http.MethodGet, "/books/1", "")
	if got := decode[Book](t, rec); got != original {
		t.Errorf("book after failed updates = %+v, want it unchanged as %+v", got, original)
	}
}

func TestDeleteBook(t *testing.T) {
	h := newTestServer(t)
	createBook(t, h, `{"title":"Dune","author":"Frank Herbert"}`)
	createBook(t, h, `{"title":"Emma","author":"Jane Austen"}`)

	rec := do(t, h, http.MethodDelete, "/books/1", "")
	wantStatus(t, rec, http.StatusNoContent)
	if rec.Body.Len() != 0 {
		t.Errorf("body = %q, want empty", rec.Body.String())
	}

	wantStatus(t, do(t, h, http.MethodGet, "/books/1", ""), http.StatusNotFound)
	wantStatus(t, do(t, h, http.MethodDelete, "/books/1", ""), http.StatusNotFound)

	rec = do(t, h, http.MethodGet, "/books", "")
	books := decode[[]Book](t, rec)
	if len(books) != 1 || books[0].Title != "Emma" {
		t.Errorf("remaining books = %+v, want only Emma", books)
	}

	// IDs of deleted books are not handed out again.
	if b := createBook(t, h, `{"title":"Ulysses","author":"James Joyce"}`); b.ID != 3 {
		t.Errorf("id after delete = %d, want 3", b.ID)
	}
}

func TestBookIDErrors(t *testing.T) {
	h := newTestServer(t)

	tests := []struct {
		name       string
		method     string
		target     string
		wantStatus int
	}{
		{"get missing", http.MethodGet, "/books/1", http.StatusNotFound},
		{"delete missing", http.MethodDelete, "/books/1", http.StatusNotFound},
		{"get non-numeric id", http.MethodGet, "/books/abc", http.StatusBadRequest},
		{"get zero id", http.MethodGet, "/books/0", http.StatusBadRequest},
		{"get negative id", http.MethodGet, "/books/-1", http.StatusBadRequest},
		{"get overflowing id", http.MethodGet, "/books/99999999999999999999", http.StatusBadRequest},
		{"delete non-numeric id", http.MethodDelete, "/books/abc", http.StatusBadRequest},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, h, tt.method, tt.target, "")
			wantStatus(t, rec, tt.wantStatus)
			if resp := decode[errorResponse](t, rec); resp.Error == "" {
				t.Errorf("error message is empty")
			}
		})
	}
}

func TestUnsupportedRoutes(t *testing.T) {
	h := newTestServer(t)

	tests := []struct {
		name       string
		method     string
		target     string
		wantStatus int
		wantAllow  string
	}{
		{"delete collection", http.MethodDelete, "/books", http.StatusMethodNotAllowed, "GET, HEAD, POST"},
		{"post to item", http.MethodPost, "/books/1", http.StatusMethodNotAllowed, "GET, HEAD, PUT, DELETE"},
		{"post to health", http.MethodPost, "/health", http.StatusMethodNotAllowed, "GET, HEAD"},
		{"unknown path", http.MethodGet, "/nope", http.StatusNotFound, ""},
		{"nested path", http.MethodGet, "/books/1/reviews", http.StatusNotFound, ""},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, h, tt.method, tt.target, "")
			wantStatus(t, rec, tt.wantStatus)
			if got := rec.Header().Get("Allow"); got != tt.wantAllow {
				t.Errorf("Allow = %q, want %q", got, tt.wantAllow)
			}
			if resp := decode[errorResponse](t, rec); resp.Error == "" {
				t.Errorf("error message is empty")
			}
		})
	}
}

func TestDataPersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))

	store, err := OpenStore(path)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	created := createBook(t, NewServer(store, logger), `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	store, err = OpenStore(path)
	if err != nil {
		t.Fatalf("reopen OpenStore: %v", err)
	}
	defer store.Close()

	rec := do(t, NewServer(store, logger), http.MethodGet, "/books/1", "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[Book](t, rec); got != created {
		t.Errorf("book after reopen = %+v, want %+v", got, created)
	}
}

func TestDatabasePathWithURICharacters(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "odd dir?%#")
	if err := os.Mkdir(dir, 0o755); err != nil {
		t.Fatalf("Mkdir: %v", err)
	}
	path := filepath.Join(dir, "books.db")

	store, err := OpenStore(path)
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	defer store.Close()

	createBook(t, NewServer(store, slog.New(slog.NewTextHandler(io.Discard, nil))), `{"title":"Dune","author":"Frank Herbert"}`)
	if _, err := os.Stat(path); err != nil {
		t.Errorf("database file was not created at the requested path: %v", err)
	}
}

func TestInMemoryStore(t *testing.T) {
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	defer store.Close()
	h := NewServer(store, slog.New(slog.NewTextHandler(io.Discard, nil)))

	createBook(t, h, `{"title":"Dune","author":"Frank Herbert"}`)
	rec := do(t, h, http.MethodGet, "/books", "")
	if books := decode[[]Book](t, rec); len(books) != 1 {
		t.Errorf("books = %+v, want 1", books)
	}
}
