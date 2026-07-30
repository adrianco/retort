package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// newTestServer returns a Server backed by a fresh temporary SQLite file. A
// file (rather than :memory:) is used so the tests exercise the same code path
// as production, including WAL mode.
func newTestServer(t *testing.T) *Server {
	t.Helper()
	store := OpenTestStore(t)
	return NewServer(store, nil)
}

// OpenTestStore opens a store on a throwaway database that is closed when the
// test finishes.
func OpenTestStore(t *testing.T) *Store {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() {
		if err := store.Close(); err != nil {
			t.Errorf("close store: %v", err)
		}
	})
	return store
}

// do performs a request against the handler. A nil body sends no payload; a
// string body is sent verbatim; anything else is JSON-encoded.
func do(t *testing.T, h http.Handler, method, target string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var reader *bytes.Reader
	switch v := body.(type) {
	case nil:
		reader = bytes.NewReader(nil)
	case string:
		reader = bytes.NewReader([]byte(v))
	default:
		raw, err := json.Marshal(v)
		if err != nil {
			t.Fatalf("marshal request body: %v", err)
		}
		reader = bytes.NewReader(raw)
	}

	req := httptest.NewRequest(method, target, reader)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decodeBody[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var out T
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
		t.Fatalf("decode response %q: %v", rec.Body.String(), err)
	}
	return out
}

func assertStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d (body: %s)", rec.Code, want, strings.TrimSpace(rec.Body.String()))
	}
}

// createBook is a fixture helper that fails the test if creation does not
// succeed.
func createBook(t *testing.T, h http.Handler, in BookInput) Book {
	t.Helper()
	rec := do(t, h, http.MethodPost, "/books", in)
	assertStatus(t, rec, http.StatusCreated)
	return decodeBody[Book](t, rec)
}

var dune = BookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0-441-01359-3"}

func TestCreateBook(t *testing.T) {
	srv := newTestServer(t)

	rec := do(t, srv, http.MethodPost, "/books", dune)
	assertStatus(t, rec, http.StatusCreated)

	if got, want := rec.Header().Get("Content-Type"), "application/json; charset=utf-8"; got != want {
		t.Errorf("Content-Type = %q, want %q", got, want)
	}

	got := decodeBody[Book](t, rec)
	if got.ID < 1 {
		t.Errorf("ID = %d, want a positive integer", got.ID)
	}
	if got.Title != dune.Title || got.Author != dune.Author || got.Year != dune.Year || got.ISBN != dune.ISBN {
		t.Errorf("created book = %+v, want fields from %+v", got, dune)
	}
	if got.CreatedAt.IsZero() || got.UpdatedAt.IsZero() {
		t.Errorf("timestamps = %v/%v, want both set", got.CreatedAt, got.UpdatedAt)
	}
	if want := "/books/" + itoa(got.ID); rec.Header().Get("Location") != want {
		t.Errorf("Location = %q, want %q", rec.Header().Get("Location"), want)
	}

	// The advertised Location must actually resolve.
	rec = do(t, srv, http.MethodGet, rec.Header().Get("Location"), nil)
	assertStatus(t, rec, http.StatusOK)
	if fetched := decodeBody[Book](t, rec); fetched.ID != got.ID {
		t.Errorf("Location resolved to book %d, want %d", fetched.ID, got.ID)
	}
}

func TestCreateBookOptionalFields(t *testing.T) {
	srv := newTestServer(t)

	// Only title and author are required.
	got := createBook(t, srv, BookInput{Title: "  Untitled  ", Author: "  Anon  "})
	if got.Title != "Untitled" || got.Author != "Anon" {
		t.Errorf("got title=%q author=%q, want whitespace trimmed", got.Title, got.Author)
	}
	if got.Year != 0 || got.ISBN != "" {
		t.Errorf("got year=%d isbn=%q, want zero values", got.Year, got.ISBN)
	}
}

func TestCreateBookValidation(t *testing.T) {
	srv := newTestServer(t)
	nextYear := time.Now().Year() + 100

	tests := []struct {
		name       string
		body       any
		wantStatus int
		wantFields []string
	}{
		{"missing title", BookInput{Author: "Frank Herbert"}, http.StatusBadRequest, []string{"title"}},
		{"blank title", BookInput{Title: "   ", Author: "Frank Herbert"}, http.StatusBadRequest, []string{"title"}},
		{"missing author", BookInput{Title: "Dune"}, http.StatusBadRequest, []string{"author"}},
		{"missing both", BookInput{Year: 1965}, http.StatusBadRequest, []string{"author", "title"}},
		{"title too long", BookInput{Title: strings.Repeat("x", maxTitleLen+1), Author: "A"}, http.StatusBadRequest, []string{"title"}},
		{"year too early", BookInput{Title: "Dune", Author: "A", Year: 1200}, http.StatusBadRequest, []string{"year"}},
		{"year too late", BookInput{Title: "Dune", Author: "A", Year: nextYear}, http.StatusBadRequest, []string{"year"}},
		{"malformed isbn", BookInput{Title: "Dune", Author: "A", ISBN: "not-an-isbn"}, http.StatusBadRequest, []string{"isbn"}},
		{"short isbn", BookInput{Title: "Dune", Author: "A", ISBN: "12345"}, http.StatusBadRequest, []string{"isbn"}},
		{"malformed json", `{"title": `, http.StatusBadRequest, nil},
		{"empty body", ``, http.StatusBadRequest, nil},
		{"wrong field type", `{"title":"Dune","author":"A","year":"1965"}`, http.StatusBadRequest, nil},
		{"unknown field", `{"title":"Dune","author":"A","publisher":"Ace"}`, http.StatusBadRequest, nil},
		{"trailing data", `{"title":"Dune","author":"A"}{"title":"x"}`, http.StatusBadRequest, nil},
		{"json array", `[{"title":"Dune","author":"A"}]`, http.StatusBadRequest, nil},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			rec := do(t, srv, http.MethodPost, "/books", tc.body)
			assertStatus(t, rec, tc.wantStatus)

			got := decodeBody[errorBody](t, rec)
			if got.Error == "" {
				t.Error("error message is empty")
			}
			if len(tc.wantFields) != len(got.Fields) {
				t.Fatalf("fields = %v, want keys %v", got.Fields, tc.wantFields)
			}
			for _, f := range tc.wantFields {
				if got.Fields[f] == "" {
					t.Errorf("fields[%q] is missing from %v", f, got.Fields)
				}
			}
		})
	}

	// Nothing above should have been persisted.
	rec := do(t, srv, http.MethodGet, "/books", nil)
	assertStatus(t, rec, http.StatusOK)
	if books := decodeBody[[]Book](t, rec); len(books) != 0 {
		t.Errorf("collection contains %d books after rejected creates, want 0", len(books))
	}
}

func TestCreateBookRejectsNonJSONContentType(t *testing.T) {
	srv := newTestServer(t)

	req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader(`title=Dune`))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)

	assertStatus(t, rec, http.StatusUnsupportedMediaType)
}

func TestListBooks(t *testing.T) {
	srv := newTestServer(t)

	rec := do(t, srv, http.MethodGet, "/books", nil)
	assertStatus(t, rec, http.StatusOK)
	if got := strings.TrimSpace(rec.Body.String()); got != "[]" {
		t.Errorf("empty collection = %s, want []", got)
	}

	want := []BookInput{
		{Title: "Dune", Author: "Frank Herbert", Year: 1965},
		{Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969},
		{Title: "Neuromancer", Author: "William Gibson", Year: 1984},
	}
	for _, in := range want {
		createBook(t, srv, in)
	}

	rec = do(t, srv, http.MethodGet, "/books", nil)
	assertStatus(t, rec, http.StatusOK)
	got := decodeBody[[]Book](t, rec)
	if len(got) != len(want) {
		t.Fatalf("got %d books, want %d", len(got), len(want))
	}
	for i := range want {
		if got[i].Title != want[i].Title {
			t.Errorf("book %d title = %q, want %q (expected insertion order)", i, got[i].Title, want[i].Title)
		}
	}
}

func TestListBooksAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	for _, in := range []BookInput{
		{Title: "Dune", Author: "Frank Herbert"},
		{Title: "Dune Messiah", Author: "Frank Herbert"},
		{Title: "Neuromancer", Author: "William Gibson"},
	} {
		createBook(t, srv, in)
	}

	tests := []struct {
		name  string
		query string
		want  []string
	}{
		{"exact match", "?author=Frank+Herbert", []string{"Dune", "Dune Messiah"}},
		{"case insensitive", "?author=frank+herbert", []string{"Dune", "Dune Messiah"}},
		{"other author", "?author=William+Gibson", []string{"Neuromancer"}},
		{"no match", "?author=Ursula+K.+Le+Guin", nil},
		{"blank filter is ignored", "?author=", []string{"Dune", "Dune Messiah", "Neuromancer"}},
		{"whitespace filter is ignored", "?author=%20", []string{"Dune", "Dune Messiah", "Neuromancer"}},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			rec := do(t, srv, http.MethodGet, "/books"+tc.query, nil)
			assertStatus(t, rec, http.StatusOK)

			got := decodeBody[[]Book](t, rec)
			if len(got) != len(tc.want) {
				t.Fatalf("got %d books, want %d (%v)", len(got), len(tc.want), tc.want)
			}
			for i, title := range tc.want {
				if got[i].Title != title {
					t.Errorf("book %d = %q, want %q", i, got[i].Title, title)
				}
			}
		})
	}
}

func TestGetBook(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, dune)

	rec := do(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil)
	assertStatus(t, rec, http.StatusOK)
	if got := decodeBody[Book](t, rec); got != created {
		t.Errorf("got %+v, want %+v", got, created)
	}

	tests := []struct {
		name       string
		path       string
		wantStatus int
	}{
		{"unknown id", "/books/99999", http.StatusNotFound},
		{"non-numeric id", "/books/abc", http.StatusBadRequest},
		{"zero id", "/books/0", http.StatusBadRequest},
		{"negative id", "/books/-1", http.StatusBadRequest},
		{"overflowing id", "/books/99999999999999999999", http.StatusBadRequest},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			rec := do(t, srv, http.MethodGet, tc.path, nil)
			assertStatus(t, rec, tc.wantStatus)
			if got := decodeBody[errorBody](t, rec); got.Error == "" {
				t.Error("error message is empty")
			}
		})
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, dune)

	update := BookInput{Title: "Dune (Deluxe Edition)", Author: "Frank Herbert", Year: 2019, ISBN: "9780593099322"}
	rec := do(t, srv, http.MethodPut, "/books/"+itoa(created.ID), update)
	assertStatus(t, rec, http.StatusOK)

	got := decodeBody[Book](t, rec)
	if got.ID != created.ID {
		t.Errorf("ID = %d, want %d unchanged", got.ID, created.ID)
	}
	if got.Title != update.Title || got.Year != update.Year || got.ISBN != update.ISBN {
		t.Errorf("got %+v, want fields from %+v", got, update)
	}
	if !got.CreatedAt.Equal(created.CreatedAt) {
		t.Errorf("CreatedAt = %v, want %v unchanged", got.CreatedAt, created.CreatedAt)
	}
	if got.UpdatedAt.Before(created.UpdatedAt) {
		t.Errorf("UpdatedAt = %v, want at or after %v", got.UpdatedAt, created.UpdatedAt)
	}

	// A subsequent read must observe the update.
	rec = do(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil)
	assertStatus(t, rec, http.StatusOK)
	if reread := decodeBody[Book](t, rec); reread != got {
		t.Errorf("re-read = %+v, want %+v", reread, got)
	}

	// PUT replaces the whole record: omitted optional fields are cleared.
	rec = do(t, srv, http.MethodPut, "/books/"+itoa(created.ID),
		BookInput{Title: "Dune", Author: "Frank Herbert"})
	assertStatus(t, rec, http.StatusOK)
	if cleared := decodeBody[Book](t, rec); cleared.Year != 0 || cleared.ISBN != "" {
		t.Errorf("got year=%d isbn=%q, want cleared by full replacement", cleared.Year, cleared.ISBN)
	}
}

func TestUpdateBookErrors(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, dune)

	tests := []struct {
		name       string
		path       string
		body       any
		wantStatus int
	}{
		{"unknown id", "/books/99999", dune, http.StatusNotFound},
		{"invalid id", "/books/abc", dune, http.StatusBadRequest},
		{"missing title", "/books/" + itoa(created.ID), BookInput{Author: "Frank Herbert"}, http.StatusBadRequest},
		{"missing author", "/books/" + itoa(created.ID), BookInput{Title: "Dune"}, http.StatusBadRequest},
		{"malformed json", "/books/" + itoa(created.ID), `{`, http.StatusBadRequest},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			rec := do(t, srv, http.MethodPut, tc.path, tc.body)
			assertStatus(t, rec, tc.wantStatus)
		})
	}

	// A rejected update must leave the record untouched.
	rec := do(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil)
	assertStatus(t, rec, http.StatusOK)
	if got := decodeBody[Book](t, rec); got != created {
		t.Errorf("got %+v, want %+v unchanged", got, created)
	}
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, dune)
	survivor := createBook(t, srv, BookInput{Title: "Neuromancer", Author: "William Gibson"})

	rec := do(t, srv, http.MethodDelete, "/books/"+itoa(created.ID), nil)
	assertStatus(t, rec, http.StatusNoContent)
	if rec.Body.Len() != 0 {
		t.Errorf("body = %q, want empty for 204", rec.Body.String())
	}

	// It is gone, and deleting again reports 404 rather than another 204.
	for _, method := range []string{http.MethodGet, http.MethodDelete, http.MethodPut} {
		var body any
		if method == http.MethodPut {
			body = dune
		}
		rec := do(t, srv, method, "/books/"+itoa(created.ID), body)
		assertStatus(t, rec, http.StatusNotFound)
	}

	// Other records are unaffected.
	rec = do(t, srv, http.MethodGet, "/books", nil)
	assertStatus(t, rec, http.StatusOK)
	got := decodeBody[[]Book](t, rec)
	if len(got) != 1 || got[0].ID != survivor.ID {
		t.Errorf("remaining books = %+v, want only %d", got, survivor.ID)
	}
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)

	rec := do(t, srv, http.MethodGet, "/health", nil)
	assertStatus(t, rec, http.StatusOK)

	got := decodeBody[map[string]string](t, rec)
	if got["status"] != "ok" || got["database"] != "ok" {
		t.Errorf("body = %v, want status and database ok", got)
	}
}

func TestHealthReportsUnavailableDatabase(t *testing.T) {
	store := OpenTestStore(t)
	srv := NewServer(store, nil)
	if err := store.Close(); err != nil {
		t.Fatalf("close store: %v", err)
	}

	rec := do(t, srv, http.MethodGet, "/health", nil)
	assertStatus(t, rec, http.StatusServiceUnavailable)
	if got := decodeBody[map[string]string](t, rec); got["status"] == "ok" {
		t.Errorf("body = %v, want a non-ok status", got)
	}
}

func TestRoutingErrors(t *testing.T) {
	srv := newTestServer(t)

	tests := []struct {
		name       string
		method     string
		path       string
		wantStatus int
		wantAllow  string
	}{
		{"unknown path", http.MethodGet, "/authors", http.StatusNotFound, ""},
		{"nested path", http.MethodGet, "/books/1/reviews", http.StatusNotFound, ""},
		{"collection method", http.MethodDelete, "/books", http.StatusMethodNotAllowed, "GET, POST"},
		{"item method", http.MethodPost, "/books/1", http.StatusMethodNotAllowed, "GET, PUT, DELETE"},
		{"health method", http.MethodPost, "/health", http.StatusMethodNotAllowed, "GET"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			rec := do(t, srv, tc.method, tc.path, nil)
			assertStatus(t, rec, tc.wantStatus)
			if got := rec.Header().Get("Allow"); got != tc.wantAllow {
				t.Errorf("Allow = %q, want %q", got, tc.wantAllow)
			}
			if got := decodeBody[errorBody](t, rec); got.Error == "" {
				t.Error("error message is empty")
			}
		})
	}
}

// TestFullLifecycle walks the documented happy path end to end over a real
// TCP listener, exercising the same handler a client would reach.
func TestFullLifecycle(t *testing.T) {
	ts := httptest.NewServer(newTestServer(t))
	defer ts.Close()

	client := ts.Client()

	body, _ := json.Marshal(dune)
	res, err := client.Post(ts.URL+"/books", "application/json", bytes.NewReader(body))
	if err != nil {
		t.Fatalf("POST /books: %v", err)
	}
	defer res.Body.Close()
	if res.StatusCode != http.StatusCreated {
		t.Fatalf("POST /books status = %d, want 201", res.StatusCode)
	}
	var created Book
	if err := json.NewDecoder(res.Body).Decode(&created); err != nil {
		t.Fatalf("decode created book: %v", err)
	}

	res, err = client.Get(ts.URL + "/books?author=Frank%20Herbert")
	if err != nil {
		t.Fatalf("GET /books: %v", err)
	}
	defer res.Body.Close()
	var listed []Book
	if err := json.NewDecoder(res.Body).Decode(&listed); err != nil {
		t.Fatalf("decode list: %v", err)
	}
	if len(listed) != 1 || listed[0].ID != created.ID {
		t.Fatalf("filtered list = %+v, want just book %d", listed, created.ID)
	}

	req, err := http.NewRequest(http.MethodDelete, ts.URL+"/books/"+itoa(created.ID), nil)
	if err != nil {
		t.Fatalf("build DELETE: %v", err)
	}
	res, err = client.Do(req)
	if err != nil {
		t.Fatalf("DELETE: %v", err)
	}
	defer res.Body.Close()
	if res.StatusCode != http.StatusNoContent {
		t.Fatalf("DELETE status = %d, want 204", res.StatusCode)
	}
}
