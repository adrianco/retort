package main

import (
	"bytes"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// newTestServer returns a Server backed by a fresh in-memory database.
func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() {
		if err := store.Close(); err != nil {
			t.Errorf("close store: %v", err)
		}
	})
	// Discard log output so failing-path tests stay quiet.
	log := slog.New(slog.NewTextHandler(io.Discard, nil))
	return NewServer(store, log)
}

// do performs a request against srv and returns the recorded response.
func do(t *testing.T, srv *Server, method, target string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var reader io.Reader
	if body != nil {
		switch b := body.(type) {
		case string:
			reader = strings.NewReader(b)
		default:
			raw, err := json.Marshal(b)
			if err != nil {
				t.Fatalf("marshal body: %v", err)
			}
			reader = bytes.NewReader(raw)
		}
	}
	req := httptest.NewRequest(method, target, reader)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	return rec
}

// decodeBook unmarshals a Book from a response, failing on the wrong status.
func decodeBook(t *testing.T, rec *httptest.ResponseRecorder, wantStatus int) Book {
	t.Helper()
	if rec.Code != wantStatus {
		t.Fatalf("status = %d, want %d (body: %s)", rec.Code, wantStatus, rec.Body.String())
	}
	var b Book
	if err := json.Unmarshal(rec.Body.Bytes(), &b); err != nil {
		t.Fatalf("unmarshal book: %v (body: %s)", err, rec.Body.String())
	}
	return b
}

func createBook(t *testing.T, srv *Server, title, author string, year int, isbn string) Book {
	t.Helper()
	rec := do(t, srv, http.MethodPost, "/books", map[string]any{
		"title": title, "author": author, "year": year, "isbn": isbn,
	})
	return decodeBook(t, rec, http.StatusCreated)
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)

	rec := do(t, srv, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}

	var got map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got["status"] != "ok" || got["database"] != "ok" {
		t.Errorf("body = %v, want status/database ok", got)
	}
}

// TestHealthReportsUnavailableDatabase covers the failure branch of the health
// check by closing the database underneath a live server.
func TestHealthReportsUnavailableDatabase(t *testing.T) {
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	srv := NewServer(store, slog.New(slog.NewTextHandler(io.Discard, nil)))
	if err := store.Close(); err != nil {
		t.Fatalf("close store: %v", err)
	}

	rec := do(t, srv, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusServiceUnavailable {
		t.Fatalf("status = %d, want 503 (body: %s)", rec.Code, rec.Body.String())
	}
}

func TestCreateBook(t *testing.T) {
	srv := newTestServer(t)

	rec := do(t, srv, http.MethodPost, "/books", map[string]any{
		"title": "The Go Programming Language", "author": "Donovan", "year": 2015,
		"isbn": "978-0-134-19044-0",
	})
	got := decodeBook(t, rec, http.StatusCreated)

	if got.ID == 0 {
		t.Error("ID was not assigned")
	}
	if got.Title != "The Go Programming Language" || got.Author != "Donovan" || got.Year != 2015 {
		t.Errorf("book = %+v, want the submitted fields echoed back", got)
	}
	// Hyphens are stripped during normalisation.
	if got.ISBN != "9780134190440" {
		t.Errorf("ISBN = %q, want normalised 9780134190440", got.ISBN)
	}
	if want := "/books/" + itoa(got.ID); rec.Header().Get("Location") != want {
		t.Errorf("Location = %q, want %q", rec.Header().Get("Location"), want)
	}
}

// TestCreateAssignsDistinctIDs guards against two books colliding on one ID.
func TestCreateAssignsDistinctIDs(t *testing.T) {
	srv := newTestServer(t)

	first := createBook(t, srv, "A", "Author", 2000, "")
	second := createBook(t, srv, "B", "Author", 2001, "")
	if first.ID == second.ID {
		t.Fatalf("both books got ID %d", first.ID)
	}
}

func TestCreateValidation(t *testing.T) {
	srv := newTestServer(t)

	tests := []struct {
		name       string
		body       any
		wantStatus int
		wantField  string
	}{
		{
			name:       "missing title",
			body:       map[string]any{"author": "Someone"},
			wantStatus: http.StatusBadRequest,
			wantField:  "title",
		},
		{
			name:       "missing author",
			body:       map[string]any{"title": "Something"},
			wantStatus: http.StatusBadRequest,
			wantField:  "author",
		},
		{
			name:       "blank title is not a title",
			body:       map[string]any{"title": "   ", "author": "Someone"},
			wantStatus: http.StatusBadRequest,
			wantField:  "title",
		},
		{
			name:       "both missing",
			body:       map[string]any{},
			wantStatus: http.StatusBadRequest,
			wantField:  "title",
		},
		{
			name:       "implausible year",
			body:       map[string]any{"title": "T", "author": "A", "year": 90000},
			wantStatus: http.StatusBadRequest,
			wantField:  "year",
		},
		{
			name:       "malformed isbn",
			body:       map[string]any{"title": "T", "author": "A", "isbn": "12345"},
			wantStatus: http.StatusBadRequest,
			wantField:  "isbn",
		},
		{
			name:       "malformed json",
			body:       `{"title": `,
			wantStatus: http.StatusBadRequest,
		},
		{
			name:       "unknown field",
			body:       map[string]any{"title": "T", "author": "A", "publisher": "X"},
			wantStatus: http.StatusBadRequest,
		},
		{
			name:       "wrong type for year",
			body:       `{"title":"T","author":"A","year":"recent"}`,
			wantStatus: http.StatusBadRequest,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			rec := do(t, srv, http.MethodPost, "/books", tc.body)
			if rec.Code != tc.wantStatus {
				t.Fatalf("status = %d, want %d (body: %s)", rec.Code, tc.wantStatus, rec.Body.String())
			}
			var resp errorResponse
			if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
				t.Fatalf("unmarshal error response: %v", err)
			}
			if resp.Error == "" {
				t.Error("error message is empty")
			}
			if tc.wantField != "" && resp.Fields[tc.wantField] == "" {
				t.Errorf("fields = %v, want an entry for %q", resp.Fields, tc.wantField)
			}
		})
	}

	// Nothing above should have been persisted.
	rec := do(t, srv, http.MethodGet, "/books", nil)
	if !strings.Contains(rec.Body.String(), `"count":0`) {
		t.Errorf("rejected payloads were stored: %s", rec.Body.String())
	}
}

func TestCreateRejectsNonJSONContentType(t *testing.T) {
	srv := newTestServer(t)

	req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader(`title=T`))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)

	if rec.Code != http.StatusUnsupportedMediaType {
		t.Fatalf("status = %d, want 415 (body: %s)", rec.Code, rec.Body.String())
	}
}

func TestCreateDuplicateISBNConflicts(t *testing.T) {
	srv := newTestServer(t)
	createBook(t, srv, "First", "Author", 2001, "9780134190440")

	rec := do(t, srv, http.MethodPost, "/books", map[string]any{
		"title": "Second", "author": "Author", "isbn": "9780134190440",
	})
	if rec.Code != http.StatusConflict {
		t.Fatalf("status = %d, want 409 (body: %s)", rec.Code, rec.Body.String())
	}

	// Books without an ISBN must not collide with each other.
	createBook(t, srv, "No ISBN 1", "Author", 2002, "")
	createBook(t, srv, "No ISBN 2", "Author", 2003, "")
}

func TestListAndAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	createBook(t, srv, "Book One", "Ada Lovelace", 1843, "")
	createBook(t, srv, "Book Two", "Ada Lovelace", 1844, "")
	createBook(t, srv, "Book Three", "Grace Hopper", 1952, "")

	type listResp struct {
		Books []Book `json:"books"`
		Count int    `json:"count"`
	}

	t.Run("all", func(t *testing.T) {
		rec := do(t, srv, http.MethodGet, "/books", nil)
		var got listResp
		if rec.Code != http.StatusOK {
			t.Fatalf("status = %d, want 200", rec.Code)
		}
		if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
			t.Fatalf("unmarshal: %v", err)
		}
		if got.Count != 3 || len(got.Books) != 3 {
			t.Fatalf("count = %d / %d books, want 3", got.Count, len(got.Books))
		}
		// Results are ordered by ID, i.e. insertion order.
		if got.Books[0].Title != "Book One" || got.Books[2].Title != "Book Three" {
			t.Errorf("unexpected order: %+v", got.Books)
		}
	})

	t.Run("filtered by author", func(t *testing.T) {
		rec := do(t, srv, http.MethodGet, "/books?author=Ada+Lovelace", nil)
		var got listResp
		if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
			t.Fatalf("unmarshal: %v", err)
		}
		if got.Count != 2 {
			t.Fatalf("count = %d, want 2 (body: %s)", got.Count, rec.Body.String())
		}
		for _, b := range got.Books {
			if b.Author != "Ada Lovelace" {
				t.Errorf("got book by %q in an Ada Lovelace filter", b.Author)
			}
		}
	})

	t.Run("filter is case-insensitive", func(t *testing.T) {
		rec := do(t, srv, http.MethodGet, "/books?author=ada+lovelace", nil)
		var got listResp
		if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
			t.Fatalf("unmarshal: %v", err)
		}
		if got.Count != 2 {
			t.Errorf("count = %d, want 2", got.Count)
		}
	})

	t.Run("unknown author yields empty array not null", func(t *testing.T) {
		rec := do(t, srv, http.MethodGet, "/books?author=Nobody", nil)
		if rec.Code != http.StatusOK {
			t.Fatalf("status = %d, want 200", rec.Code)
		}
		if !strings.Contains(rec.Body.String(), `"books":[]`) {
			t.Errorf("body = %s, want an empty books array", rec.Body.String())
		}
	})
}

func TestGetBook(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, "Findable", "Author", 1999, "0306406152")

	t.Run("found", func(t *testing.T) {
		rec := do(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil)
		got := decodeBook(t, rec, http.StatusOK)
		if got != created {
			t.Errorf("got %+v, want %+v", got, created)
		}
	})

	t.Run("missing id yields 404", func(t *testing.T) {
		rec := do(t, srv, http.MethodGet, "/books/999999", nil)
		if rec.Code != http.StatusNotFound {
			t.Fatalf("status = %d, want 404 (body: %s)", rec.Code, rec.Body.String())
		}
	})

	t.Run("non-numeric id yields 400", func(t *testing.T) {
		rec := do(t, srv, http.MethodGet, "/books/abc", nil)
		if rec.Code != http.StatusBadRequest {
			t.Fatalf("status = %d, want 400 (body: %s)", rec.Code, rec.Body.String())
		}
	})
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, "Original Title", "Original Author", 1990, "0306406152")

	t.Run("replaces every field", func(t *testing.T) {
		rec := do(t, srv, http.MethodPut, "/books/"+itoa(created.ID), map[string]any{
			"title": "New Title", "author": "New Author", "year": 2020,
		})
		got := decodeBook(t, rec, http.StatusOK)

		if got.ID != created.ID {
			t.Errorf("ID = %d, want %d", got.ID, created.ID)
		}
		if got.Title != "New Title" || got.Author != "New Author" || got.Year != 2020 {
			t.Errorf("got %+v, want the new values", got)
		}
		// PUT is a full replacement, so the omitted ISBN is cleared.
		if got.ISBN != "" {
			t.Errorf("ISBN = %q, want it cleared by the replacement", got.ISBN)
		}

		// The change is durable, not just echoed.
		persisted := decodeBook(t, do(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil), http.StatusOK)
		if persisted != got {
			t.Errorf("persisted %+v, want %+v", persisted, got)
		}
	})

	t.Run("idempotent rewrite of identical values", func(t *testing.T) {
		body := map[string]any{"title": "Same", "author": "Same", "year": 2001}
		path := "/books/" + itoa(created.ID)
		if rec := do(t, srv, http.MethodPut, path, body); rec.Code != http.StatusOK {
			t.Fatalf("first put status = %d, want 200", rec.Code)
		}
		// A no-op UPDATE affects zero rows; that must not read as "not found".
		if rec := do(t, srv, http.MethodPut, path, body); rec.Code != http.StatusOK {
			t.Fatalf("second put status = %d, want 200 (body: %s)", rec.Code, rec.Body.String())
		}
	})

	t.Run("validation still applies", func(t *testing.T) {
		rec := do(t, srv, http.MethodPut, "/books/"+itoa(created.ID), map[string]any{"author": "Only Author"})
		if rec.Code != http.StatusBadRequest {
			t.Fatalf("status = %d, want 400 (body: %s)", rec.Code, rec.Body.String())
		}
	})

	t.Run("missing id yields 404", func(t *testing.T) {
		rec := do(t, srv, http.MethodPut, "/books/999999", map[string]any{"title": "T", "author": "A"})
		if rec.Code != http.StatusNotFound {
			t.Fatalf("status = %d, want 404 (body: %s)", rec.Code, rec.Body.String())
		}
	})
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, "Doomed", "Author", 2010, "")

	rec := do(t, srv, http.MethodDelete, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("status = %d, want 204 (body: %s)", rec.Code, rec.Body.String())
	}
	if body := rec.Body.String(); body != "" {
		t.Errorf("204 response had body %q", body)
	}

	if rec := do(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil); rec.Code != http.StatusNotFound {
		t.Errorf("get after delete status = %d, want 404", rec.Code)
	}
	// Deleting twice is a 404, not a silent success.
	if rec := do(t, srv, http.MethodDelete, "/books/"+itoa(created.ID), nil); rec.Code != http.StatusNotFound {
		t.Errorf("second delete status = %d, want 404", rec.Code)
	}
}

// TestMethodNotAllowed checks that ServeMux rejects verbs we do not implement.
func TestMethodNotAllowed(t *testing.T) {
	srv := newTestServer(t)

	rec := do(t, srv, http.MethodPatch, "/books/1", map[string]any{"title": "T"})
	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("PATCH status = %d, want 405", rec.Code)
	}
	if rec := do(t, srv, http.MethodGet, "/nope", nil); rec.Code != http.StatusNotFound {
		t.Errorf("unknown path status = %d, want 404", rec.Code)
	}
}

// TestFullLifecycle walks a book through create, read, update and delete the way
// a client would.
func TestFullLifecycle(t *testing.T) {
	srv := newTestServer(t)

	created := createBook(t, srv, "Lifecycle", "Tester", 2024, "9780306406157")

	fetched := decodeBook(t, do(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil), http.StatusOK)
	if fetched != created {
		t.Fatalf("fetched %+v, want %+v", fetched, created)
	}

	updated := decodeBook(t, do(t, srv, http.MethodPut, "/books/"+itoa(created.ID), map[string]any{
		"title": "Lifecycle, Revised", "author": "Tester", "year": 2025, "isbn": "9780306406157",
	}), http.StatusOK)
	if updated.Title != "Lifecycle, Revised" || updated.Year != 2025 {
		t.Fatalf("updated = %+v", updated)
	}

	if rec := do(t, srv, http.MethodDelete, "/books/"+itoa(created.ID), nil); rec.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, want 204", rec.Code)
	}
	if rec := do(t, srv, http.MethodGet, "/books", nil); !strings.Contains(rec.Body.String(), `"count":0`) {
		t.Fatalf("collection not empty after delete: %s", rec.Body.String())
	}
}
