package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

// newTestServer spins up the full stack (router + middleware + SQLite store)
// against a throwaway database file.
func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()

	store, err := OpenStore(context.Background(), filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() {
		if err := store.Close(); err != nil {
			t.Errorf("close store: %v", err)
		}
	})

	srv := httptest.NewServer(NewServer(store, nil))
	t.Cleanup(srv.Close)
	return srv
}

// do issues a request against the test server. A non-nil body is JSON-encoded
// unless it is already a string, which is sent verbatim (for malformed-JSON
// cases).
func do(t *testing.T, srv *httptest.Server, method, path string, body any) (*http.Response, []byte) {
	t.Helper()

	var reader io.Reader
	if body != nil {
		switch v := body.(type) {
		case string:
			reader = strings.NewReader(v)
		default:
			encoded, err := json.Marshal(v)
			if err != nil {
				t.Fatalf("marshal request body: %v", err)
			}
			reader = bytes.NewReader(encoded)
		}
	}

	req, err := http.NewRequest(method, srv.URL+path, reader)
	if err != nil {
		t.Fatalf("build request: %v", err)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	resp, err := srv.Client().Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, path, err)
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read response body: %v", err)
	}
	return resp, raw
}

func decodeInto[T any](t *testing.T, raw []byte) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(raw, &v); err != nil {
		t.Fatalf("decode %T from %q: %v", v, raw, err)
	}
	return v
}

func requireStatus(t *testing.T, resp *http.Response, raw []byte, want int) {
	t.Helper()
	if resp.StatusCode != want {
		t.Fatalf("%s %s: status = %d, want %d (body: %s)",
			resp.Request.Method, resp.Request.URL.Path, resp.StatusCode, want, raw)
	}
	if ct := resp.Header.Get("Content-Type"); want != http.StatusNoContent &&
		!strings.HasPrefix(ct, "application/json") {
		t.Fatalf("Content-Type = %q, want application/json", ct)
	}
}

// createBook is a helper for tests that need existing data.
func createBook(t *testing.T, srv *httptest.Server, body map[string]any) Book {
	t.Helper()
	resp, raw := do(t, srv, http.MethodPost, "/books", body)
	requireStatus(t, resp, raw, http.StatusCreated)
	return decodeInto[Book](t, raw)
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)

	resp, raw := do(t, srv, http.MethodGet, "/health", nil)
	requireStatus(t, resp, raw, http.StatusOK)

	got := decodeInto[map[string]string](t, raw)
	if got["status"] != "ok" {
		t.Errorf("status = %q, want %q", got["status"], "ok")
	}
}

func TestCreateBook(t *testing.T) {
	srv := newTestServer(t)

	before := time.Now().UTC().Add(-time.Second)
	resp, raw := do(t, srv, http.MethodPost, "/books", map[string]any{
		"title":  "  The Go Programming Language  ",
		"author": "Alan Donovan",
		"year":   2015,
		"isbn":   "978-0-13-419044-0",
	})
	requireStatus(t, resp, raw, http.StatusCreated)

	book := decodeInto[Book](t, raw)
	if book.ID < 1 {
		t.Errorf("ID = %d, want a positive id", book.ID)
	}
	// Surrounding whitespace should be trimmed.
	if book.Title != "The Go Programming Language" {
		t.Errorf("Title = %q, want it trimmed", book.Title)
	}
	if book.Author != "Alan Donovan" {
		t.Errorf("Author = %q", book.Author)
	}
	if book.Year != 2015 {
		t.Errorf("Year = %d, want 2015", book.Year)
	}
	// Separators should be stripped by normalization.
	if book.ISBN != "9780134190440" {
		t.Errorf("ISBN = %q, want %q", book.ISBN, "9780134190440")
	}
	if book.CreatedAt.Before(before) || book.CreatedAt.After(time.Now().UTC().Add(time.Second)) {
		t.Errorf("CreatedAt = %v, want ~now", book.CreatedAt)
	}
	if !book.UpdatedAt.Equal(book.CreatedAt) {
		t.Errorf("UpdatedAt = %v, want it to equal CreatedAt %v", book.UpdatedAt, book.CreatedAt)
	}

	if got, want := resp.Header.Get("Location"), fmt.Sprintf("/books/%d", book.ID); got != want {
		t.Errorf("Location = %q, want %q", got, want)
	}

	// The Location header must point at the persisted record.
	resp, raw = do(t, srv, http.MethodGet, resp.Header.Get("Location"), nil)
	requireStatus(t, resp, raw, http.StatusOK)
	if fetched := decodeInto[Book](t, raw); fetched != book {
		t.Errorf("fetched = %+v, want %+v", fetched, book)
	}
}

func TestCreateBookOptionalFields(t *testing.T) {
	srv := newTestServer(t)

	book := createBook(t, srv, map[string]any{"title": "Untitled Draft", "author": "Anon"})
	if book.Year != 0 || book.ISBN != "" {
		t.Errorf("got Year=%d ISBN=%q, want zero values when omitted", book.Year, book.ISBN)
	}

	// Two books without an ISBN must not collide on the unique index.
	createBook(t, srv, map[string]any{"title": "Another Draft", "author": "Anon", "isbn": ""})
}

func TestCreateBookValidation(t *testing.T) {
	srv := newTestServer(t)

	tests := []struct {
		name       string
		body       any
		wantStatus int
		wantDetail string
	}{
		{
			name:       "missing title",
			body:       map[string]any{"author": "Ursula K. Le Guin"},
			wantStatus: http.StatusBadRequest,
			wantDetail: "title is required",
		},
		{
			name:       "blank title",
			body:       map[string]any{"title": "   ", "author": "Ursula K. Le Guin"},
			wantStatus: http.StatusBadRequest,
			wantDetail: "title is required",
		},
		{
			name:       "missing author",
			body:       map[string]any{"title": "The Dispossessed"},
			wantStatus: http.StatusBadRequest,
			wantDetail: "author is required",
		},
		{
			name:       "both missing reports both problems",
			body:       map[string]any{"year": 1974},
			wantStatus: http.StatusBadRequest,
			wantDetail: "author is required",
		},
		{
			name:       "year in the far future",
			body:       map[string]any{"title": "Tomorrow", "author": "A", "year": 9999},
			wantStatus: http.StatusBadRequest,
			wantDetail: "year must be 0 (unknown) or between",
		},
		{
			name:       "negative year",
			body:       map[string]any{"title": "Yesterday", "author": "A", "year": -5},
			wantStatus: http.StatusBadRequest,
			wantDetail: "year must be 0 (unknown) or between",
		},
		{
			name:       "isbn wrong length",
			body:       map[string]any{"title": "T", "author": "A", "isbn": "12345"},
			wantStatus: http.StatusBadRequest,
			wantDetail: "isbn must have 10 or 13 digits",
		},
		{
			name:       "isbn bad check digit",
			body:       map[string]any{"title": "T", "author": "A", "isbn": "9780134190441"},
			wantStatus: http.StatusBadRequest,
			wantDetail: "invalid ISBN-13 check digit",
		},
		{
			name:       "wrong field type",
			body:       `{"title":"T","author":"A","year":"nineteen"}`,
			wantStatus: http.StatusBadRequest,
			wantDetail: `field "year" must be of type int`,
		},
		{
			name:       "unknown field",
			body:       `{"title":"T","author":"A","publisher":"Nope"}`,
			wantStatus: http.StatusBadRequest,
			wantDetail: "publisher",
		},
		{
			name:       "malformed json",
			body:       `{"title":`,
			wantStatus: http.StatusBadRequest,
			wantDetail: "invalid JSON",
		},
		{
			name:       "empty body",
			body:       ``,
			wantStatus: http.StatusBadRequest,
			wantDetail: "body is empty",
		},
		{
			name:       "trailing garbage",
			body:       `{"title":"T","author":"A"}{"title":"U","author":"B"}`,
			wantStatus: http.StatusBadRequest,
			wantDetail: "exactly one JSON object",
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			resp, raw := do(t, srv, http.MethodPost, "/books", tc.body)
			requireStatus(t, resp, raw, tc.wantStatus)

			body := decodeInto[errorBody](t, raw)
			joined := body.Error + " " + strings.Join(body.Details, " ")
			if !strings.Contains(joined, tc.wantDetail) {
				t.Errorf("response %q does not mention %q", joined, tc.wantDetail)
			}
		})
	}

	// Nothing above should have been persisted.
	resp, raw := do(t, srv, http.MethodGet, "/books", nil)
	requireStatus(t, resp, raw, http.StatusOK)
	if books := decodeInto[[]Book](t, raw); len(books) != 0 {
		t.Errorf("collection has %d books, want 0 after only invalid requests", len(books))
	}
}

func TestCreateBookRejectsNonJSONContentType(t *testing.T) {
	srv := newTestServer(t)

	req, err := http.NewRequest(http.MethodPost, srv.URL+"/books", strings.NewReader(`title=T`))
	if err != nil {
		t.Fatalf("build request: %v", err)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := srv.Client().Do(req)
	if err != nil {
		t.Fatalf("post: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusUnsupportedMediaType {
		t.Errorf("status = %d, want %d", resp.StatusCode, http.StatusUnsupportedMediaType)
	}
}

func TestCreateDuplicateISBNConflicts(t *testing.T) {
	srv := newTestServer(t)

	createBook(t, srv, map[string]any{
		"title": "The Go Programming Language", "author": "Donovan", "isbn": "9780134190440",
	})

	// Same ISBN, written with separators: normalization must catch the clash.
	resp, raw := do(t, srv, http.MethodPost, "/books", map[string]any{
		"title": "Duplicate", "author": "Someone", "isbn": "978-0-13-419044-0",
	})
	requireStatus(t, resp, raw, http.StatusConflict)

	if body := decodeInto[errorBody](t, raw); !strings.Contains(body.Error, "isbn") {
		t.Errorf("error = %q, want it to mention isbn", body.Error)
	}
}

func TestListBooksAndAuthorFilter(t *testing.T) {
	srv := newTestServer(t)

	// An empty collection must serialize as [], never null.
	resp, raw := do(t, srv, http.MethodGet, "/books", nil)
	requireStatus(t, resp, raw, http.StatusOK)
	if got := strings.TrimSpace(string(raw)); got != "[]" {
		t.Errorf("empty list body = %q, want %q", got, "[]")
	}

	for _, b := range []map[string]any{
		{"title": "A Wizard of Earthsea", "author": "Ursula K. Le Guin", "year": 1968},
		{"title": "The Dispossessed", "author": "Ursula K. Le Guin", "year": 1974},
		{"title": "Neuromancer", "author": "William Gibson", "year": 1984},
	} {
		createBook(t, srv, b)
	}

	tests := []struct {
		name       string
		query      string
		wantTitles []string
	}{
		{"no filter returns all in id order", "", []string{"A Wizard of Earthsea", "The Dispossessed", "Neuromancer"}},
		{"exact author", "?author=Ursula+K.+Le+Guin", []string{"A Wizard of Earthsea", "The Dispossessed"}},
		{"case insensitive", "?author=ursula+k.+le+guin", []string{"A Wizard of Earthsea", "The Dispossessed"}},
		{"partial match", "?author=Gibson", []string{"Neuromancer"}},
		{"surrounding spaces ignored", "?author=+Gibson+", []string{"Neuromancer"}},
		{"empty filter is ignored", "?author=", []string{"A Wizard of Earthsea", "The Dispossessed", "Neuromancer"}},
		{"no matches", "?author=Asimov", nil},
		// A bare "%" must be escaped rather than matching everything.
		{"wildcards are escaped", "?author=%25", nil},
		{"underscore is escaped", "?author=_", nil},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			resp, raw := do(t, srv, http.MethodGet, "/books"+tc.query, nil)
			requireStatus(t, resp, raw, http.StatusOK)

			books := decodeInto[[]Book](t, raw)
			var titles []string
			for _, b := range books {
				titles = append(titles, b.Title)
			}
			if fmt.Sprint(titles) != fmt.Sprint(tc.wantTitles) {
				t.Errorf("titles = %v, want %v", titles, tc.wantTitles)
			}
		})
	}
}

func TestGetBookNotFound(t *testing.T) {
	srv := newTestServer(t)

	resp, raw := do(t, srv, http.MethodGet, "/books/424242", nil)
	requireStatus(t, resp, raw, http.StatusNotFound)
	if body := decodeInto[errorBody](t, raw); body.Error != "book not found" {
		t.Errorf("error = %q, want %q", body.Error, "book not found")
	}
}

func TestInvalidIDIsRejected(t *testing.T) {
	srv := newTestServer(t)

	for _, id := range []string{"abc", "0", "-1", "1.5", "9999999999999999999999"} {
		for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
			var body any
			if method == http.MethodPut {
				body = map[string]any{"title": "T", "author": "A"}
			}
			resp, raw := do(t, srv, method, "/books/"+id, body)
			requireStatus(t, resp, raw, http.StatusBadRequest)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)

	original := createBook(t, srv, map[string]any{
		"title": "Neuromancer", "author": "W. Gibson", "year": 1984, "isbn": "9780441569595",
	})

	resp, raw := do(t, srv, http.MethodPut, fmt.Sprintf("/books/%d", original.ID), map[string]any{
		"title": "Neuromancer (Sprawl #1)", "author": "William Gibson", "year": 1984,
	})
	requireStatus(t, resp, raw, http.StatusOK)

	updated := decodeInto[Book](t, raw)
	if updated.ID != original.ID {
		t.Errorf("ID = %d, want it unchanged at %d", updated.ID, original.ID)
	}
	if updated.Title != "Neuromancer (Sprawl #1)" || updated.Author != "William Gibson" {
		t.Errorf("got %+v, want the new title and author", updated)
	}
	// PUT replaces the whole record, so the omitted ISBN must be cleared.
	if updated.ISBN != "" {
		t.Errorf("ISBN = %q, want it cleared by the full replacement", updated.ISBN)
	}
	if !updated.CreatedAt.Equal(original.CreatedAt) {
		t.Errorf("CreatedAt = %v, want it preserved at %v", updated.CreatedAt, original.CreatedAt)
	}
	if updated.UpdatedAt.Before(original.UpdatedAt) {
		t.Errorf("UpdatedAt = %v, want it at or after %v", updated.UpdatedAt, original.UpdatedAt)
	}

	// The change must be durable, and the freed ISBN reusable.
	resp, raw = do(t, srv, http.MethodGet, fmt.Sprintf("/books/%d", original.ID), nil)
	requireStatus(t, resp, raw, http.StatusOK)
	if fetched := decodeInto[Book](t, raw); fetched != updated {
		t.Errorf("fetched = %+v, want %+v", fetched, updated)
	}
	createBook(t, srv, map[string]any{"title": "Other", "author": "A", "isbn": "9780441569595"})
}

func TestUpdateBookErrors(t *testing.T) {
	srv := newTestServer(t)

	first := createBook(t, srv, map[string]any{"title": "One", "author": "A", "isbn": "9780134190440"})
	second := createBook(t, srv, map[string]any{"title": "Two", "author": "B", "isbn": "9780441569595"})

	t.Run("missing book", func(t *testing.T) {
		resp, raw := do(t, srv, http.MethodPut, "/books/424242",
			map[string]any{"title": "Ghost", "author": "Nobody"})
		requireStatus(t, resp, raw, http.StatusNotFound)
	})

	t.Run("validation still applies", func(t *testing.T) {
		resp, raw := do(t, srv, http.MethodPut, fmt.Sprintf("/books/%d", first.ID),
			map[string]any{"author": "A"})
		requireStatus(t, resp, raw, http.StatusBadRequest)
	})

	t.Run("stealing another book's isbn conflicts", func(t *testing.T) {
		resp, raw := do(t, srv, http.MethodPut, fmt.Sprintf("/books/%d", first.ID),
			map[string]any{"title": "One", "author": "A", "isbn": second.ISBN})
		requireStatus(t, resp, raw, http.StatusConflict)
	})

	t.Run("keeping its own isbn is fine", func(t *testing.T) {
		resp, raw := do(t, srv, http.MethodPut, fmt.Sprintf("/books/%d", first.ID),
			map[string]any{"title": "One Revised", "author": "A", "isbn": first.ISBN})
		requireStatus(t, resp, raw, http.StatusOK)
	})
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)

	book := createBook(t, srv, map[string]any{"title": "Ephemeral", "author": "A"})

	resp, raw := do(t, srv, http.MethodDelete, fmt.Sprintf("/books/%d", book.ID), nil)
	requireStatus(t, resp, raw, http.StatusNoContent)
	if len(raw) != 0 {
		t.Errorf("body = %q, want it empty for 204", raw)
	}

	resp, raw = do(t, srv, http.MethodGet, fmt.Sprintf("/books/%d", book.ID), nil)
	requireStatus(t, resp, raw, http.StatusNotFound)

	// Deleting again must not silently succeed.
	resp, raw = do(t, srv, http.MethodDelete, fmt.Sprintf("/books/%d", book.ID), nil)
	requireStatus(t, resp, raw, http.StatusNotFound)
}

func TestUnroutedRequestsReturnJSON(t *testing.T) {
	srv := newTestServer(t)

	t.Run("unknown path", func(t *testing.T) {
		resp, raw := do(t, srv, http.MethodGet, "/authors", nil)
		requireStatus(t, resp, raw, http.StatusNotFound)
		if body := decodeInto[errorBody](t, raw); body.Error != "resource not found" {
			t.Errorf("error = %q, want %q", body.Error, "resource not found")
		}
	})

	t.Run("unsupported method", func(t *testing.T) {
		resp, raw := do(t, srv, http.MethodPatch, "/books", `{}`)
		requireStatus(t, resp, raw, http.StatusMethodNotAllowed)

		body := decodeInto[errorBody](t, raw)
		if body.Error != "method not allowed" {
			t.Errorf("error = %q, want %q", body.Error, "method not allowed")
		}
		if allow := resp.Header.Get("Allow"); !strings.Contains(allow, http.MethodPost) {
			t.Errorf("Allow = %q, want it to list POST", allow)
		}
	})
}

func TestOversizedBodyRejected(t *testing.T) {
	srv := newTestServer(t)

	huge := strings.Repeat("x", maxBodyBytes+1)
	resp, raw := do(t, srv, http.MethodPost, "/books",
		fmt.Sprintf(`{"title":%q,"author":"A"}`, huge))
	requireStatus(t, resp, raw, http.StatusRequestEntityTooLarge)
}

// TestConcurrentCreates guards against SQLite "database is locked" errors and
// duplicate IDs when handlers run in parallel.
func TestConcurrentCreates(t *testing.T) {
	srv := newTestServer(t)

	const n = 25
	var wg sync.WaitGroup
	ids := make(chan int64, n)

	for i := range n {
		wg.Add(1)
		go func() {
			defer wg.Done()
			resp, raw := do(t, srv, http.MethodPost, "/books", map[string]any{
				"title": fmt.Sprintf("Book %d", i), "author": "Prolific Writer",
			})
			if resp.StatusCode != http.StatusCreated {
				t.Errorf("concurrent create: status = %d (body: %s)", resp.StatusCode, raw)
				return
			}
			ids <- decodeInto[Book](t, raw).ID
		}()
	}
	wg.Wait()
	close(ids)

	seen := map[int64]bool{}
	for id := range ids {
		if seen[id] {
			t.Errorf("id %d was handed out twice", id)
		}
		seen[id] = true
	}
	if len(seen) != n {
		t.Fatalf("created %d books, want %d", len(seen), n)
	}

	resp, raw := do(t, srv, http.MethodGet, "/books?author=Prolific", nil)
	requireStatus(t, resp, raw, http.StatusOK)
	if books := decodeInto[[]Book](t, raw); len(books) != n {
		t.Errorf("listed %d books, want %d", len(books), n)
	}
}

func TestPanicIsRecovered(t *testing.T) {
	// A handler that blows up must yield a JSON 500 rather than a dropped
	// connection.
	rec := httptest.NewRecorder()
	handler := recoverPanics(discardLogger())(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {
		panic("boom")
	}))
	handler.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/books", nil))

	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want %d", rec.Code, http.StatusInternalServerError)
	}
	if body := decodeInto[errorBody](t, rec.Body.Bytes()); body.Error != "internal server error" {
		t.Errorf("error = %q, want %q", body.Error, "internal server error")
	}
}
