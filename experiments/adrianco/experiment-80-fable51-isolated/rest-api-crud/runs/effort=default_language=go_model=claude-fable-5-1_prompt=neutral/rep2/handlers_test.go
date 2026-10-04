package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

func newTestHandler(t *testing.T) http.Handler {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewHandler(store)
}

func do(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Fatalf("Content-Type = %q, want application/json", ct)
	}
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode %q: %v", rec.Body.String(), err)
	}
	return v
}

func wantStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d (body: %s)", rec.Code, want, rec.Body.String())
	}
}

const dune = `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`

func TestHealth(t *testing.T) {
	h := newTestHandler(t)
	rec := do(t, h, http.MethodGet, "/health", "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[map[string]string](t, rec); got["status"] != "ok" {
		t.Errorf("status = %q, want ok", got["status"])
	}
}

func TestCreateAndGetBook(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, http.MethodPost, "/books", dune)
	wantStatus(t, rec, http.StatusCreated)
	created := decode[Book](t, rec)
	want := Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"}
	if created.ID <= 0 || created != want {
		t.Errorf("created = %+v, want %+v with positive ID", created, want)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}

	rec = do(t, h, http.MethodGet, "/books/1", "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[Book](t, rec); got != want {
		t.Errorf("got = %+v, want %+v", got, want)
	}
}

func TestCreateValidation(t *testing.T) {
	h := newTestHandler(t)

	tests := []struct {
		name       string
		body       string
		status     int
		wantFields []string
	}{
		{"missing title", `{"author":"A"}`, http.StatusUnprocessableEntity, []string{"title"}},
		{"missing author", `{"title":"T"}`, http.StatusUnprocessableEntity, []string{"author"}},
		{"blank title and author", `{"title":"  ","author":""}`, http.StatusUnprocessableEntity, []string{"title", "author"}},
		{"negative year", `{"title":"T","author":"A","year":-1}`, http.StatusUnprocessableEntity, []string{"year"}},
		{"malformed JSON", `{"title":`, http.StatusBadRequest, nil},
		{"wrong type", `{"title":"T","author":"A","year":"1965"}`, http.StatusBadRequest, nil},
		{"empty body", ``, http.StatusBadRequest, nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, h, http.MethodPost, "/books", tt.body)
			wantStatus(t, rec, tt.status)
			resp := decode[struct {
				Error  string            `json:"error"`
				Fields map[string]string `json:"fields"`
			}](t, rec)
			if resp.Error == "" {
				t.Error("expected an error message")
			}
			if len(resp.Fields) != len(tt.wantFields) {
				t.Errorf("fields = %v, want keys %v", resp.Fields, tt.wantFields)
			}
			for _, f := range tt.wantFields {
				if resp.Fields[f] == "" {
					t.Errorf("missing problem for field %q in %v", f, resp.Fields)
				}
			}
		})
	}

	// Nothing invalid should have been stored.
	rec := do(t, h, http.MethodGet, "/books", "")
	if got := decode[[]Book](t, rec); len(got) != 0 {
		t.Errorf("expected no books, got %+v", got)
	}
}

func TestListBooksAndAuthorFilter(t *testing.T) {
	h := newTestHandler(t)

	// An empty collection is an empty array, not null.
	rec := do(t, h, http.MethodGet, "/books", "")
	wantStatus(t, rec, http.StatusOK)
	if body := strings.TrimSpace(rec.Body.String()); body != "[]" {
		t.Errorf("empty list body = %q, want []", body)
	}

	for _, b := range []string{
		dune,
		`{"title":"Children of Dune","author":"Frank Herbert","year":1976}`,
		`{"title":"Neuromancer","author":"William Gibson","year":1984}`,
	} {
		wantStatus(t, do(t, h, http.MethodPost, "/books", b), http.StatusCreated)
	}

	rec = do(t, h, http.MethodGet, "/books", "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[[]Book](t, rec); len(got) != 3 {
		t.Errorf("len(all) = %d, want 3", len(got))
	}

	rec = do(t, h, http.MethodGet, "/books?author=Frank+Herbert", "")
	wantStatus(t, rec, http.StatusOK)
	got := decode[[]Book](t, rec)
	if len(got) != 2 {
		t.Fatalf("len(filtered) = %d, want 2", len(got))
	}
	for _, b := range got {
		if b.Author != "Frank Herbert" {
			t.Errorf("unexpected author %q in filtered list", b.Author)
		}
	}

	rec = do(t, h, http.MethodGet, "/books?author=william+gibson", "")
	if got := decode[[]Book](t, rec); len(got) != 1 || got[0].Title != "Neuromancer" {
		t.Errorf("case-insensitive filter = %+v, want Neuromancer only", got)
	}

	rec = do(t, h, http.MethodGet, "/books?author=Nobody", "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[[]Book](t, rec); len(got) != 0 {
		t.Errorf("filter with no matches = %+v, want empty", got)
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestHandler(t)
	wantStatus(t, do(t, h, http.MethodPost, "/books", dune), http.StatusCreated)

	rec := do(t, h, http.MethodPut, "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
	wantStatus(t, rec, http.StatusOK)
	want := Book{ID: 1, Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969}
	if got := decode[Book](t, rec); got != want {
		t.Errorf("updated = %+v, want %+v", got, want)
	}

	// The change must be persisted, not just echoed.
	rec = do(t, h, http.MethodGet, "/books/1", "")
	if got := decode[Book](t, rec); got != want {
		t.Errorf("after update = %+v, want %+v", got, want)
	}

	rec = do(t, h, http.MethodPut, "/books/1", `{"title":"","author":"Frank Herbert"}`)
	wantStatus(t, rec, http.StatusUnprocessableEntity)

	rec = do(t, h, http.MethodPut, "/books/999", dune)
	wantStatus(t, rec, http.StatusNotFound)
}

func TestDeleteBook(t *testing.T) {
	h := newTestHandler(t)
	wantStatus(t, do(t, h, http.MethodPost, "/books", dune), http.StatusCreated)

	rec := do(t, h, http.MethodDelete, "/books/1", "")
	wantStatus(t, rec, http.StatusNoContent)
	if rec.Body.Len() != 0 {
		t.Errorf("expected empty body, got %q", rec.Body.String())
	}

	wantStatus(t, do(t, h, http.MethodGet, "/books/1", ""), http.StatusNotFound)
	wantStatus(t, do(t, h, http.MethodDelete, "/books/1", ""), http.StatusNotFound)
}

func TestNotFoundAndBadID(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, http.MethodGet, "/books/42", "")
	wantStatus(t, rec, http.StatusNotFound)
	if got := decode[map[string]string](t, rec); got["error"] == "" {
		t.Error("expected an error message")
	}

	for _, id := range []string{"abc", "0", "-1", "1.5"} {
		for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
			rec := do(t, h, method, "/books/"+id, dune)
			if rec.Code != http.StatusBadRequest {
				t.Errorf("%s /books/%s = %d, want 400", method, id, rec.Code)
			}
		}
	}

	wantStatus(t, do(t, h, http.MethodPatch, "/books/1", ""), http.StatusMethodNotAllowed)
}

func TestPersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := NewStore(path)
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	wantStatus(t, do(t, NewHandler(store), http.MethodPost, "/books", dune), http.StatusCreated)
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	store, err = NewStore(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer store.Close()
	rec := do(t, NewHandler(store), http.MethodGet, "/books/1", "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[Book](t, rec); got.Title != "Dune" {
		t.Errorf("title after reopen = %q, want Dune", got.Title)
	}
}
