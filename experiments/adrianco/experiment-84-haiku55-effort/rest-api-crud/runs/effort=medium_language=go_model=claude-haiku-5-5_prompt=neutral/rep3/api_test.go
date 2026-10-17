package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

// newTestServer returns an API backed by a fresh in-memory database.
func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

func do(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode response %q: %v", rec.Body.String(), err)
	}
	return v
}

func expectStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d; body: %s", rec.Code, want, rec.Body.String())
	}
}

const dune = `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}`

func TestCreateAndGetBook(t *testing.T) {
	h := newTestServer(t)

	rec := do(t, h, http.MethodPost, "/books", dune)
	expectStatus(t, rec, http.StatusCreated)
	created := decode[Book](t, rec)
	if created.ID == 0 {
		t.Fatal("created book has no ID")
	}
	if created.Title != "Dune" || created.Author != "Frank Herbert" || created.Year != 1965 {
		t.Fatalf("unexpected created book: %+v", created)
	}
	if created.ISBN != "9780441172719" {
		t.Errorf("isbn = %q, want normalized digits", created.ISBN)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/"+itoa(created.ID) {
		t.Errorf("Location = %q", loc)
	}

	rec = do(t, h, http.MethodGet, "/books/"+itoa(created.ID), "")
	expectStatus(t, rec, http.StatusOK)
	if got := decode[Book](t, rec); got != created {
		t.Errorf("GET returned %+v, want %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	h := newTestServer(t)
	tests := []struct {
		name   string
		body   string
		fields []string
	}{
		{"missing title", `{"author":"A"}`, []string{"title"}},
		{"blank title and author", `{"title":"   ","author":""}`, []string{"title", "author"}},
		{"bad year", `{"title":"T","author":"A","year":3000}`, []string{"year"}},
		{"bad isbn", `{"title":"T","author":"A","isbn":"123"}`, []string{"isbn"}},
		{"isbn bad checksum", `{"title":"T","author":"A","isbn":"9780441172718"}`, []string{"isbn"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, h, http.MethodPost, "/books", tt.body)
			expectStatus(t, rec, http.StatusBadRequest)
			resp := decode[struct {
				Error  string            `json:"error"`
				Fields map[string]string `json:"fields"`
			}](t, rec)
			if resp.Error != "validation failed" {
				t.Errorf("error = %q", resp.Error)
			}
			for _, f := range tt.fields {
				if _, ok := resp.Fields[f]; !ok {
					t.Errorf("expected problem with field %q, got %v", f, resp.Fields)
				}
			}
		})
	}
}

func TestCreateMalformedJSON(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, http.MethodPost, "/books", `{"title":`)
	expectStatus(t, rec, http.StatusBadRequest)
}

func TestDuplicateISBNConflicts(t *testing.T) {
	h := newTestServer(t)
	expectStatus(t, do(t, h, http.MethodPost, "/books", dune), http.StatusCreated)

	// Same ISBN, different formatting, must still be detected as a duplicate.
	dup := `{"title":"Other","author":"Someone","isbn":"9780441172719"}`
	expectStatus(t, do(t, h, http.MethodPost, "/books", dup), http.StatusConflict)
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	h := newTestServer(t)
	expectStatus(t, do(t, h, http.MethodPost, "/books", dune), http.StatusCreated)
	expectStatus(t, do(t, h, http.MethodPost, "/books",
		`{"title":"Children of Dune","author":"Frank Herbert"}`), http.StatusCreated)
	expectStatus(t, do(t, h, http.MethodPost, "/books",
		`{"title":"Neuromancer","author":"William Gibson"}`), http.StatusCreated)

	rec := do(t, h, http.MethodGet, "/books", "")
	expectStatus(t, rec, http.StatusOK)
	if all := decode[[]Book](t, rec); len(all) != 3 {
		t.Fatalf("unfiltered list has %d books, want 3", len(all))
	}

	rec = do(t, h, http.MethodGet, "/books?author=frank%20herbert", "")
	expectStatus(t, rec, http.StatusOK)
	filtered := decode[[]Book](t, rec)
	if len(filtered) != 2 {
		t.Fatalf("author filter returned %d books, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Frank Herbert" {
			t.Errorf("filter leaked book by %q", b.Author)
		}
	}

	rec = do(t, h, http.MethodGet, "/books?author=Nobody", "")
	expectStatus(t, rec, http.StatusOK)
	if body := strings.TrimSpace(rec.Body.String()); body != "[]" {
		t.Errorf("empty result body = %s, want []", body)
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestServer(t)
	created := decode[Book](t, do(t, h, http.MethodPost, "/books", dune))

	rec := do(t, h, http.MethodPut, "/books/"+itoa(created.ID),
		`{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
	expectStatus(t, rec, http.StatusOK)
	updated := decode[Book](t, rec)
	if updated.ID != created.ID || updated.Title != "Dune Messiah" || updated.Year != 1969 {
		t.Fatalf("unexpected update result: %+v", updated)
	}
	if updated.ISBN != "" {
		t.Errorf("PUT without isbn should clear it, got %q", updated.ISBN)
	}

	rec = do(t, h, http.MethodGet, "/books/"+itoa(created.ID), "")
	if got := decode[Book](t, rec); got != updated {
		t.Errorf("GET after PUT = %+v, want %+v", got, updated)
	}
}

func TestUpdateValidationAndNotFound(t *testing.T) {
	h := newTestServer(t)
	created := decode[Book](t, do(t, h, http.MethodPost, "/books", dune))

	expectStatus(t, do(t, h, http.MethodPut, "/books/"+itoa(created.ID), `{"author":"X"}`),
		http.StatusBadRequest)
	expectStatus(t, do(t, h, http.MethodPut, "/books/999999", `{"title":"T","author":"A"}`),
		http.StatusNotFound)
}

func TestDeleteBook(t *testing.T) {
	h := newTestServer(t)
	created := decode[Book](t, do(t, h, http.MethodPost, "/books", dune))
	path := "/books/" + itoa(created.ID)

	expectStatus(t, do(t, h, http.MethodDelete, path, ""), http.StatusNoContent)
	expectStatus(t, do(t, h, http.MethodGet, path, ""), http.StatusNotFound)
	expectStatus(t, do(t, h, http.MethodDelete, path, ""), http.StatusNotFound)
}

func TestInvalidAndMissingIDs(t *testing.T) {
	h := newTestServer(t)
	for _, id := range []string{"abc", "0", "-3", "1.5"} {
		expectStatus(t, do(t, h, http.MethodGet, "/books/"+id, ""), http.StatusBadRequest)
	}
	expectStatus(t, do(t, h, http.MethodGet, "/books/42", ""), http.StatusNotFound)
}

func TestHealth(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, http.MethodGet, "/health", "")
	expectStatus(t, rec, http.StatusOK)
	if got := decode[map[string]string](t, rec)["status"]; got != "ok" {
		t.Errorf("status = %q, want ok", got)
	}
}

func TestMethodNotAllowedAndUnknownRoutesAreJSON(t *testing.T) {
	h := newTestServer(t)

	rec := do(t, h, http.MethodPatch, "/books/1", "")
	expectStatus(t, rec, http.StatusMethodNotAllowed)
	if allow := rec.Header().Get("Allow"); allow != "GET, PUT, DELETE" {
		t.Errorf("Allow = %q", allow)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q", ct)
	}

	expectStatus(t, do(t, h, http.MethodPost, "/health", ""), http.StatusMethodNotAllowed)
	expectStatus(t, do(t, h, http.MethodGet, "/nope", ""), http.StatusNotFound)
}

// TestDataPersistsAcrossRestart checks that books survive reopening the
// database file, which is the point of using SQLite rather than memory.
func TestDataPersistsAcrossRestart(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	h := NewServer(store)
	created := decode[Book](t, do(t, h, http.MethodPost, "/books", dune))
	store.Close()

	store2, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer store2.Close()
	rec := do(t, NewServer(store2), http.MethodGet, "/books/"+itoa(created.ID), "")
	expectStatus(t, rec, http.StatusOK)
	if got := decode[Book](t, rec); got != created {
		t.Errorf("after reopen got %+v, want %+v", got, created)
	}
}

func itoa(n int64) string {
	return strconv.FormatInt(n, 10)
}
