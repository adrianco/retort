package main

import (
	"bytes"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	return NewServer(newTestStore(t), nil) // a nil logger falls back to discarding output
}

func discardLogger() *slog.Logger {
	return slog.New(slog.NewTextHandler(io.Discard, nil))
}

// do sends a request to the handler. A string body is sent verbatim (for
// malformed-JSON cases); anything else is marshalled to JSON first.
func do(t *testing.T, h http.Handler, method, target string, body any) *httptest.ResponseRecorder {
	t.Helper()

	var reader io.Reader
	switch b := body.(type) {
	case nil:
	case string:
		reader = strings.NewReader(b)
	default:
		raw, err := json.Marshal(b)
		if err != nil {
			t.Fatalf("marshalling request body: %v", err)
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

func checkStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d (body: %s)", rec.Code, want, rec.Body.String())
	}
	if want == http.StatusNoContent {
		if rec.Body.Len() != 0 {
			t.Errorf("204 response should have an empty body, got %q", rec.Body.String())
		}
		return
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json; charset=utf-8" {
		t.Errorf("Content-Type = %q, want application/json; charset=utf-8", ct)
	}
}

func decodeInto[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decoding response %q: %v", rec.Body.String(), err)
	}
	return v
}

func createBook(t *testing.T, h http.Handler, in map[string]any) Book {
	t.Helper()
	rec := do(t, h, http.MethodPost, "/books", in)
	checkStatus(t, rec, http.StatusCreated)
	return decodeInto[Book](t, rec)
}

func TestHealthEndpoint(t *testing.T) {
	rec := do(t, newTestServer(t), http.MethodGet, "/health", nil)

	checkStatus(t, rec, http.StatusOK)
	got := decodeInto[healthResponse](t, rec)
	if got.Status != "ok" || got.Database != "up" {
		t.Errorf("health = %+v, want {ok up}", got)
	}
}

// TestBookLifecycle drives the full CRUD cycle through a real HTTP server and
// a real client, so routing, status codes and headers are all exercised the
// way a caller would see them.
func TestBookLifecycle(t *testing.T) {
	ts := httptest.NewServer(newTestServer(t))
	defer ts.Close()

	// Create
	res, err := ts.Client().Post(ts.URL+"/books", "application/json", strings.NewReader(
		`{"title":"The Hitchhiker's Guide to the Galaxy","author":"Douglas Adams","year":1979,"isbn":"0-345-39180-2"}`))
	if err != nil {
		t.Fatalf("POST /books: %v", err)
	}
	defer res.Body.Close()
	if res.StatusCode != http.StatusCreated {
		body, _ := io.ReadAll(res.Body)
		t.Fatalf("POST /books status = %d, want 201 (body: %s)", res.StatusCode, body)
	}

	var created Book
	if err := json.NewDecoder(res.Body).Decode(&created); err != nil {
		t.Fatalf("decoding created book: %v", err)
	}
	if created.ID <= 0 {
		t.Fatalf("created book has id %d, want a positive id", created.ID)
	}
	if want := "/books/" + strconv.FormatInt(created.ID, 10); res.Header.Get("Location") != want {
		t.Errorf("Location = %q, want %q", res.Header.Get("Location"), want)
	}
	if created.ISBN == nil || *created.ISBN != "0345391802" {
		t.Errorf("ISBN = %s, want the normalized 0345391802", showPtr(created.ISBN))
	}

	bookURL := ts.URL + "/books/" + strconv.FormatInt(created.ID, 10)

	// Read
	res, err = ts.Client().Get(bookURL)
	if err != nil {
		t.Fatalf("GET %s: %v", bookURL, err)
	}
	var fetched Book
	if err := json.NewDecoder(res.Body).Decode(&fetched); err != nil {
		t.Fatalf("decoding fetched book: %v", err)
	}
	res.Body.Close()
	if res.StatusCode != http.StatusOK {
		t.Fatalf("GET book status = %d, want 200", res.StatusCode)
	}
	if fetched.Title != created.Title || fetched.ID != created.ID {
		t.Errorf("fetched %+v, want the book that was just created", fetched)
	}

	// Update
	req, err := http.NewRequest(http.MethodPut, bookURL, strings.NewReader(
		`{"title":"The Hitchhiker's Guide to the Galaxy","author":"Douglas Adams","year":1980,"isbn":"0345391802"}`))
	if err != nil {
		t.Fatalf("building PUT: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")
	res, err = ts.Client().Do(req)
	if err != nil {
		t.Fatalf("PUT %s: %v", bookURL, err)
	}
	var updated Book
	if err := json.NewDecoder(res.Body).Decode(&updated); err != nil {
		t.Fatalf("decoding updated book: %v", err)
	}
	res.Body.Close()
	if res.StatusCode != http.StatusOK {
		t.Fatalf("PUT status = %d, want 200", res.StatusCode)
	}
	if updated.Year == nil || *updated.Year != 1980 {
		t.Errorf("Year = %s, want 1980", showPtr(updated.Year))
	}

	// Delete
	req, err = http.NewRequest(http.MethodDelete, bookURL, nil)
	if err != nil {
		t.Fatalf("building DELETE: %v", err)
	}
	res, err = ts.Client().Do(req)
	if err != nil {
		t.Fatalf("DELETE %s: %v", bookURL, err)
	}
	res.Body.Close()
	if res.StatusCode != http.StatusNoContent {
		t.Fatalf("DELETE status = %d, want 204", res.StatusCode)
	}

	// Gone
	res, err = ts.Client().Get(bookURL)
	if err != nil {
		t.Fatalf("GET after delete: %v", err)
	}
	res.Body.Close()
	if res.StatusCode != http.StatusNotFound {
		t.Errorf("GET after delete status = %d, want 404", res.StatusCode)
	}
}

func TestCreateBookValidation(t *testing.T) {
	tests := []struct {
		name        string
		body        any
		wantStatus  int
		wantDetails []string
	}{
		{
			name:        "title missing",
			body:        map[string]any{"author": "Douglas Adams"},
			wantStatus:  http.StatusBadRequest,
			wantDetails: []string{"title is required"},
		},
		{
			name:        "author missing",
			body:        map[string]any{"title": "Mostly Harmless"},
			wantStatus:  http.StatusBadRequest,
			wantDetails: []string{"author is required"},
		},
		{
			name:        "title and author blank",
			body:        map[string]any{"title": "  ", "author": ""},
			wantStatus:  http.StatusBadRequest,
			wantDetails: []string{"title is required", "author is required"},
		},
		{
			name:        "empty object",
			body:        map[string]any{},
			wantStatus:  http.StatusBadRequest,
			wantDetails: []string{"title is required", "author is required"},
		},
		{
			name:       "year out of range",
			body:       map[string]any{"title": "Time Traveller", "author": "H. G. Wells", "year": 0},
			wantStatus: http.StatusBadRequest,
		},
		{
			name:       "isbn malformed",
			body:       map[string]any{"title": "Dune", "author": "Frank Herbert", "isbn": "not-an-isbn"},
			wantStatus: http.StatusBadRequest,
		},
		{
			name:       "year of the wrong JSON type",
			body:       `{"title":"Dune","author":"Frank Herbert","year":"nineteen sixty five"}`,
			wantStatus: http.StatusBadRequest,
		},
		{
			name:       "malformed JSON",
			body:       `{"title":"Dune",`,
			wantStatus: http.StatusBadRequest,
		},
		{
			name:       "two JSON objects in one body",
			body:       `{"title":"Dune","author":"Frank Herbert"}{"title":"Extra","author":"Sneaky"}`,
			wantStatus: http.StatusBadRequest,
		},
		{
			name:       "empty body",
			body:       ``,
			wantStatus: http.StatusBadRequest,
		},
	}

	srv := newTestServer(t)
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, srv, http.MethodPost, "/books", tt.body)
			checkStatus(t, rec, tt.wantStatus)

			got := decodeInto[errorResponse](t, rec)
			if got.Error == "" {
				t.Errorf("error response has no message: %s", rec.Body.String())
			}
			if tt.wantDetails != nil {
				if strings.Join(got.Details, " | ") != strings.Join(tt.wantDetails, " | ") {
					t.Errorf("details = %v, want %v", got.Details, tt.wantDetails)
				}
			}
		})
	}

	// Nothing above should have been persisted.
	rec := do(t, srv, http.MethodGet, "/books", nil)
	checkStatus(t, rec, http.StatusOK)
	if books := decodeInto[[]Book](t, rec); len(books) != 0 {
		t.Errorf("rejected requests created %d books", len(books))
	}
}

func TestCreateBookOmittingOptionalFields(t *testing.T) {
	srv := newTestServer(t)

	book := createBook(t, srv, map[string]any{"title": "Minimal", "author": "Someone"})

	if book.Year != nil {
		t.Errorf("Year = %d, want null", *book.Year)
	}
	if book.ISBN != nil {
		t.Errorf("ISBN = %q, want null", *book.ISBN)
	}

	// Optional fields must be present as null rather than dropped, so clients
	// can round-trip a GET response straight back into a PUT.
	var raw map[string]json.RawMessage
	rec := do(t, srv, http.MethodGet, "/books/"+strconv.FormatInt(book.ID, 10), nil)
	checkStatus(t, rec, http.StatusOK)
	if err := json.Unmarshal(rec.Body.Bytes(), &raw); err != nil {
		t.Fatalf("decoding book object: %v", err)
	}
	for _, field := range []string{"id", "title", "author", "year", "isbn", "created_at", "updated_at"} {
		if _, ok := raw[field]; !ok {
			t.Errorf("response is missing the %q field: %s", field, rec.Body.String())
		}
	}
}

func TestListBooks(t *testing.T) {
	srv := newTestServer(t)

	t.Run("empty collection is an empty array", func(t *testing.T) {
		rec := do(t, srv, http.MethodGet, "/books", nil)
		checkStatus(t, rec, http.StatusOK)
		if body := strings.TrimSpace(rec.Body.String()); body != "[]" {
			t.Errorf("body = %s, want []", body)
		}
	})

	createBook(t, srv, map[string]any{"title": "Dune", "author": "Frank Herbert", "year": 1965})
	createBook(t, srv, map[string]any{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969})
	createBook(t, srv, map[string]any{"title": "Neuromancer", "author": "William Gibson", "year": 1984})

	t.Run("all books", func(t *testing.T) {
		rec := do(t, srv, http.MethodGet, "/books", nil)
		checkStatus(t, rec, http.StatusOK)
		if books := decodeInto[[]Book](t, rec); len(books) != 3 {
			t.Errorf("got %d books, want 3", len(books))
		}
	})

	t.Run("author filter", func(t *testing.T) {
		rec := do(t, srv, http.MethodGet, "/books?author=Frank+Herbert", nil)
		checkStatus(t, rec, http.StatusOK)
		books := decodeInto[[]Book](t, rec)
		if len(books) != 2 {
			t.Fatalf("got %d books, want 2", len(books))
		}
		for _, b := range books {
			if b.Author != "Frank Herbert" {
				t.Errorf("filter returned a book by %q", b.Author)
			}
		}
	})

	t.Run("author filter is case insensitive", func(t *testing.T) {
		rec := do(t, srv, http.MethodGet, "/books?author=william+gibson", nil)
		checkStatus(t, rec, http.StatusOK)
		if books := decodeInto[[]Book](t, rec); len(books) != 1 {
			t.Errorf("got %d books, want 1", len(books))
		}
	})

	t.Run("author filter with no matches", func(t *testing.T) {
		rec := do(t, srv, http.MethodGet, "/books?author=Nobody", nil)
		checkStatus(t, rec, http.StatusOK)
		if body := strings.TrimSpace(rec.Body.String()); body != "[]" {
			t.Errorf("body = %s, want []", body)
		}
	})

	t.Run("blank author filter is ignored", func(t *testing.T) {
		rec := do(t, srv, http.MethodGet, "/books?author=", nil)
		checkStatus(t, rec, http.StatusOK)
		if books := decodeInto[[]Book](t, rec); len(books) != 3 {
			t.Errorf("got %d books, want all 3", len(books))
		}
	})
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)
	book := createBook(t, srv, map[string]any{
		"title": "Neuromancer", "author": "Wiliam Gibsn", "year": 1984, "isbn": "0441569560",
	})
	path := "/books/" + strconv.FormatInt(book.ID, 10)

	t.Run("replaces the record", func(t *testing.T) {
		rec := do(t, srv, http.MethodPut, path, map[string]any{
			"title": "Neuromancer", "author": "William Gibson", "year": 1984,
		})
		checkStatus(t, rec, http.StatusOK)

		updated := decodeInto[Book](t, rec)
		if updated.ID != book.ID {
			t.Errorf("ID = %d, want %d", updated.ID, book.ID)
		}
		if updated.Author != "William Gibson" {
			t.Errorf("Author = %q, want %q", updated.Author, "William Gibson")
		}
		if updated.ISBN != nil {
			t.Errorf("ISBN = %q, want null: PUT replaces the whole record", *updated.ISBN)
		}
		if !updated.UpdatedAt.After(book.UpdatedAt) {
			t.Errorf("UpdatedAt = %v, want later than %v", updated.UpdatedAt, book.UpdatedAt)
		}
		if !updated.CreatedAt.Equal(book.CreatedAt) {
			t.Errorf("CreatedAt = %v, want it unchanged at %v", updated.CreatedAt, book.CreatedAt)
		}
	})

	t.Run("validates the payload", func(t *testing.T) {
		rec := do(t, srv, http.MethodPut, path, map[string]any{"author": "William Gibson"})
		checkStatus(t, rec, http.StatusBadRequest)
		if details := decodeInto[errorResponse](t, rec).Details; len(details) != 1 || details[0] != "title is required" {
			t.Errorf("details = %v, want [title is required]", details)
		}
	})

	t.Run("unknown id", func(t *testing.T) {
		rec := do(t, srv, http.MethodPut, "/books/987654", map[string]any{"title": "Ghost", "author": "Nobody"})
		checkStatus(t, rec, http.StatusNotFound)
	})
}

func TestDuplicateISBNIsAConflict(t *testing.T) {
	srv := newTestServer(t)
	createBook(t, srv, map[string]any{"title": "Dune", "author": "Frank Herbert", "isbn": "9780441013593"})

	t.Run("on create", func(t *testing.T) {
		rec := do(t, srv, http.MethodPost, "/books", map[string]any{
			"title": "Dune (reprint)", "author": "Frank Herbert", "isbn": "978-0-441-01359-3",
		})
		checkStatus(t, rec, http.StatusConflict)
	})

	t.Run("on update", func(t *testing.T) {
		other := createBook(t, srv, map[string]any{"title": "Neuromancer", "author": "William Gibson"})
		rec := do(t, srv, http.MethodPut, "/books/"+strconv.FormatInt(other.ID, 10), map[string]any{
			"title": "Neuromancer", "author": "William Gibson", "isbn": "9780441013593",
		})
		checkStatus(t, rec, http.StatusConflict)
	})
}

func TestMissingAndMalformedIDs(t *testing.T) {
	srv := newTestServer(t)

	tests := []struct {
		name       string
		method     string
		target     string
		body       any
		wantStatus int
	}{
		{"get unknown id", http.MethodGet, "/books/999", nil, http.StatusNotFound},
		{"delete unknown id", http.MethodDelete, "/books/999", nil, http.StatusNotFound},
		{"get non-numeric id", http.MethodGet, "/books/abc", nil, http.StatusBadRequest},
		{"get zero id", http.MethodGet, "/books/0", nil, http.StatusBadRequest},
		{"get negative id", http.MethodGet, "/books/-1", nil, http.StatusBadRequest},
		{"delete non-numeric id", http.MethodDelete, "/books/abc", nil, http.StatusBadRequest},
		{"put non-numeric id", http.MethodPut, "/books/abc", map[string]any{"title": "T", "author": "A"}, http.StatusBadRequest},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, srv, tt.method, tt.target, tt.body)
			checkStatus(t, rec, tt.wantStatus)
			if decodeInto[errorResponse](t, rec).Error == "" {
				t.Errorf("error response has no message: %s", rec.Body.String())
			}
		})
	}
}

func TestRoutingErrors(t *testing.T) {
	srv := newTestServer(t)

	t.Run("wrong method on a collection", func(t *testing.T) {
		rec := do(t, srv, http.MethodDelete, "/books", nil)
		checkStatus(t, rec, http.StatusMethodNotAllowed)
		if allow := rec.Header().Get("Allow"); allow != "GET, POST" {
			t.Errorf("Allow = %q, want %q", allow, "GET, POST")
		}
	})

	t.Run("wrong method on an item", func(t *testing.T) {
		rec := do(t, srv, http.MethodPost, "/books/1", map[string]any{"title": "T", "author": "A"})
		checkStatus(t, rec, http.StatusMethodNotAllowed)
		if allow := rec.Header().Get("Allow"); allow != "GET, PUT, DELETE" {
			t.Errorf("Allow = %q, want %q", allow, "GET, PUT, DELETE")
		}
	})

	t.Run("wrong method on health", func(t *testing.T) {
		rec := do(t, srv, http.MethodPost, "/health", map[string]any{})
		checkStatus(t, rec, http.StatusMethodNotAllowed)
	})

	t.Run("unknown path", func(t *testing.T) {
		rec := do(t, srv, http.MethodGet, "/nope", nil)
		checkStatus(t, rec, http.StatusNotFound)
	})

	t.Run("too many path segments", func(t *testing.T) {
		rec := do(t, srv, http.MethodGet, "/books/1/pages", nil)
		checkStatus(t, rec, http.StatusNotFound)
	})
}

func TestRequestBodyGuards(t *testing.T) {
	srv := newTestServer(t)

	t.Run("wrong content type", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader(`{"title":"T","author":"A"}`))
		req.Header.Set("Content-Type", "text/plain")
		rec := httptest.NewRecorder()
		srv.ServeHTTP(rec, req)
		checkStatus(t, rec, http.StatusUnsupportedMediaType)
	})

	t.Run("content type with a charset parameter is accepted", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader(`{"title":"T","author":"A"}`))
		req.Header.Set("Content-Type", "application/json; charset=utf-8")
		rec := httptest.NewRecorder()
		srv.ServeHTTP(rec, req)
		checkStatus(t, rec, http.StatusCreated)
	})

	t.Run("missing content type is tolerated", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader(`{"title":"T2","author":"A"}`))
		rec := httptest.NewRecorder()
		srv.ServeHTTP(rec, req)
		checkStatus(t, rec, http.StatusCreated)
	})

	t.Run("oversized body", func(t *testing.T) {
		huge := `{"title":"` + strings.Repeat("a", maxRequestBytes+1024) + `","author":"A"}`
		rec := do(t, srv, http.MethodPost, "/books", huge)
		checkStatus(t, rec, http.StatusRequestEntityTooLarge)
	})
}

// TestHandlerRecoversFromPanic checks the safety net around the handlers: a
// panic must become a 500 rather than taking the process down.
func TestHandlerRecoversFromPanic(t *testing.T) {
	boom := http.HandlerFunc(func(http.ResponseWriter, *http.Request) {
		panic("boom")
	})
	h := recoverPanics(discardLogger(), logRequests(discardLogger(), boom))

	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/books", nil))

	checkStatus(t, rec, http.StatusInternalServerError)
	if got := decodeInto[errorResponse](t, rec); got.Error != "internal server error" {
		t.Errorf("error = %q, want %q", got.Error, "internal server error")
	}
}

// TestHealthReportsDatabaseFailure closes the database out from under the
// server, which is the situation the health check exists to detect.
func TestHealthReportsDatabaseFailure(t *testing.T) {
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	rec := do(t, NewServer(store, discardLogger()), http.MethodGet, "/health", nil)

	checkStatus(t, rec, http.StatusServiceUnavailable)
	if got := decodeInto[healthResponse](t, rec); got.Status != "unavailable" || got.Database != "down" {
		t.Errorf("health = %+v, want {unavailable down}", got)
	}
}
