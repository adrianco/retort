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
	"time"
)

// newTestServer serves the API over a fresh database file. The store is
// returned so tests can break it deliberately.
func newTestServer(t *testing.T) (*httptest.Server, *Store) {
	t.Helper()
	store := newTestStore(t)
	srv := httptest.NewServer(NewHandler(store, slog.New(slog.DiscardHandler)))
	t.Cleanup(srv.Close)
	return srv, store
}

// do sends a request with an optional JSON body, checks the response status
// and returns the response together with its body.
func do(t *testing.T, srv *httptest.Server, method, path, body string, wantStatus int) (*http.Response, []byte) {
	t.Helper()
	req, err := http.NewRequestWithContext(t.Context(), method, srv.URL+path, strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := srv.Client().Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatal(err)
	}
	if resp.StatusCode != wantStatus {
		t.Fatalf("%s %s: status = %d, want %d; body: %s", method, path, resp.StatusCode, wantStatus, respBody)
	}
	if ct := resp.Header.Get("Content-Type"); wantStatus != http.StatusNoContent && ct != "application/json" {
		t.Errorf("%s %s: Content-Type = %q, want application/json", method, path, ct)
	}
	return resp, respBody
}

// decode unmarshals a JSON response body.
func decode[T any](t *testing.T, body []byte) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(body, &v); err != nil {
		t.Fatalf("decoding %s: %v", body, err)
	}
	return v
}

func createBook(t *testing.T, srv *httptest.Server, body string) Book {
	t.Helper()
	_, respBody := do(t, srv, http.MethodPost, "/books", body, http.StatusCreated)
	return decode[Book](t, respBody)
}

func TestHealth(t *testing.T) {
	srv, store := newTestServer(t)

	_, body := do(t, srv, http.MethodGet, "/health", "", http.StatusOK)
	assertEqual(t, decode[map[string]string](t, body), map[string]string{"status": "ok"})

	store.Close()
	_, body = do(t, srv, http.MethodGet, "/health", "", http.StatusServiceUnavailable)
	assertEqual(t, decode[map[string]string](t, body), map[string]string{"status": "unavailable"})
}

// TestBookLifecycle takes one book through every CRUD endpoint.
func TestBookLifecycle(t *testing.T) {
	srv, _ := newTestServer(t)

	resp, body := do(t, srv, http.MethodPost, "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}`, http.StatusCreated)
	created := decode[Book](t, body)
	if created.ID < 1 {
		t.Fatalf("created book has ID %d, want a positive ID", created.ID)
	}
	assertEqual(t, created, Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: "978-0441013593"})
	path := fmt.Sprintf("/books/%d", created.ID)
	if loc := resp.Header.Get("Location"); loc != path {
		t.Errorf("Location = %q, want %q", loc, path)
	}

	_, body = do(t, srv, http.MethodGet, path, "", http.StatusOK)
	assertEqual(t, decode[Book](t, body), created)

	_, body = do(t, srv, http.MethodGet, "/books", "", http.StatusOK)
	assertEqual(t, decode[[]Book](t, body), []Book{created})

	// PUT replaces the book: the ISBN left out of the body is cleared.
	_, body = do(t, srv, http.MethodPut, path, `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`, http.StatusOK)
	updated := decode[Book](t, body)
	assertEqual(t, updated, Book{ID: created.ID, Title: "Dune Messiah", Author: "Frank Herbert", Year: ptr(1969)})
	_, body = do(t, srv, http.MethodGet, path, "", http.StatusOK)
	assertEqual(t, decode[Book](t, body), updated)

	// A client may send back a book exactly as received, ID included.
	_, body = do(t, srv, http.MethodPut, path, string(body), http.StatusOK)
	assertEqual(t, decode[Book](t, body), updated)

	_, body = do(t, srv, http.MethodDelete, path, "", http.StatusNoContent)
	if len(body) != 0 {
		t.Errorf("DELETE returned body %q, want none", body)
	}

	do(t, srv, http.MethodGet, path, "", http.StatusNotFound)
	do(t, srv, http.MethodPut, path, `{"title":"Dune","author":"Frank Herbert"}`, http.StatusNotFound)
	do(t, srv, http.MethodDelete, path, "", http.StatusNotFound)
	_, body = do(t, srv, http.MethodGet, "/books", "", http.StatusOK)
	assertEqual(t, decode[[]Book](t, body), []Book{})
}

func TestCreateBookNormalizesInput(t *testing.T) {
	srv, _ := newTestServer(t)

	got := createBook(t, srv, `{"title":"  Pride & Prejudice ","author":"\tJane Austen\n","year":null,"isbn":" "}`)
	assertEqual(t, got, Book{ID: got.ID, Title: "Pride & Prejudice", Author: "Jane Austen"})
}

func TestCreateBookRejectsInvalidInput(t *testing.T) {
	srv, _ := newTestServer(t)
	yearErr := fmt.Sprintf("must be between 1 and %d", time.Now().Year()+1)

	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantError  string
		wantFields ValidationError
	}{
		{
			name:       "missing title",
			body:       `{"author":"Frank Herbert","year":1965}`,
			wantStatus: http.StatusBadRequest,
			wantError:  "validation failed: title is required",
			wantFields: ValidationError{"title": "is required"},
		},
		{
			name:       "missing author",
			body:       `{"title":"Dune"}`,
			wantStatus: http.StatusBadRequest,
			wantError:  "validation failed: author is required",
			wantFields: ValidationError{"author": "is required"},
		},
		{
			name:       "blank title and author",
			body:       `{"title":"   ","author":""}`,
			wantStatus: http.StatusBadRequest,
			wantError:  "validation failed: author is required; title is required",
			wantFields: ValidationError{"author": "is required", "title": "is required"},
		},
		{
			name:       "year out of range",
			body:       `{"title":"Dune","author":"Frank Herbert","year":0}`,
			wantStatus: http.StatusBadRequest,
			wantError:  "validation failed: year " + yearErr,
			wantFields: ValidationError{"year": yearErr},
		},
		{
			name:       "year is a string",
			body:       `{"title":"Dune","author":"Frank Herbert","year":"1965"}`,
			wantStatus: http.StatusBadRequest,
			wantError:  "year must be an integer",
		},
		{
			name:       "year is fractional",
			body:       `{"title":"Dune","author":"Frank Herbert","year":1965.5}`,
			wantStatus: http.StatusBadRequest,
			wantError:  "year must be an integer",
		},
		{
			name:       "title is a number",
			body:       `{"title":1984,"author":"George Orwell"}`,
			wantStatus: http.StatusBadRequest,
			wantError:  "title must be a string",
		},
		{
			name:       "empty body",
			body:       "",
			wantStatus: http.StatusBadRequest,
			wantError:  "request body must not be empty",
		},
		{
			name:       "malformed JSON",
			body:       `{"title":"Dune",`,
			wantStatus: http.StatusBadRequest,
			wantError:  "request body is not valid JSON",
		},
		{
			name:       "not an object",
			body:       `["Dune","Frank Herbert"]`,
			wantStatus: http.StatusBadRequest,
			wantError:  "request body must be a JSON object",
		},
		{
			name:       "trailing data",
			body:       `{"title":"Dune","author":"Frank Herbert"}{"title":"Emma"}`,
			wantStatus: http.StatusBadRequest,
			wantError:  "request body must contain a single JSON object",
		},
		{
			name:       "body too large",
			body:       `{"title":"Dune","author":"Frank Herbert","isbn":"` + strings.Repeat(" ", maxBodyBytes) + `"}`,
			wantStatus: http.StatusRequestEntityTooLarge,
			wantError:  "request body must not exceed 1048576 bytes",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, body := do(t, srv, http.MethodPost, "/books", tt.body, tt.wantStatus)
			assertEqual(t, decode[errorResponse](t, body), errorResponse{Error: tt.wantError, Fields: tt.wantFields})
		})
	}

	// None of the rejected requests stored anything.
	_, body := do(t, srv, http.MethodGet, "/books", "", http.StatusOK)
	assertEqual(t, decode[[]Book](t, body), []Book{})
}

func TestUpdateBookRejectsInvalidInput(t *testing.T) {
	srv, _ := newTestServer(t)
	book := createBook(t, srv, `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	path := fmt.Sprintf("/books/%d", book.ID)

	_, body := do(t, srv, http.MethodPut, path, `{"title":"Dune Messiah"}`, http.StatusBadRequest)
	assertEqual(t, decode[errorResponse](t, body).Fields, ValidationError{"author": "is required"})
	do(t, srv, http.MethodPut, path, `{"title":`, http.StatusBadRequest)

	_, body = do(t, srv, http.MethodGet, path, "", http.StatusOK)
	assertEqual(t, decode[Book](t, body), book) // unchanged
}

func TestListBooksFiltersByAuthor(t *testing.T) {
	srv, _ := newTestServer(t)
	earthsea := createBook(t, srv, `{"title":"A Wizard of Earthsea","author":"Ursula K. Le Guin","year":1968}`)
	dune := createBook(t, srv, `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	darkness := createBook(t, srv, `{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969}`)

	tests := []struct {
		name  string
		query string
		want  []Book
	}{
		{"no filter lists every book by ID", "", []Book{earthsea, dune, darkness}},
		{"exact name", "?author=Frank+Herbert", []Book{dune}},
		{"case-insensitive", "?author=ursula%20k.%20le%20guin", []Book{earthsea, darkness}},
		{"surrounding spaces ignored", "?author=%20Frank%20Herbert%20", []Book{dune}},
		{"empty filter is no filter", "?author=", []Book{earthsea, dune, darkness}},
		{"partial names do not match", "?author=Herbert", []Book{}},
		{"unknown author", "?author=Jane+Austen", []Book{}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, body := do(t, srv, http.MethodGet, "/books"+tt.query, "", http.StatusOK)
			assertEqual(t, decode[[]Book](t, body), tt.want)
		})
	}
}

func TestListBooksReturnsEmptyArray(t *testing.T) {
	srv, _ := newTestServer(t)

	_, body := do(t, srv, http.MethodGet, "/books", "", http.StatusOK)
	if got := string(bytes.TrimSpace(body)); got != "[]" {
		t.Errorf("GET /books on an empty collection = %s, want []", got)
	}
}

func TestBookIDErrors(t *testing.T) {
	srv, _ := newTestServer(t)
	valid := `{"title":"Dune","author":"Frank Herbert"}`

	for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
		t.Run(method, func(t *testing.T) {
			reqBody := ""
			if method == http.MethodPut {
				reqBody = valid
			}
			_, body := do(t, srv, method, "/books/abc", reqBody, http.StatusBadRequest)
			assertEqual(t, decode[errorResponse](t, body), errorResponse{Error: "book id must be an integer"})

			_, body = do(t, srv, method, "/books/999", reqBody, http.StatusNotFound)
			assertEqual(t, decode[errorResponse](t, body), errorResponse{Error: "book not found"})
		})
	}
}

func TestUnknownRoutesAndMethods(t *testing.T) {
	srv, _ := newTestServer(t)

	tests := []struct {
		method, path string
		wantStatus   int
		wantAllow    string
	}{
		{http.MethodPatch, "/books/1", http.StatusMethodNotAllowed, "GET, HEAD, PUT, DELETE"},
		{http.MethodDelete, "/books", http.StatusMethodNotAllowed, "GET, HEAD, POST"},
		{http.MethodPost, "/health", http.StatusMethodNotAllowed, "GET, HEAD"},
		{http.MethodGet, "/authors", http.StatusNotFound, ""},
		{http.MethodGet, "/books/1/reviews", http.StatusNotFound, ""},
	}
	for _, tt := range tests {
		t.Run(tt.method+" "+tt.path, func(t *testing.T) {
			resp, body := do(t, srv, tt.method, tt.path, "", tt.wantStatus)
			if got := resp.Header.Get("Allow"); got != tt.wantAllow {
				t.Errorf("Allow = %q, want %q", got, tt.wantAllow)
			}
			if decode[errorResponse](t, body).Error == "" {
				t.Errorf("body %s has no error message", body)
			}
		})
	}
}

func TestConcurrentCreates(t *testing.T) {
	srv, _ := newTestServer(t)
	const n = 50

	ids := make([]int64, n)
	var wg sync.WaitGroup
	for i := range n {
		wg.Go(func() {
			body := fmt.Sprintf(`{"title":"Volume %d","author":"Anonymous"}`, i)
			resp, err := srv.Client().Post(srv.URL+"/books", "application/json", strings.NewReader(body))
			if err != nil {
				t.Error(err)
				return
			}
			defer resp.Body.Close()
			var book Book
			if err := json.NewDecoder(resp.Body).Decode(&book); err != nil || resp.StatusCode != http.StatusCreated {
				t.Errorf("create %d: status %d, decode error %v", i, resp.StatusCode, err)
				return
			}
			ids[i] = book.ID
		})
	}
	wg.Wait()

	seen := make(map[int64]bool, n)
	for _, id := range ids {
		if seen[id] {
			t.Errorf("ID %d was assigned more than once", id)
		}
		seen[id] = true
	}
	_, body := do(t, srv, http.MethodGet, "/books", "", http.StatusOK)
	if got := len(decode[[]Book](t, body)); got != n {
		t.Errorf("listed %d books, want %d", got, n)
	}
}

// TestInternalErrorsAreNotLeaked checks that database failures produce a
// generic 500 rather than exposing driver error text.
func TestInternalErrorsAreNotLeaked(t *testing.T) {
	srv, store := newTestServer(t)
	valid := `{"title":"Dune","author":"Frank Herbert"}`
	store.Close()

	requests := []struct{ method, path, body string }{
		{http.MethodGet, "/books", ""},
		{http.MethodPost, "/books", valid},
		{http.MethodGet, "/books/1", ""},
		{http.MethodPut, "/books/1", valid},
		{http.MethodDelete, "/books/1", ""},
	}
	for _, r := range requests {
		_, body := do(t, srv, r.method, r.path, r.body, http.StatusInternalServerError)
		assertEqual(t, decode[errorResponse](t, body), errorResponse{Error: "internal server error"})
	}
}

func TestPanicsBecomeInternalServerErrors(t *testing.T) {
	s := &server{logger: slog.New(slog.DiscardHandler)}
	h := s.recoverPanics(http.HandlerFunc(func(http.ResponseWriter, *http.Request) { panic("boom") }))

	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/books", nil))

	if rec.Code != http.StatusInternalServerError {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusInternalServerError)
	}
	assertEqual(t, decode[errorResponse](t, rec.Body.Bytes()), errorResponse{Error: "internal server error"})
}

func TestRequestsAreLogged(t *testing.T) {
	var logs bytes.Buffer
	h := NewHandler(newTestStore(t), slog.New(slog.NewTextHandler(&logs, nil)))

	h.ServeHTTP(httptest.NewRecorder(), httptest.NewRequest(http.MethodGet, "/books/42", nil))

	if got := logs.String(); !strings.Contains(got, "method=GET path=/books/42 status=404") {
		t.Errorf("log output %q does not record the request and its status", got)
	}
}
