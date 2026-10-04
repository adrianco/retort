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
		t.Fatalf("status = %d, want %d (body %s)", rec.Code, want, rec.Body.String())
	}
}

const dune = `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`

func TestHealth(t *testing.T) {
	rec := do(t, newTestHandler(t), "GET", "/health", "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[map[string]string](t, rec)["status"]; got != "ok" {
		t.Errorf("status = %q, want ok", got)
	}
}

func TestCreateAndGet(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, "POST", "/books", dune)
	wantStatus(t, rec, http.StatusCreated)
	created := decode[Book](t, rec)
	want := Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"}
	if created.ID == 0 || created != want {
		t.Fatalf("created = %+v, want %+v with non-zero ID", created, want)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}

	rec = do(t, h, "GET", "/books/1", "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[Book](t, rec); got != want {
		t.Errorf("got %+v, want %+v", got, want)
	}
}

func TestCreateValidation(t *testing.T) {
	h := newTestHandler(t)
	tests := []struct {
		name, body string
		fields     []string
	}{
		{"missing title", `{"author":"A"}`, []string{"title"}},
		{"missing author", `{"title":"T"}`, []string{"author"}},
		{"blank title and author", `{"title":"  ","author":""}`, []string{"title", "author"}},
		{"negative year", `{"title":"T","author":"A","year":-1}`, []string{"year"}},
		{"malformed json", `{"title":`, nil},
		{"wrong type", `{"title":"T","author":"A","year":"1965"}`, nil},
		{"empty body", ``, nil},
		{"trailing data", `{"title":"T","author":"A"}{}`, nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, h, "POST", "/books", tt.body)
			wantStatus(t, rec, http.StatusBadRequest)
			body := decode[errorBody](t, rec)
			if body.Error == "" {
				t.Error("missing error message")
			}
			if len(body.Fields) != len(tt.fields) {
				t.Errorf("fields = %v, want %v", body.Fields, tt.fields)
			}
			for _, f := range tt.fields {
				if body.Fields[f] == "" {
					t.Errorf("missing field error for %q in %v", f, body.Fields)
				}
			}
		})
	}

	rec := do(t, h, "GET", "/books", "")
	if got := decode[[]Book](t, rec); len(got) != 0 {
		t.Errorf("invalid requests stored books: %+v", got)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, "GET", "/books", "")
	wantStatus(t, rec, http.StatusOK)
	if got := strings.TrimSpace(rec.Body.String()); got != "[]" {
		t.Errorf("empty list body = %s, want []", got)
	}

	for _, b := range []string{
		dune,
		`{"title":"Emma","author":"Jane Austen","year":1815}`,
		`{"title":"Children of Dune","author":"Frank Herbert","year":1976}`,
	} {
		wantStatus(t, do(t, h, "POST", "/books", b), http.StatusCreated)
	}

	if got := decode[[]Book](t, do(t, h, "GET", "/books", "")); len(got) != 3 {
		t.Fatalf("listed %d books, want 3", len(got))
	}

	got := decode[[]Book](t, do(t, h, "GET", "/books?author=Frank+Herbert", ""))
	if len(got) != 2 || got[0].Title != "Dune" || got[1].Title != "Children of Dune" {
		t.Errorf("filtered = %+v, want the two Herbert books", got)
	}

	if got := decode[[]Book](t, do(t, h, "GET", "/books?author=frank+herbert", "")); len(got) != 2 {
		t.Errorf("case-insensitive filter returned %d books, want 2", len(got))
	}

	rec = do(t, h, "GET", "/books?author=Nobody", "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[[]Book](t, rec); len(got) != 0 {
		t.Errorf("unknown author returned %+v", got)
	}
}

func TestUpdate(t *testing.T) {
	h := newTestHandler(t)
	wantStatus(t, do(t, h, "POST", "/books", dune), http.StatusCreated)

	rec := do(t, h, "PUT", "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
	wantStatus(t, rec, http.StatusOK)
	want := Book{ID: 1, Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969}
	if got := decode[Book](t, rec); got != want {
		t.Errorf("update response = %+v, want %+v", got, want)
	}
	if got := decode[Book](t, do(t, h, "GET", "/books/1", "")); got != want {
		t.Errorf("after update = %+v, want %+v", got, want)
	}

	wantStatus(t, do(t, h, "PUT", "/books/1", `{"title":"","author":"X"}`), http.StatusBadRequest)
	wantStatus(t, do(t, h, "PUT", "/books/99", dune), http.StatusNotFound)
	wantStatus(t, do(t, h, "PUT", "/books/abc", dune), http.StatusBadRequest)
}

func TestDelete(t *testing.T) {
	h := newTestHandler(t)
	wantStatus(t, do(t, h, "POST", "/books", dune), http.StatusCreated)

	rec := do(t, h, "DELETE", "/books/1", "")
	wantStatus(t, rec, http.StatusNoContent)
	if rec.Body.Len() != 0 {
		t.Errorf("delete body = %q, want empty", rec.Body.String())
	}
	wantStatus(t, do(t, h, "GET", "/books/1", ""), http.StatusNotFound)
	wantStatus(t, do(t, h, "DELETE", "/books/1", ""), http.StatusNotFound)
}

func TestNotFoundAndBadID(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, "GET", "/books/42", "")
	wantStatus(t, rec, http.StatusNotFound)
	if decode[errorBody](t, rec).Error == "" {
		t.Error("missing error message")
	}
	wantStatus(t, do(t, h, "GET", "/books/abc", ""), http.StatusBadRequest)
	wantStatus(t, do(t, h, "GET", "/books/0", ""), http.StatusBadRequest)
	wantStatus(t, do(t, h, "PATCH", "/books/1", ""), http.StatusMethodNotAllowed)
}

func TestPersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := NewStore(path)
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	wantStatus(t, do(t, NewHandler(store), "POST", "/books", dune), http.StatusCreated)
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	store, err = NewStore(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer store.Close()
	got := decode[Book](t, do(t, NewHandler(store), "GET", "/books/1", ""))
	if got.Title != "Dune" {
		t.Errorf("after reopen = %+v, want Dune", got)
	}
}
