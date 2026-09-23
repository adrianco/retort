package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"reflect"
	"strings"
	"testing"
	"time"
)

const orwellJSON = `{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949,"isbn":"978-0452284234"}`

// newTestServer returns an API backed by a new database, and that database.
func newTestServer(t *testing.T) (*Server, *Store) {
	t.Helper()
	store := newTestStore(t)
	return NewServer(store, slog.New(slog.DiscardHandler)), store
}

// send makes an in-process request to h. A non-empty body is sent as JSON.
func send(t *testing.T, h http.Handler, method, target, body string) *httptest.ResponseRecorder {
	t.Helper()
	var r io.Reader
	if body != "" {
		r = strings.NewReader(body)
	}
	req := httptest.NewRequest(method, target, r)
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

// postBook creates a book through the API, failing the test if that fails.
func postBook(t *testing.T, h http.Handler, body string) {
	t.Helper()
	if rec := send(t, h, http.MethodPost, "/books", body); rec.Code != http.StatusCreated {
		t.Fatalf("POST /books: status %d, body %s", rec.Code, rec.Body)
	}
}

// assertResponse checks the status code of a JSON response and that its body
// is equivalent to wantBody.
func assertResponse(t *testing.T, rec *httptest.ResponseRecorder, wantStatus int, wantBody string) {
	t.Helper()
	if rec.Code != wantStatus {
		t.Errorf("status = %d, want %d", rec.Code, wantStatus)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
	var got, want any
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("body is not JSON (%v): %s", err, rec.Body)
	}
	if err := json.Unmarshal([]byte(wantBody), &want); err != nil {
		t.Fatalf("bad test expectation %s: %v", wantBody, err)
	}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("body = %s\nwant   %s", strings.TrimSpace(rec.Body.String()), wantBody)
	}
}

func TestHealth(t *testing.T) {
	srv, store := newTestServer(t)
	assertResponse(t, send(t, srv, http.MethodGet, "/health", ""), http.StatusOK, `{"status":"ok"}`)

	store.Close()
	assertResponse(t, send(t, srv, http.MethodGet, "/health", ""), http.StatusServiceUnavailable,
		`{"status":"unavailable","error":"database unavailable"}`)
}

func TestCreateBook(t *testing.T) {
	srv, _ := newTestServer(t)

	// Surrounding whitespace is trimmed.
	rec := send(t, srv, http.MethodPost, "/books",
		`{"title":"  Nineteen Eighty-Four ","author":"George Orwell","year":1949,"isbn":"978-0452284234"}`)
	assertResponse(t, rec, http.StatusCreated,
		`{"id":1,"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949,"isbn":"978-0452284234"}`)
	if got := rec.Header().Get("Location"); got != "/books/1" {
		t.Errorf("Location = %q, want /books/1", got)
	}

	// Year and ISBN are optional, and fields the API doesn't know are ignored.
	rec = send(t, srv, http.MethodPost, "/books", `{"id":99,"title":"Brave New World","author":"Aldous Huxley","genre":"dystopia"}`)
	assertResponse(t, rec, http.StatusCreated,
		`{"id":2,"title":"Brave New World","author":"Aldous Huxley","year":null,"isbn":null}`)
	if got := rec.Header().Get("Location"); got != "/books/2" {
		t.Errorf("Location = %q, want /books/2", got)
	}
}

func TestCreateBookRejectsInvalidInput(t *testing.T) {
	maxYear := time.Now().Year() + 1
	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantBody   string
	}{
		{
			"missing title", `{"author":"George Orwell"}`,
			http.StatusBadRequest, `{"error":"validation failed: title is required","fields":{"title":"is required"}}`,
		},
		{
			"missing author", `{"title":"Nineteen Eighty-Four"}`,
			http.StatusBadRequest, `{"error":"validation failed: author is required","fields":{"author":"is required"}}`,
		},
		{
			"blank title and author", `{"title":" ","author":"","year":1949}`,
			http.StatusBadRequest,
			`{"error":"validation failed: title is required; author is required","fields":{"title":"is required","author":"is required"}}`,
		},
		{
			"future year", fmt.Sprintf(`{"title":"Nineteen Eighty-Four","author":"George Orwell","year":%d}`, maxYear+1),
			http.StatusBadRequest,
			fmt.Sprintf(`{"error":"validation failed: year must be between 1 and %d","fields":{"year":"must be between 1 and %[1]d"}}`, maxYear),
		},
		{
			"title not a string", `{"title":1984,"author":"George Orwell"}`,
			http.StatusBadRequest, `{"error":"title must be a string"}`,
		},
		{
			"year not an integer", `{"title":"Nineteen Eighty-Four","author":"George Orwell","year":"1949"}`,
			http.StatusBadRequest, `{"error":"year must be an integer"}`,
		},
		{
			"fractional year", `{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949.5}`,
			http.StatusBadRequest, `{"error":"year must be an integer"}`,
		},
		{"empty body", ``, http.StatusBadRequest, `{"error":"request body must not be empty"}`},
		{"truncated JSON", `{"title":"Nineteen Eighty-Four",`, http.StatusBadRequest, `{"error":"request body contains malformed JSON"}`},
		{"invalid JSON", `{"title" "Nineteen Eighty-Four"}`, http.StatusBadRequest, `{"error":"request body contains malformed JSON"}`},
		{"not an object", `["Nineteen Eighty-Four","George Orwell"]`, http.StatusBadRequest, `{"error":"request body must be a JSON object"}`},
		{
			"two objects", orwellJSON + orwellJSON,
			http.StatusBadRequest, `{"error":"request body must contain a single JSON object"}`,
		},
		{
			"too large", `{"title":"` + strings.Repeat("x", maxBodyBytes) + `","author":"George Orwell"}`,
			http.StatusRequestEntityTooLarge, `{"error":"request body must not exceed 1048576 bytes"}`,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			srv, _ := newTestServer(t)
			assertResponse(t, send(t, srv, http.MethodPost, "/books", tt.body), tt.wantStatus, tt.wantBody)
			// Nothing was stored.
			assertResponse(t, send(t, srv, http.MethodGet, "/books", ""), http.StatusOK, `[]`)
		})
	}
}

func TestGetBook(t *testing.T) {
	srv, _ := newTestServer(t)
	postBook(t, srv, orwellJSON)

	assertResponse(t, send(t, srv, http.MethodGet, "/books/1", ""), http.StatusOK,
		`{"id":1,"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949,"isbn":"978-0452284234"}`)

	for _, target := range []string{"/books/2", "/books/0", "/books/-1", "/books/1.5", "/books/abc"} {
		t.Run(target, func(t *testing.T) {
			assertResponse(t, send(t, srv, http.MethodGet, target, ""), http.StatusNotFound, `{"error":"book not found"}`)
		})
	}
}

func TestListBooks(t *testing.T) {
	srv, _ := newTestServer(t)
	// An empty collection is an empty array, not null.
	assertResponse(t, send(t, srv, http.MethodGet, "/books", ""), http.StatusOK, `[]`)

	postBook(t, srv, `{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949}`)
	postBook(t, srv, `{"title":"Brave New World","author":"Aldous Huxley","year":1932}`)
	postBook(t, srv, `{"title":"Animal Farm","author":"George Orwell","year":1945}`)
	const (
		book1 = `{"id":1,"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949,"isbn":null}`
		book2 = `{"id":2,"title":"Brave New World","author":"Aldous Huxley","year":1932,"isbn":null}`
		book3 = `{"id":3,"title":"Animal Farm","author":"George Orwell","year":1945,"isbn":null}`
	)

	tests := []struct {
		name, target, want string
	}{
		{"all books in ID order", "/books", "[" + book1 + "," + book2 + "," + book3 + "]"},
		{"filter by author", "/books?author=George%20Orwell", "[" + book1 + "," + book3 + "]"},
		{"filter matches part of the name, ignoring case", "/books?author=orwell", "[" + book1 + "," + book3 + "]"},
		{"filter ignores surrounding spaces", "/books?author=+HUXLEY+", "[" + book2 + "]"},
		{"filter matches nothing", "/books?author=Tolkien", "[]"},
		{"empty filter", "/books?author=", "[" + book1 + "," + book2 + "," + book3 + "]"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assertResponse(t, send(t, srv, http.MethodGet, tt.target, ""), http.StatusOK, tt.want)
		})
	}
}

func TestUpdateBook(t *testing.T) {
	srv, _ := newTestServer(t)
	postBook(t, srv, orwellJSON)

	// PUT replaces the whole book, so the omitted ISBN is cleared.
	want := `{"id":1,"title":"1984","author":"George Orwell","year":1950,"isbn":null}`
	assertResponse(t, send(t, srv, http.MethodPut, "/books/1", `{"title":"1984","author":"George Orwell","year":1950}`),
		http.StatusOK, want)
	assertResponse(t, send(t, srv, http.MethodGet, "/books/1", ""), http.StatusOK, want)

	// Invalid input is rejected and leaves the book as it was.
	assertResponse(t, send(t, srv, http.MethodPut, "/books/1", `{"title":"1984"}`), http.StatusBadRequest,
		`{"error":"validation failed: author is required","fields":{"author":"is required"}}`)
	assertResponse(t, send(t, srv, http.MethodGet, "/books/1", ""), http.StatusOK, want)

	// A book that doesn't exist is reported as such, whatever the body.
	for _, body := range []string{orwellJSON, `{}`, `not JSON`} {
		assertResponse(t, send(t, srv, http.MethodPut, "/books/2", body), http.StatusNotFound, `{"error":"book not found"}`)
	}
}

func TestDeleteBook(t *testing.T) {
	srv, _ := newTestServer(t)
	postBook(t, srv, orwellJSON)

	rec := send(t, srv, http.MethodDelete, "/books/1", "")
	if rec.Code != http.StatusNoContent {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusNoContent)
	}
	if rec.Body.Len() != 0 {
		t.Errorf("body = %q, want none", rec.Body)
	}

	assertResponse(t, send(t, srv, http.MethodGet, "/books/1", ""), http.StatusNotFound, `{"error":"book not found"}`)
	assertResponse(t, send(t, srv, http.MethodDelete, "/books/1", ""), http.StatusNotFound, `{"error":"book not found"}`)
}

func TestUnknownRoutesAndMethods(t *testing.T) {
	srv, _ := newTestServer(t)
	tests := []struct {
		method, target string
		wantStatus     int
		wantAllow      string
		wantBody       string
	}{
		{http.MethodGet, "/authors", http.StatusNotFound, "", `{"error":"not found"}`},
		{http.MethodGet, "/books/", http.StatusNotFound, "", `{"error":"not found"}`},
		{http.MethodGet, "/books/1/reviews", http.StatusNotFound, "", `{"error":"not found"}`},
		{http.MethodPost, "/health", http.StatusMethodNotAllowed, "GET, HEAD", `{"error":"method POST not allowed"}`},
		{http.MethodDelete, "/books", http.StatusMethodNotAllowed, "GET, HEAD, POST", `{"error":"method DELETE not allowed"}`},
		{http.MethodPatch, "/books/1", http.StatusMethodNotAllowed, "GET, HEAD, PUT, DELETE", `{"error":"method PATCH not allowed"}`},
	}
	for _, tt := range tests {
		t.Run(tt.method+" "+tt.target, func(t *testing.T) {
			rec := send(t, srv, tt.method, tt.target, "")
			assertResponse(t, rec, tt.wantStatus, tt.wantBody)
			if got := rec.Header().Get("Allow"); got != tt.wantAllow {
				t.Errorf("Allow = %q, want %q", got, tt.wantAllow)
			}
		})
	}
}

func TestDatabaseErrorsAreLoggedNotExposed(t *testing.T) {
	var logs strings.Builder
	store := newTestStore(t)
	srv := NewServer(store, slog.New(slog.NewTextHandler(&logs, nil)))
	store.Close() // every query now fails

	tests := []struct{ method, target, body string }{
		{http.MethodGet, "/books", ""},
		{http.MethodPost, "/books", orwellJSON},
		{http.MethodGet, "/books/1", ""},
		{http.MethodPut, "/books/1", orwellJSON},
		{http.MethodDelete, "/books/1", ""},
	}
	for _, tt := range tests {
		t.Run(tt.method+" "+tt.target, func(t *testing.T) {
			logs.Reset()
			assertResponse(t, send(t, srv, tt.method, tt.target, tt.body),
				http.StatusInternalServerError, `{"error":"internal server error"}`)
			if !strings.Contains(logs.String(), "database is closed") {
				t.Errorf("the cause was not logged; logs:\n%s", logs.String())
			}
		})
	}
}

func TestPanicIsInternalServerError(t *testing.T) {
	var logs strings.Builder
	srv := NewServer(nil, slog.New(slog.NewTextHandler(&logs, nil)))
	h := srv.recoverPanics(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {
		panic("something broke")
	}))

	assertResponse(t, send(t, h, http.MethodGet, "/books", ""), http.StatusInternalServerError,
		`{"error":"internal server error"}`)
	if !strings.Contains(logs.String(), "something broke") {
		t.Errorf("the panic was not logged; logs:\n%s", logs.String())
	}
}
