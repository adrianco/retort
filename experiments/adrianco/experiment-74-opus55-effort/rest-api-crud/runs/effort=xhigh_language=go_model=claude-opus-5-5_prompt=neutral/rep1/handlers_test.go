package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
)

// testAPI is a running HTTP server backed by a fresh on-disk SQLite database.
type testAPI struct {
	t     *testing.T
	srv   *httptest.Server
	store *Store
}

func newTestAPI(t *testing.T) *testAPI {
	t.Helper()
	store := newTestStore(t)
	srv := httptest.NewServer(NewServer(store, slog.New(slog.DiscardHandler)))
	t.Cleanup(srv.Close)
	return &testAPI{t: t, srv: srv, store: store}
}

// do sends a request. A string body is sent verbatim (to test malformed input);
// anything else is JSON-encoded.
func (a *testAPI) do(method, path string, body any) (*http.Response, []byte) {
	a.t.Helper()
	var reader io.Reader
	switch b := body.(type) {
	case nil:
	case string:
		reader = strings.NewReader(b)
	default:
		buf, err := json.Marshal(b)
		if err != nil {
			a.t.Fatalf("marshal body: %v", err)
		}
		reader = bytes.NewReader(buf)
	}
	req, err := http.NewRequest(method, a.srv.URL+path, reader)
	if err != nil {
		a.t.Fatalf("new request: %v", err)
	}
	if reader != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := a.srv.Client().Do(req)
	if err != nil {
		a.t.Fatalf("%s %s: %v", method, path, err)
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		a.t.Fatalf("read body: %v", err)
	}
	return resp, data
}

// expect sends a request, asserts the status code and JSON content type (for
// non-empty bodies), and decodes the response into out if non-nil.
func (a *testAPI) expect(method, path string, body any, wantStatus int, out any) *http.Response {
	a.t.Helper()
	resp, data := a.do(method, path, body)
	if resp.StatusCode != wantStatus {
		a.t.Fatalf("%s %s: status = %d, want %d; body: %s", method, path, resp.StatusCode, wantStatus, data)
	}
	if len(data) > 0 {
		if ct := resp.Header.Get("Content-Type"); ct != "application/json" {
			a.t.Errorf("%s %s: Content-Type = %q, want application/json", method, path, ct)
		}
	}
	if out != nil {
		if err := json.Unmarshal(data, out); err != nil {
			a.t.Fatalf("%s %s: decode response %q: %v", method, path, data, err)
		}
	}
	return resp
}

func (a *testAPI) createBook(in BookInput) Book {
	a.t.Helper()
	var b Book
	a.expect(http.MethodPost, "/books", in, http.StatusCreated, &b)
	return b
}

func TestHealth(t *testing.T) {
	api := newTestAPI(t)
	var body map[string]string
	api.expect(http.MethodGet, "/health", nil, http.StatusOK, &body)
	if body["status"] != "ok" {
		t.Errorf("health body = %v, want status ok", body)
	}
}

func TestHealthReportsUnavailableDatabase(t *testing.T) {
	api := newTestAPI(t)
	api.store.Close()
	var body map[string]string
	api.expect(http.MethodGet, "/health", nil, http.StatusServiceUnavailable, &body)
	if body["status"] != "unavailable" {
		t.Errorf("health body = %v, want status unavailable", body)
	}
}

func TestCreateBook(t *testing.T) {
	api := newTestAPI(t)

	var got Book
	resp := api.expect(http.MethodPost, "/books", map[string]any{
		"title":  "  Dune  ",
		"author": "Frank Herbert",
		"year":   1965,
		"isbn":   "978-0-441-17271-9",
	}, http.StatusCreated, &got)

	if got.ID < 1 {
		t.Errorf("ID = %d, want positive", got.ID)
	}
	if got.Title != "Dune" || got.Author != "Frank Herbert" || got.Year != 1965 || got.ISBN != "978-0-441-17271-9" {
		t.Errorf("created book = %+v", got)
	}
	if got.CreatedAt.IsZero() || got.UpdatedAt.IsZero() {
		t.Errorf("timestamps not set: %+v", got)
	}
	if loc, want := resp.Header.Get("Location"), fmt.Sprintf("/books/%d", got.ID); loc != want {
		t.Errorf("Location = %q, want %q", loc, want)
	}

	// The new book is retrievable at its Location.
	var fetched Book
	api.expect(http.MethodGet, resp.Header.Get("Location"), nil, http.StatusOK, &fetched)
	if !sameBook(fetched, got) {
		t.Errorf("GET after create = %+v, want %+v", fetched, got)
	}
}

func TestCreateBookOptionalFieldsOmitted(t *testing.T) {
	api := newTestAPI(t)
	got := api.createBook(BookInput{Title: "Beowulf", Author: "Unknown"})
	if got.Year != 0 || got.ISBN != "" {
		t.Errorf("optional fields = year %d, isbn %q; want zero values", got.Year, got.ISBN)
	}
}

func TestCreateBookValidation(t *testing.T) {
	tests := []struct {
		name       string
		body       any
		wantStatus int
		wantFields []string // for field validation failures
		wantError  string   // substring of the error message
	}{
		{name: "missing title", body: map[string]any{"author": "A"},
			wantStatus: 400, wantFields: []string{"title"}},
		{name: "missing author", body: map[string]any{"title": "T"},
			wantStatus: 400, wantFields: []string{"author"}},
		{name: "blank title and author", body: map[string]any{"title": "  ", "author": "\t"},
			wantStatus: 400, wantFields: []string{"title", "author"}},
		{name: "null title", body: `{"title": null, "author": "A"}`,
			wantStatus: 400, wantFields: []string{"title"}},
		{name: "negative year", body: map[string]any{"title": "T", "author": "A", "year": -5},
			wantStatus: 400, wantFields: []string{"year"}},
		{name: "bad isbn", body: map[string]any{"title": "T", "author": "A", "isbn": "not-an-isbn"},
			wantStatus: 400, wantFields: []string{"isbn"}},
		{name: "empty body", body: "",
			wantStatus: 400, wantError: "must not be empty"},
		{name: "malformed JSON", body: `{"title": "T",`,
			wantStatus: 400, wantError: "malformed JSON"},
		{name: "invalid JSON syntax", body: `{"title": 'T'}`,
			wantStatus: 400, wantError: "malformed JSON"},
		{name: "wrong field type", body: `{"title": "T", "author": "A", "year": "1965"}`,
			wantStatus: 400, wantError: `"year"`},
		{name: "non-object body", body: `["T", "A"]`,
			wantStatus: 400, wantError: "must be a JSON object"},
		{name: "trailing data", body: `{"title": "T", "author": "A"} {"title": "U"}`,
			wantStatus: 400, wantError: "single JSON object"},
		{name: "body too large", body: `{"title": "` + strings.Repeat("x", maxBodyBytes) + `", "author": "A"}`,
			wantStatus: 413, wantError: "must not exceed"},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			api := newTestAPI(t)
			var body struct {
				Error  string            `json:"error"`
				Fields map[string]string `json:"fields"`
			}
			api.expect(http.MethodPost, "/books", tc.body, tc.wantStatus, &body)

			if body.Error == "" {
				t.Errorf("response has no error message")
			}
			if tc.wantError != "" && !strings.Contains(body.Error, tc.wantError) {
				t.Errorf("error = %q, want it to contain %q", body.Error, tc.wantError)
			}
			if len(body.Fields) != len(tc.wantFields) {
				t.Errorf("fields = %v, want errors for %v", body.Fields, tc.wantFields)
			}
			for _, f := range tc.wantFields {
				if body.Fields[f] == "" {
					t.Errorf("fields = %v, missing %q", body.Fields, f)
				}
			}

			// Nothing may have been stored.
			var books []Book
			api.expect(http.MethodGet, "/books", nil, http.StatusOK, &books)
			if len(books) != 0 {
				t.Errorf("invalid request stored %d book(s)", len(books))
			}
		})
	}
}

func TestListBooks(t *testing.T) {
	api := newTestAPI(t)

	// An empty collection is an empty JSON array, not null.
	_, raw := api.do(http.MethodGet, "/books", nil)
	if got := strings.TrimSpace(string(raw)); got != "[]" {
		t.Fatalf("empty list body = %s, want []", got)
	}

	emma := api.createBook(BookInput{Title: "Emma", Author: "Jane Austen", Year: 1815})
	dune := api.createBook(BookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965})
	persuasion := api.createBook(BookInput{Title: "Persuasion", Author: "Jane Austen", Year: 1817})

	tests := []struct {
		query string
		want  []Book
	}{
		{"/books", []Book{emma, dune, persuasion}},
		{"/books?author=Jane%20Austen", []Book{emma, persuasion}},
		{"/books?author=jane+austen", []Book{emma, persuasion}},
		{"/books?author=Frank%20Herbert", []Book{dune}},
		{"/books?author=Austen", []Book{}}, // exact match, not substring
		{"/books?author=", []Book{emma, dune, persuasion}},
	}
	for _, tc := range tests {
		var got []Book
		api.expect(http.MethodGet, tc.query, nil, http.StatusOK, &got)
		if len(got) != len(tc.want) {
			t.Errorf("GET %s returned %d books, want %d: %+v", tc.query, len(got), len(tc.want), got)
			continue
		}
		for i := range got {
			if !sameBook(got[i], tc.want[i]) {
				t.Errorf("GET %s [%d] = %+v, want %+v", tc.query, i, got[i], tc.want[i])
			}
		}
	}
}

func TestGetBook(t *testing.T) {
	api := newTestAPI(t)
	created := api.createBook(BookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965})

	var got Book
	api.expect(http.MethodGet, fmt.Sprintf("/books/%d", created.ID), nil, http.StatusOK, &got)
	if !sameBook(got, created) {
		t.Errorf("GET = %+v, want %+v", got, created)
	}

	var errBody errorResponse
	api.expect(http.MethodGet, "/books/9999", nil, http.StatusNotFound, &errBody)
	if errBody.Error != "book not found" {
		t.Errorf("404 error = %q", errBody.Error)
	}

	for _, id := range []string{"abc", "0", "-1", "1.5", "99999999999999999999"} {
		api.expect(http.MethodGet, "/books/"+id, nil, http.StatusBadRequest, nil)
	}
}

func TestUpdateBook(t *testing.T) {
	api := newTestAPI(t)
	created := api.createBook(BookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"})
	path := fmt.Sprintf("/books/%d", created.ID)

	var updated Book
	api.expect(http.MethodPut, path, BookInput{Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969},
		http.StatusOK, &updated)
	if updated.ID != created.ID || updated.Title != "Dune Messiah" || updated.Year != 1969 {
		t.Errorf("updated book = %+v", updated)
	}
	if updated.ISBN != "" {
		t.Errorf("PUT is a full replacement; omitted isbn should be cleared, got %q", updated.ISBN)
	}
	if !updated.CreatedAt.Equal(created.CreatedAt) {
		t.Errorf("created_at changed: %v -> %v", created.CreatedAt, updated.CreatedAt)
	}
	if updated.UpdatedAt.Before(created.UpdatedAt) {
		t.Errorf("updated_at went backwards: %v -> %v", created.UpdatedAt, updated.UpdatedAt)
	}

	// The change is persisted.
	var fetched Book
	api.expect(http.MethodGet, path, nil, http.StatusOK, &fetched)
	if !sameBook(fetched, updated) {
		t.Errorf("GET after PUT = %+v, want %+v", fetched, updated)
	}

	// Validation applies to updates, and a failed update leaves the book untouched.
	var verr validationErrorResponse
	api.expect(http.MethodPut, path, map[string]any{"title": "", "author": "Frank Herbert"}, http.StatusBadRequest, &verr)
	if verr.Fields["title"] == "" {
		t.Errorf("validation fields = %v, want title error", verr.Fields)
	}
	api.expect(http.MethodGet, path, nil, http.StatusOK, &fetched)
	if !sameBook(fetched, updated) {
		t.Errorf("failed PUT modified the book: %+v", fetched)
	}

	api.expect(http.MethodPut, "/books/9999", BookInput{Title: "T", Author: "A"}, http.StatusNotFound, nil)
	api.expect(http.MethodPut, "/books/abc", BookInput{Title: "T", Author: "A"}, http.StatusBadRequest, nil)
	api.expect(http.MethodPut, path, "{bad json", http.StatusBadRequest, nil)
}

func TestDeleteBook(t *testing.T) {
	api := newTestAPI(t)
	keep := api.createBook(BookInput{Title: "Emma", Author: "Jane Austen"})
	doomed := api.createBook(BookInput{Title: "Dune", Author: "Frank Herbert"})
	path := fmt.Sprintf("/books/%d", doomed.ID)

	resp, body := api.do(http.MethodDelete, path, nil)
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("DELETE status = %d, want 204; body: %s", resp.StatusCode, body)
	}
	if len(body) != 0 {
		t.Errorf("DELETE body = %q, want empty", body)
	}

	api.expect(http.MethodGet, path, nil, http.StatusNotFound, nil)
	api.expect(http.MethodDelete, path, nil, http.StatusNotFound, nil)
	api.expect(http.MethodDelete, "/books/abc", nil, http.StatusBadRequest, nil)

	// Other books are unaffected.
	var books []Book
	api.expect(http.MethodGet, "/books", nil, http.StatusOK, &books)
	if len(books) != 1 || books[0].ID != keep.ID {
		t.Errorf("remaining books = %+v, want only %d", books, keep.ID)
	}
}

func TestUnsupportedMethodsAndRoutes(t *testing.T) {
	api := newTestAPI(t)

	tests := []struct {
		method, path string
		wantStatus   int
		wantAllow    string
	}{
		{http.MethodPatch, "/books/1", http.StatusMethodNotAllowed, "GET, HEAD, PUT, DELETE"},
		{http.MethodDelete, "/books", http.StatusMethodNotAllowed, "GET, HEAD, POST"},
		{http.MethodPost, "/health", http.StatusMethodNotAllowed, "GET, HEAD"},
		{http.MethodGet, "/authors", http.StatusNotFound, ""},
		{http.MethodGet, "/books/1/extra", http.StatusNotFound, ""},
	}
	for _, tc := range tests {
		var body errorResponse
		resp := api.expect(tc.method, tc.path, nil, tc.wantStatus, &body)
		if body.Error == "" {
			t.Errorf("%s %s: missing JSON error body", tc.method, tc.path)
		}
		if got := resp.Header.Get("Allow"); got != tc.wantAllow {
			t.Errorf("%s %s: Allow = %q, want %q", tc.method, tc.path, got, tc.wantAllow)
		}
	}
}

func TestPanicRecovery(t *testing.T) {
	s := &Server{logger: slog.New(slog.DiscardHandler)}
	h := s.middleware(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {
		panic("boom")
	}))

	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/", nil))

	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500", rec.Code)
	}
	var body errorResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil || body.Error != "internal server error" {
		t.Errorf("body = %q (err %v), want generic JSON error", rec.Body.String(), err)
	}
}

func TestConcurrentWrites(t *testing.T) {
	api := newTestAPI(t)
	const n = 25

	var wg sync.WaitGroup
	errs := make(chan error, n)
	for i := range n {
		wg.Add(1)
		go func() {
			defer wg.Done()
			body := fmt.Sprintf(`{"title": "Book %d", "author": "Author %d"}`, i, i%3)
			resp, err := api.srv.Client().Post(api.srv.URL+"/books", "application/json", strings.NewReader(body))
			if err != nil {
				errs <- err
				return
			}
			resp.Body.Close()
			if resp.StatusCode != http.StatusCreated {
				errs <- fmt.Errorf("status %d", resp.StatusCode)
			}
		}()
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		t.Errorf("concurrent create failed: %v", err)
	}

	var books []Book
	api.expect(http.MethodGet, "/books", nil, http.StatusOK, &books)
	if len(books) != n {
		t.Errorf("stored %d books, want %d", len(books), n)
	}
}
