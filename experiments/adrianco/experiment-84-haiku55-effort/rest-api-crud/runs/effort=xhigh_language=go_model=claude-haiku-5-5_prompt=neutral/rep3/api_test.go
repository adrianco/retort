package main

import (
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"net/url"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

// newTestServer serves the full API over a fresh SQLite file in a temp dir.
func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { _ = store.Close() })

	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	srv := httptest.NewServer(newServer(store, logger))
	t.Cleanup(srv.Close)
	return srv
}

type response struct {
	status int
	header http.Header
	body   []byte
}

// send issues a request and returns the status, headers, and full body.
// A non-empty body is sent as application/json.
func send(t *testing.T, srv *httptest.Server, method, path, body string) response {
	t.Helper()
	var rdr io.Reader
	if body != "" {
		rdr = strings.NewReader(body)
	}
	req, err := http.NewRequest(method, srv.URL+path, rdr)
	if err != nil {
		t.Fatalf("NewRequest: %v", err)
	}
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := srv.Client().Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, path, err)
	}
	defer resp.Body.Close()
	b, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read body: %v", err)
	}
	return response{status: resp.StatusCode, header: resp.Header, body: b}
}

// expectStatus fails the test unless r has the wanted status code.
func expectStatus(t *testing.T, r response, want int) {
	t.Helper()
	if r.status != want {
		t.Fatalf("status = %d, want %d; body: %s", r.status, want, r.body)
	}
}

// decode unmarshals the response body into v.
func decode(t *testing.T, r response, v any) {
	t.Helper()
	if err := json.Unmarshal(r.body, v); err != nil {
		t.Fatalf("decode %q: %v", r.body, err)
	}
}

// createBook posts a book and returns the stored representation.
func createBook(t *testing.T, srv *httptest.Server, body string) Book {
	t.Helper()
	r := send(t, srv, http.MethodPost, "/books", body)
	expectStatus(t, r, http.StatusCreated)
	var b Book
	decode(t, r, &b)
	return b
}

func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)

	r := send(t, srv, http.MethodPost, "/books",
		`{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0-306-40615-7"}`)
	expectStatus(t, r, http.StatusCreated)
	if loc := r.header.Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}
	if ct := r.header.Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
	var created Book
	decode(t, r, &created)
	if created.ID != 1 || created.Title != "The Hobbit" || created.Year == nil || *created.Year != 1937 {
		t.Errorf("created = %+v", created)
	}
	if created.ISBN == nil || *created.ISBN != "9780306406157" {
		t.Errorf("ISBN should be stored normalized, got %v", created.ISBN)
	}

	r = send(t, srv, http.MethodGet, "/books/1", "")
	expectStatus(t, r, http.StatusOK)
	var fetched Book
	decode(t, r, &fetched)
	if fetched.Title != created.Title || fetched.Author != created.Author || *fetched.Year != 1937 {
		t.Errorf("fetched = %+v, want %+v", fetched, created)
	}
}

func TestCreateBookWithoutOptionalFieldsReturnsNull(t *testing.T) {
	srv := newTestServer(t)

	r := send(t, srv, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert"}`)
	expectStatus(t, r, http.StatusCreated)
	var raw map[string]any
	decode(t, r, &raw)
	if raw["year"] != nil || raw["isbn"] != nil {
		t.Errorf("unset optional fields should be null, got %v", raw)
	}
}

func TestCreateBookValidationErrors(t *testing.T) {
	srv := newTestServer(t)

	tests := []struct {
		name       string
		body       string
		wantField  string // expected key under "fields"; empty for non-validation errors
		wantStatus int
	}{
		{"missing title", `{"author":"Frank Herbert"}`, "title", http.StatusBadRequest},
		{"blank author", `{"title":"Dune","author":"  "}`, "author", http.StatusBadRequest},
		{"bad year", `{"title":"Dune","author":"FH","year":-5}`, "year", http.StatusBadRequest},
		{"bad isbn", `{"title":"Dune","author":"FH","isbn":"123"}`, "isbn", http.StatusBadRequest},
		{"unknown field", `{"title":"Dune","author":"FH","pages":412}`, "", http.StatusBadRequest},
		{"malformed json", `{"title":`, "", http.StatusBadRequest},
		{"wrong type", `{"title":"Dune","author":"FH","year":"1965"}`, "", http.StatusBadRequest},
		{"trailing content", `{"title":"Dune","author":"FH"}{}`, "", http.StatusBadRequest},
		{"empty body", ``, "", http.StatusBadRequest},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			r := send(t, srv, http.MethodPost, "/books", tt.body)
			expectStatus(t, r, tt.wantStatus)

			var body struct {
				Error  string            `json:"error"`
				Fields map[string]string `json:"fields"`
			}
			decode(t, r, &body)
			if body.Error == "" {
				t.Errorf("error response has no message: %s", r.body)
			}
			if tt.wantField != "" {
				if _, ok := body.Fields[tt.wantField]; !ok {
					t.Errorf("expected field error on %q, got %v", tt.wantField, body.Fields)
				}
			}
		})
	}

	// Nothing should have been stored by any of the rejected requests.
	r := send(t, srv, http.MethodGet, "/books", "")
	var all []Book
	decode(t, r, &all)
	if len(all) != 0 {
		t.Errorf("rejected requests stored %d books", len(all))
	}
}

func TestCreateBookRejectsOversizedBody(t *testing.T) {
	srv := newTestServer(t)
	huge := `{"title":"` + strings.Repeat("a", maxBodyBytes) + `","author":"A"}`
	expectStatus(t, send(t, srv, http.MethodPost, "/books", huge), http.StatusRequestEntityTooLarge)
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	createBook(t, srv, `{"title":"A Wizard of Earthsea","author":"Ursula K. Le Guin"}`)
	createBook(t, srv, `{"title":"Dune","author":"Frank Herbert"}`)
	createBook(t, srv, `{"title":"The Dispossessed","author":"Ursula K. Le Guin"}`)

	r := send(t, srv, http.MethodGet, "/books", "")
	expectStatus(t, r, http.StatusOK)
	var all []Book
	decode(t, r, &all)
	if len(all) != 3 {
		t.Errorf("GET /books returned %d books, want 3", len(all))
	}

	query := "/books?author=" + url.QueryEscape("ursula k. le guin")
	r = send(t, srv, http.MethodGet, query, "")
	expectStatus(t, r, http.StatusOK)
	var filtered []Book
	decode(t, r, &filtered)
	if len(filtered) != 2 {
		t.Errorf("author filter returned %d books, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Ursula K. Le Guin" {
			t.Errorf("filter leaked book by %q", b.Author)
		}
	}

	r = send(t, srv, http.MethodGet, "/books?author=nobody", "")
	expectStatus(t, r, http.StatusOK)
	if strings.TrimSpace(string(r.body)) != "[]" {
		t.Errorf("empty result body = %s, want []", r.body)
	}
}

func TestListBooksEmptyCollectionIsArray(t *testing.T) {
	srv := newTestServer(t)
	r := send(t, srv, http.MethodGet, "/books", "")
	expectStatus(t, r, http.StatusOK)
	if strings.TrimSpace(string(r.body)) != "[]" {
		t.Errorf("empty collection body = %s, want []", r.body)
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"0306406152"}`)
	path := "/books/" + strconv.FormatInt(created.ID, 10)

	// PUT replaces the whole record, so omitting year and isbn clears them.
	r := send(t, srv, http.MethodPut, path, `{"title":"Dune (revised)","author":"Frank Herbert"}`)
	expectStatus(t, r, http.StatusOK)
	var updated Book
	decode(t, r, &updated)
	if updated.ID != created.ID || updated.Title != "Dune (revised)" {
		t.Errorf("updated = %+v", updated)
	}
	if updated.Year != nil || updated.ISBN != nil {
		t.Errorf("omitted optional fields should be cleared, got %+v", updated)
	}

	r = send(t, srv, http.MethodGet, path, "")
	expectStatus(t, r, http.StatusOK)
	var fetched Book
	decode(t, r, &fetched)
	if fetched.Title != "Dune (revised)" {
		t.Errorf("update not persisted: %+v", fetched)
	}
}

func TestUpdateBookErrors(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, `{"title":"Dune","author":"Frank Herbert"}`)

	expectStatus(t, send(t, srv, http.MethodPut, "/books/9999", `{"title":"X","author":"Y"}`), http.StatusNotFound)
	expectStatus(t, send(t, srv, http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10), `{"title":""}`), http.StatusBadRequest)
	expectStatus(t, send(t, srv, http.MethodPut, "/books/abc", `{"title":"X","author":"Y"}`), http.StatusBadRequest)
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, `{"title":"Dune","author":"Frank Herbert"}`)
	path := "/books/" + strconv.FormatInt(created.ID, 10)

	r := send(t, srv, http.MethodDelete, path, "")
	expectStatus(t, r, http.StatusNoContent)
	if len(r.body) != 0 {
		t.Errorf("204 response should have no body, got %q", r.body)
	}

	expectStatus(t, send(t, srv, http.MethodGet, path, ""), http.StatusNotFound)
	expectStatus(t, send(t, srv, http.MethodDelete, path, ""), http.StatusNotFound)
}

func TestGetBookNotFoundAndInvalidID(t *testing.T) {
	srv := newTestServer(t)

	r := send(t, srv, http.MethodGet, "/books/9999", "")
	expectStatus(t, r, http.StatusNotFound)
	var body map[string]string
	decode(t, r, &body)
	if body["error"] == "" {
		t.Errorf("404 response has no error message: %s", r.body)
	}

	for _, id := range []string{"abc", "0", "-1", "1.5"} {
		expectStatus(t, send(t, srv, http.MethodGet, "/books/"+id, ""), http.StatusBadRequest)
	}
}

func TestHealthEndpoint(t *testing.T) {
	srv := newTestServer(t)

	r := send(t, srv, http.MethodGet, "/health", "")
	expectStatus(t, r, http.StatusOK)
	var body map[string]string
	decode(t, r, &body)
	if body["status"] != "ok" {
		t.Errorf("health body = %v, want status ok", body)
	}
}

func TestUnknownRoutesAndMethodsReturnJSON(t *testing.T) {
	srv := newTestServer(t)

	r := send(t, srv, http.MethodGet, "/nope", "")
	expectStatus(t, r, http.StatusNotFound)
	if ct := r.header.Get("Content-Type"); ct != "application/json" {
		t.Errorf("404 Content-Type = %q, want application/json", ct)
	}

	r = send(t, srv, http.MethodPatch, "/books", `{}`)
	expectStatus(t, r, http.StatusMethodNotAllowed)
	if allow := r.header.Get("Allow"); allow != "GET, POST" {
		t.Errorf("Allow = %q, want \"GET, POST\"", allow)
	}

	r = send(t, srv, http.MethodPost, "/books/1", `{}`)
	expectStatus(t, r, http.StatusMethodNotAllowed)
	if allow := r.header.Get("Allow"); allow != "GET, PUT, DELETE" {
		t.Errorf("Allow = %q, want \"GET, PUT, DELETE\"", allow)
	}

	expectStatus(t, send(t, srv, http.MethodPost, "/health", ""), http.StatusMethodNotAllowed)
}
