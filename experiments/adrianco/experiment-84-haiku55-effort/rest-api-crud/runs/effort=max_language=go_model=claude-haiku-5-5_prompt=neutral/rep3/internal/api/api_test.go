package api_test

import (
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"maps"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"slices"
	"strconv"
	"strings"
	"testing"

	"bookapi/internal/api"
	"bookapi/internal/book"
	"bookapi/internal/store"
)

// newTestServer serves the full API from a fresh SQLite file in a temp dir.
func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	st, err := store.Open(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { st.Close() })

	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	srv := httptest.NewServer(api.NewRouter(st, logger))
	t.Cleanup(srv.Close)
	return srv
}

type response struct {
	status int
	header http.Header
	body   string
}

// do sends one request and reads the whole response. An empty body sends no payload.
func do(t *testing.T, srv *httptest.Server, method, path, body string) response {
	t.Helper()
	var payload io.Reader
	if body != "" {
		payload = strings.NewReader(body)
	}
	req, err := http.NewRequest(method, srv.URL+path, payload)
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := srv.Client().Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, path, err)
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read %s %s body: %v", method, path, err)
	}
	return response{status: resp.StatusCode, header: resp.Header, body: string(data)}
}

func decode(t *testing.T, r response, v any) {
	t.Helper()
	if err := json.Unmarshal([]byte(r.body), v); err != nil {
		t.Fatalf("decode %q: %v", r.body, err)
	}
}

// errorBody is the JSON error envelope every failed request returns.
type errorBody struct {
	Error   string            `json:"error"`
	Details map[string]string `json:"details"`
}

func assertJSONError(t *testing.T, r response, status int) errorBody {
	t.Helper()
	if r.status != status {
		t.Fatalf("status = %d; want %d (body %s)", r.status, status, r.body)
	}
	if ct := r.header.Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q; want application/json", ct)
	}
	var eb errorBody
	decode(t, r, &eb)
	if eb.Error == "" {
		t.Errorf("error body %q has no error message", r.body)
	}
	return eb
}

// createBook posts payload and returns the stored book, failing the test unless the server answers 201.
func createBook(t *testing.T, srv *httptest.Server, payload string) book.Book {
	t.Helper()
	r := do(t, srv, http.MethodPost, "/books", payload)
	if r.status != http.StatusCreated {
		t.Fatalf("create: status %d; body %s", r.status, r.body)
	}
	var b book.Book
	decode(t, r, &b)
	return b
}

func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)

	created := do(t, srv, http.MethodPost, "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	if created.status != http.StatusCreated {
		t.Fatalf("POST status = %d; want 201 (body %s)", created.status, created.body)
	}
	if ct := created.header.Get("Content-Type"); ct != "application/json" {
		t.Errorf("POST Content-Type = %q; want application/json", ct)
	}
	var b book.Book
	decode(t, created, &b)
	if b.ID == 0 {
		t.Fatal("POST returned no id")
	}
	want := book.Book{ID: b.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"}
	if b != want {
		t.Errorf("POST body = %+v; want %+v", b, want)
	}
	if loc, wantLoc := created.header.Get("Location"), "/books/"+strconv.FormatInt(b.ID, 10); loc != wantLoc {
		t.Errorf("Location = %q; want %q", loc, wantLoc)
	}

	got := do(t, srv, http.MethodGet, fmt.Sprintf("/books/%d", b.ID), "")
	if got.status != http.StatusOK {
		t.Fatalf("GET status = %d; want 200 (body %s)", got.status, got.body)
	}
	var fetched book.Book
	decode(t, got, &fetched)
	if fetched != want {
		t.Errorf("GET body = %+v; want %+v", fetched, want)
	}
}

func TestCreateRejectsInvalidBooks(t *testing.T) {
	srv := newTestServer(t)

	tests := []struct {
		name string
		body string
		// wantFields lists the fields expected in the validation details, sorted.
		// nil means the body is not valid JSON for this schema, so there are no details.
		wantFields []string
	}{
		{"missing title", `{"author":"Frank Herbert"}`, []string{"title"}},
		{"missing author", `{"title":"Dune"}`, []string{"author"}},
		{"blank title and author", `{"title":"  ","author":"\t"}`, []string{"author", "title"}},
		{"year out of range", `{"title":"Dune","author":"Frank Herbert","year":-3}`, []string{"year"}},
		{"malformed isbn", `{"title":"Dune","author":"Frank Herbert","isbn":"12"}`, []string{"isbn"}},
		{"year is a string", `{"title":"Dune","author":"Frank Herbert","year":"1965"}`, nil},
		{"empty body", ``, nil},
		{"truncated JSON", `{"title":`, nil},
		{"JSON array instead of object", `[1,2]`, nil},
		{"two JSON documents", `{"title":"Dune","author":"Frank Herbert"}{}`, nil},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			r := do(t, srv, http.MethodPost, "/books", tc.body)
			eb := assertJSONError(t, r, http.StatusBadRequest)

			if tc.wantFields == nil {
				if eb.Details != nil {
					t.Errorf("details = %v; want none for a malformed body", eb.Details)
				}
				return
			}
			if eb.Error != "validation failed" {
				t.Errorf("error = %q; want \"validation failed\"", eb.Error)
			}
			if got := slices.Sorted(maps.Keys(eb.Details)); !slices.Equal(got, tc.wantFields) {
				t.Errorf("details fields = %v; want %v", got, tc.wantFields)
			}
		})
	}

	// Nothing should have been stored by the rejected requests.
	list := do(t, srv, http.MethodGet, "/books", "")
	if strings.TrimSpace(list.body) != "[]" {
		t.Errorf("GET /books after rejected creates = %s; want []", list.body)
	}
}

func TestCreateAcceptsBodyWithoutContentType(t *testing.T) {
	srv := newTestServer(t)

	// Plain clients such as `curl -d` send no Content-Type, and the body is still JSON.
	req, err := http.NewRequest(http.MethodPost, srv.URL+"/books",
		strings.NewReader(`{"title":"Dune","author":"Frank Herbert"}`))
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	resp, err := srv.Client().Do(req)
	if err != nil {
		t.Fatalf("POST /books: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusCreated {
		t.Errorf("status = %d; want 201", resp.StatusCode)
	}
}

func TestCreateRejectsOversizedBody(t *testing.T) {
	srv := newTestServer(t)
	body := `{"title":"` + strings.Repeat("a", 2<<20) + `","author":"x"}`

	r := do(t, srv, http.MethodPost, "/books", body)
	assertJSONError(t, r, http.StatusRequestEntityTooLarge)
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	hobbit := createBook(t, srv, `{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937}`)
	dune := createBook(t, srv, `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	lotr := createBook(t, srv, `{"title":"The Fellowship of the Ring","author":"J.R.R. Tolkien","year":1954}`)

	tests := []struct {
		name string
		path string
		want []book.Book
	}{
		{"no filter returns all books in ID order", "/books", []book.Book{hobbit, dune, lotr}},
		{"author filter ignores case", "/books?author=tolkien", []book.Book{hobbit, lotr}},
		{"author filter matches part of a name", "/books?author=herbert", []book.Book{dune}},
		{"surrounding spaces are ignored", "/books?author=%20Frank%20Herbert%20", []book.Book{dune}},
		{"no matches", "/books?author=nobody", nil},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			r := do(t, srv, http.MethodGet, tc.path, "")
			if r.status != http.StatusOK {
				t.Fatalf("status = %d; want 200 (body %s)", r.status, r.body)
			}
			if len(tc.want) == 0 {
				if strings.TrimSpace(r.body) != "[]" {
					t.Errorf("body = %s; want an empty JSON array", r.body)
				}
				return
			}
			var got []book.Book
			decode(t, r, &got)
			if !slices.Equal(got, tc.want) {
				t.Errorf("books = %+v; want %+v", got, tc.want)
			}
		})
	}
}

func TestGetBookNotFoundAndBadID(t *testing.T) {
	srv := newTestServer(t)

	tests := []struct {
		name   string
		path   string
		status int
	}{
		{"unknown id", "/books/999999", http.StatusNotFound},
		{"non-numeric id", "/books/abc", http.StatusBadRequest},
		{"zero id", "/books/0", http.StatusBadRequest},
		{"negative id", "/books/-4", http.StatusBadRequest},
		{"fractional id", "/books/1.5", http.StatusBadRequest},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			assertJSONError(t, do(t, srv, http.MethodGet, tc.path, ""), tc.status)
		})
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	path := fmt.Sprintf("/books/%d", created.ID)

	// PUT replaces the whole book, so the omitted ISBN is cleared and the ID is kept.
	// A client echoing back the "id" field must not be able to change it.
	r := do(t, srv, http.MethodPut, path, `{"id":999,"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
	if r.status != http.StatusOK {
		t.Fatalf("PUT status = %d; want 200 (body %s)", r.status, r.body)
	}
	want := book.Book{ID: created.ID, Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969}
	var updated book.Book
	decode(t, r, &updated)
	if updated != want {
		t.Errorf("PUT body = %+v; want %+v", updated, want)
	}

	// A rejected update must leave the stored book unchanged.
	assertJSONError(t, do(t, srv, http.MethodPut, path, `{"title":"Broken"}`), http.StatusBadRequest)
	var stored book.Book
	decode(t, do(t, srv, http.MethodGet, path, ""), &stored)
	if stored != want {
		t.Errorf("stored book after rejected PUT = %+v; want %+v", stored, want)
	}

	assertJSONError(t,
		do(t, srv, http.MethodPut, "/books/999999", `{"title":"Ghost","author":"Nobody"}`),
		http.StatusNotFound)
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, `{"title":"Dune","author":"Frank Herbert"}`)
	path := fmt.Sprintf("/books/%d", created.ID)

	r := do(t, srv, http.MethodDelete, path, "")
	if r.status != http.StatusNoContent {
		t.Fatalf("DELETE status = %d; want 204 (body %s)", r.status, r.body)
	}
	if r.body != "" {
		t.Errorf("DELETE body = %q; want empty", r.body)
	}

	assertJSONError(t, do(t, srv, http.MethodGet, path, ""), http.StatusNotFound)
	assertJSONError(t, do(t, srv, http.MethodDelete, path, ""), http.StatusNotFound)
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)

	r := do(t, srv, http.MethodGet, "/health", "")
	if r.status != http.StatusOK {
		t.Fatalf("GET /health status = %d; want 200 (body %s)", r.status, r.body)
	}
	var health map[string]string
	decode(t, r, &health)
	if health["status"] != "ok" {
		t.Errorf("health = %v; want status ok", health)
	}

	if head := do(t, srv, http.MethodHead, "/health", ""); head.status != http.StatusOK {
		t.Errorf("HEAD /health status = %d; want 200", head.status)
	}
}

func TestHealthReportsUnavailableDatabase(t *testing.T) {
	st, err := store.Open(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	srv := httptest.NewServer(api.NewRouter(st, slog.New(slog.NewTextHandler(io.Discard, nil))))
	t.Cleanup(srv.Close)
	st.Close() // the database is gone, so the health check must fail

	r := do(t, srv, http.MethodGet, "/health", "")
	if r.status != http.StatusServiceUnavailable {
		t.Fatalf("GET /health status = %d; want 503 (body %s)", r.status, r.body)
	}
	var health map[string]string
	decode(t, r, &health)
	if health["status"] != "unavailable" {
		t.Errorf("health = %v; want status unavailable", health)
	}
}

func TestUnknownRoutesAndMethodsReturnJSON(t *testing.T) {
	srv := newTestServer(t)

	tests := []struct {
		name   string
		method string
		path   string
		status int
		allow  string // expected Allow header, empty if none is required
	}{
		{"unknown path", http.MethodGet, "/nope", http.StatusNotFound, ""},
		{"trailing slash on collection", http.MethodGet, "/books/", http.StatusNotFound, ""},
		{"extra path segment", http.MethodGet, "/books/1/extra", http.StatusNotFound, ""},
		{"unsupported method on collection", http.MethodPatch, "/books", http.StatusMethodNotAllowed, "GET, HEAD, POST"},
		{"unsupported method on item", http.MethodPost, "/books/1", http.StatusMethodNotAllowed, "DELETE, GET, HEAD, PUT"},
		{"unsupported method on health", http.MethodPost, "/health", http.StatusMethodNotAllowed, "GET, HEAD"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			r := do(t, srv, tc.method, tc.path, "")
			assertJSONError(t, r, tc.status)
			if tc.allow != "" {
				if got := r.header.Get("Allow"); got != tc.allow {
					t.Errorf("Allow = %q; want %q", got, tc.allow)
				}
			}
		})
	}
}
