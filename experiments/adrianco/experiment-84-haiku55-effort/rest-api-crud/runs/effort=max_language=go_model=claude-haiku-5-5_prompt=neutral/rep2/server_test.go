package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"maps"
	"net/http"
	"net/http/httptest"
	"reflect"
	"slices"
	"strings"
	"testing"
)

// discardLogger returns a logger that drops everything, to keep test output quiet.
func discardLogger() *slog.Logger {
	return slog.New(slog.NewTextHandler(io.Discard, nil))
}

// newTestAPI returns the API handler and the store behind it, backed by a fresh database.
func newTestAPI(t *testing.T) (http.Handler, *Store) {
	t.Helper()
	store := newTestStore(t)
	return NewServer(store, discardLogger()).Handler(), store
}

// send issues a request against h and returns the recorded response.
func send(t *testing.T, h http.Handler, method, target, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, target, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

// decodeBody decodes a JSON response body into v and checks the content type.
func decodeBody(t *testing.T, rec *httptest.ResponseRecorder, v any) {
	t.Helper()
	if ct := rec.Header().Get("Content-Type"); ct != "application/json; charset=utf-8" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
	if err := json.Unmarshal(rec.Body.Bytes(), v); err != nil {
		t.Fatalf("decode body %q: %v", rec.Body.String(), err)
	}
}

// wantStatus fails the test unless rec has the given status code.
func wantStatus(t *testing.T, rec *httptest.ResponseRecorder, status int) {
	t.Helper()
	if rec.Code != status {
		t.Fatalf("status = %d, want %d (body: %s)", rec.Code, status, rec.Body.String())
	}
}

// wantError fails the test unless rec is an error response with the given status and message.
func wantError(t *testing.T, rec *httptest.ResponseRecorder, status int, msg string) {
	t.Helper()
	wantStatus(t, rec, status)
	var body errorResponse
	decodeBody(t, rec, &body)
	if body.Error != msg {
		t.Errorf("error = %q, want %q", body.Error, msg)
	}
}

func bookPath(id int64) string {
	return fmt.Sprintf("/books/%d", id)
}

func TestCreateBook(t *testing.T) {
	h, _ := newTestAPI(t)

	rec := send(t, h, http.MethodPost, "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}`)
	wantStatus(t, rec, http.StatusCreated)
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}
	var got Book
	decodeBody(t, rec, &got)
	assertBook(t, got, Book{
		ID:     1,
		Title:  "Dune",
		Author: "Frank Herbert",
		Year:   intPtr(1965),
		ISBN:   strPtr("978-0441172719"),
	})

	// The server assigns IDs, so an ID sent by the client is ignored.
	rec = send(t, h, http.MethodPost, "/books", `{"id":99,"title":"Neuromancer","author":"William Gibson"}`)
	wantStatus(t, rec, http.StatusCreated)
	var second Book
	decodeBody(t, rec, &second)
	if second.ID != 2 {
		t.Errorf("ID = %d, want 2", second.ID)
	}
}

func TestCreateBookValidation(t *testing.T) {
	futureYear := latestPublicationYear() + 1

	tests := []struct {
		name       string
		body       string
		wantFields []string
	}{
		{name: "missing title", body: `{"author":"Frank Herbert"}`, wantFields: []string{"title"}},
		{name: "missing author", body: `{"title":"Dune"}`, wantFields: []string{"author"}},
		{name: "blank title", body: `{"title":"   ","author":"Frank Herbert"}`, wantFields: []string{"title"}},
		{name: "missing title and author", body: `{"year":1965}`, wantFields: []string{"title", "author"}},
		{name: "year zero", body: `{"title":"Dune","author":"Frank Herbert","year":0}`, wantFields: []string{"year"}},
		{
			name:       "year too far in the future",
			body:       fmt.Sprintf(`{"title":"Dune","author":"Frank Herbert","year":%d}`, futureYear),
			wantFields: []string{"year"},
		},
		{name: "malformed ISBN", body: `{"title":"Dune","author":"Frank Herbert","isbn":"123"}`, wantFields: []string{"isbn"}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h, _ := newTestAPI(t)

			rec := send(t, h, http.MethodPost, "/books", tt.body)
			wantStatus(t, rec, http.StatusBadRequest)
			var body errorResponse
			decodeBody(t, rec, &body)
			if body.Error != "validation failed" {
				t.Errorf("error = %q, want %q", body.Error, "validation failed")
			}
			wantFields := slices.Clone(tt.wantFields)
			slices.Sort(wantFields)
			if got := slices.Sorted(maps.Keys(body.Fields)); !slices.Equal(got, wantFields) {
				t.Errorf("invalid fields = %v, want %v", got, wantFields)
			}

			// A rejected book must not be stored.
			var books []Book
			decodeBody(t, send(t, h, http.MethodGet, "/books", ""), &books)
			if len(books) != 0 {
				t.Errorf("rejected book was stored: %s", toJSON(books))
			}
		})
	}
}

func TestCreateBookRejectsMalformedBodies(t *testing.T) {
	tests := []struct {
		name    string
		body    string
		wantErr string // the error message must start with this
	}{
		{name: "empty body", body: "", wantErr: "request body is required"},
		{name: "truncated JSON", body: `{"title":`, wantErr: "malformed JSON"},
		{name: "JSON array", body: `["Dune","Frank Herbert"]`, wantErr: "request body must be a JSON object"},
		{
			name:    "two JSON objects",
			body:    `{"title":"Dune","author":"Frank Herbert"}{}`,
			wantErr: "request body must contain a single JSON object",
		},
		{
			name:    "garbage after the JSON object",
			body:    `{"title":"Dune","author":"Frank Herbert"} xyz`,
			wantErr: "malformed JSON",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h, _ := newTestAPI(t)

			rec := send(t, h, http.MethodPost, "/books", tt.body)
			wantStatus(t, rec, http.StatusBadRequest)
			var body errorResponse
			decodeBody(t, rec, &body)
			if !strings.HasPrefix(body.Error, tt.wantErr) {
				t.Errorf("error = %q, want it to start with %q", body.Error, tt.wantErr)
			}
		})
	}
}

func TestCreateBookWrongFieldType(t *testing.T) {
	tests := []struct {
		name  string
		body  string
		field string
		msg   string
	}{
		{name: "year as a string", body: `{"title":"Dune","author":"A","year":"1965"}`, field: "year", msg: "must be an integer"},
		{name: "year with a fraction", body: `{"title":"Dune","author":"A","year":1965.5}`, field: "year", msg: "must be an integer"},
		{name: "title as a number", body: `{"title":42,"author":"A"}`, field: "title", msg: "must be a string"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h, _ := newTestAPI(t)

			rec := send(t, h, http.MethodPost, "/books", tt.body)
			wantStatus(t, rec, http.StatusBadRequest)
			var body errorResponse
			decodeBody(t, rec, &body)
			if want := (fieldErrors{tt.field: tt.msg}); !reflect.DeepEqual(body.Fields, want) {
				t.Errorf("fields = %s, want %s", toJSON(body.Fields), toJSON(want))
			}
		})
	}
}

func TestCreateBookBodyTooLarge(t *testing.T) {
	h, _ := newTestAPI(t)

	body := `{"title":"` + strings.Repeat("a", maxBodyBytes) + `","author":"A"}`
	rec := send(t, h, http.MethodPost, "/books", body)
	wantError(t, rec, http.StatusRequestEntityTooLarge,
		fmt.Sprintf("request body must be at most %d bytes", maxBodyBytes))
}

func TestGetBook(t *testing.T) {
	h, store := newTestAPI(t)
	created := mustCreate(t, store, Book{Title: "Dune", Author: "Frank Herbert", Year: intPtr(1965)})

	rec := send(t, h, http.MethodGet, bookPath(created.ID), "")
	wantStatus(t, rec, http.StatusOK)
	var got Book
	decodeBody(t, rec, &got)
	assertBook(t, got, created)

	wantError(t, send(t, h, http.MethodGet, "/books/9999", ""), http.StatusNotFound, "book not found")
	wantError(t, send(t, h, http.MethodGet, "/books/abc", ""), http.StatusBadRequest, "book id must be an integer")
}

func TestListBooks(t *testing.T) {
	h, store := newTestAPI(t)

	// An empty collection must be an empty JSON array, not null.
	rec := send(t, h, http.MethodGet, "/books", "")
	wantStatus(t, rec, http.StatusOK)
	if body := strings.TrimSpace(rec.Body.String()); body != "[]" {
		t.Errorf("empty list body = %q, want []", body)
	}

	dune := mustCreate(t, store, Book{Title: "Dune", Author: "Frank Herbert"})
	gibson := mustCreate(t, store, Book{Title: "Neuromancer", Author: "William Gibson"})
	children := mustCreate(t, store, Book{Title: "Children of Dune", Author: "Frank Herbert"})

	tests := []struct {
		target string
		want   []Book
	}{
		{target: "/books", want: []Book{dune, gibson, children}},
		{target: "/books?author=Frank%20Herbert", want: []Book{dune, children}},
		{target: "/books?author=gibson", want: []Book{gibson}},
		{target: "/books?author=%20%20", want: []Book{dune, gibson, children}}, // a blank filter is ignored
		{target: "/books?author=Asimov", want: []Book{}},
	}

	for _, tt := range tests {
		t.Run(tt.target, func(t *testing.T) {
			rec := send(t, h, http.MethodGet, tt.target, "")
			wantStatus(t, rec, http.StatusOK)
			var got []Book
			decodeBody(t, rec, &got)
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("books = %s, want %s", toJSON(got), toJSON(tt.want))
			}
		})
	}
}

func TestUpdateBook(t *testing.T) {
	original := Book{Title: "Dune", Author: "Frank Herbert", Year: intPtr(1965), ISBN: strPtr("978-0441172719")}

	t.Run("replaces every field and clears omitted optional fields", func(t *testing.T) {
		h, store := newTestAPI(t)
		created := mustCreate(t, store, original)

		rec := send(t, h, http.MethodPut, bookPath(created.ID),
			`{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
		wantStatus(t, rec, http.StatusOK)
		want := Book{ID: created.ID, Title: "Dune Messiah", Author: "Frank Herbert", Year: intPtr(1969)}
		var got Book
		decodeBody(t, rec, &got)
		assertBook(t, got, want)

		var stored Book
		decodeBody(t, send(t, h, http.MethodGet, bookPath(created.ID), ""), &stored)
		assertBook(t, stored, want)
	})

	t.Run("missing book", func(t *testing.T) {
		h, _ := newTestAPI(t)
		wantError(t, send(t, h, http.MethodPut, "/books/9999", `{"title":"X","author":"Y"}`),
			http.StatusNotFound, "book not found")
	})

	t.Run("invalid body leaves the book unchanged", func(t *testing.T) {
		h, store := newTestAPI(t)
		created := mustCreate(t, store, original)

		rec := send(t, h, http.MethodPut, bookPath(created.ID), `{"title":"Changed"}`)
		wantError(t, rec, http.StatusBadRequest, "validation failed")

		var stored Book
		decodeBody(t, send(t, h, http.MethodGet, bookPath(created.ID), ""), &stored)
		assertBook(t, stored, created)
	})

	t.Run("non-integer id", func(t *testing.T) {
		h, _ := newTestAPI(t)
		wantError(t, send(t, h, http.MethodPut, "/books/abc", `{"title":"X","author":"Y"}`),
			http.StatusBadRequest, "book id must be an integer")
	})
}

func TestDeleteBook(t *testing.T) {
	h, store := newTestAPI(t)
	created := mustCreate(t, store, Book{Title: "Dune", Author: "Frank Herbert"})
	path := bookPath(created.ID)

	rec := send(t, h, http.MethodDelete, path, "")
	wantStatus(t, rec, http.StatusNoContent)
	if rec.Body.Len() != 0 {
		t.Errorf("204 response has a body: %q", rec.Body.String())
	}

	wantError(t, send(t, h, http.MethodGet, path, ""), http.StatusNotFound, "book not found")
	wantError(t, send(t, h, http.MethodDelete, path, ""), http.StatusNotFound, "book not found")
}

func TestHealth(t *testing.T) {
	h, store := newTestAPI(t)

	rec := send(t, h, http.MethodGet, "/health", "")
	wantStatus(t, rec, http.StatusOK)
	var body map[string]string
	decodeBody(t, rec, &body)
	if body["status"] != "ok" {
		t.Errorf("health status = %q, want ok", body["status"])
	}

	// With the database closed, the health check must report failure.
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}
	rec = send(t, h, http.MethodGet, "/health", "")
	wantStatus(t, rec, http.StatusServiceUnavailable)
	decodeBody(t, rec, &body)
	if body["status"] != "unavailable" {
		t.Errorf("health status = %q, want unavailable", body["status"])
	}
}

func TestUnknownRoutesAndMethods(t *testing.T) {
	tests := []struct {
		name   string
		method string
		target string
		status int
		msg    string
		allow  string // expected Allow header; only set for 405 responses
	}{
		{name: "unknown path", method: http.MethodGet, target: "/nope",
			status: http.StatusNotFound, msg: "not found"},
		{name: "unknown nested path", method: http.MethodGet, target: "/books/1/extra",
			status: http.StatusNotFound, msg: "not found"},
		{name: "trailing slash on collection", method: http.MethodGet, target: "/books/",
			status: http.StatusNotFound, msg: "not found"},
		{name: "unsupported method on /books", method: http.MethodPatch, target: "/books",
			status: http.StatusMethodNotAllowed, msg: "method not allowed", allow: "GET, HEAD, POST"},
		{name: "unsupported method on /books/{id}", method: http.MethodPatch, target: "/books/1",
			status: http.StatusMethodNotAllowed, msg: "method not allowed", allow: "GET, HEAD, PUT, DELETE"},
		{name: "unsupported method on /health", method: http.MethodPost, target: "/health",
			status: http.StatusMethodNotAllowed, msg: "method not allowed", allow: "GET, HEAD"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h, _ := newTestAPI(t)

			rec := send(t, h, tt.method, tt.target, "")
			wantError(t, rec, tt.status, tt.msg)
			if allow := rec.Header().Get("Allow"); allow != tt.allow {
				t.Errorf("Allow = %q, want %q", allow, tt.allow)
			}
		})
	}
}

// TestHTTPLifecycle runs the whole API over a real listening server.
func TestHTTPLifecycle(t *testing.T) {
	h, _ := newTestAPI(t)
	srv := httptest.NewServer(h)
	t.Cleanup(srv.Close)

	call := func(t *testing.T, method, path, body string) (int, []byte) {
		t.Helper()
		req, err := http.NewRequest(method, srv.URL+path, strings.NewReader(body))
		if err != nil {
			t.Fatalf("NewRequest: %v", err)
		}
		req.Header.Set("Content-Type", "application/json")
		resp, err := srv.Client().Do(req)
		if err != nil {
			t.Fatalf("%s %s: %v", method, path, err)
		}
		defer resp.Body.Close()
		data, err := io.ReadAll(resp.Body)
		if err != nil {
			t.Fatalf("read %s %s body: %v", method, path, err)
		}
		return resp.StatusCode, data
	}

	status, data := call(t, http.MethodPost, "/books",
		`{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969}`)
	if status != http.StatusCreated {
		t.Fatalf("POST /books status = %d, body %s", status, data)
	}
	var created Book
	if err := json.Unmarshal(data, &created); err != nil {
		t.Fatalf("decode created book: %v", err)
	}
	path := bookPath(created.ID)

	if status, data = call(t, http.MethodGet, "/books?author=le%20guin", ""); status != http.StatusOK {
		t.Fatalf("GET filtered list status = %d, body %s", status, data)
	} else if !strings.Contains(string(data), `"title":"The Left Hand of Darkness"`) {
		t.Errorf("filtered list does not contain the new book: %s", data)
	}

	if status, data = call(t, http.MethodPut, path,
		`{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969,"isbn":"0441478123"}`); status != http.StatusOK {
		t.Fatalf("PUT status = %d, body %s", status, data)
	}
	if status, data = call(t, http.MethodGet, path, ""); status != http.StatusOK {
		t.Fatalf("GET after PUT status = %d, body %s", status, data)
	} else if !strings.Contains(string(data), `"isbn":"0441478123"`) {
		t.Errorf("GET after PUT does not show the update: %s", data)
	}

	if status, data = call(t, http.MethodDelete, path, ""); status != http.StatusNoContent {
		t.Fatalf("DELETE status = %d, body %s", status, data)
	}
	if status, data = call(t, http.MethodGet, path, ""); status != http.StatusNotFound {
		t.Fatalf("GET after DELETE status = %d, body %s", status, data)
	}
	if status, data = call(t, http.MethodGet, "/health", ""); status != http.StatusOK {
		t.Fatalf("GET /health status = %d, body %s", status, data)
	}
}
