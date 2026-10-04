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
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode %q: %v", rec.Body.String(), err)
	}
	return v
}

func mustCreate(t *testing.T, h http.Handler, body string) Book {
	t.Helper()
	rec := do(t, h, http.MethodPost, "/books", body)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d, body = %s", rec.Code, rec.Body)
	}
	return decode[Book](t, rec)
}

func TestHealth(t *testing.T) {
	h := newTestHandler(t)
	rec := do(t, h, http.MethodGet, "/health", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if got := decode[map[string]string](t, rec)["status"]; got != "ok" {
		t.Errorf("status = %q, want ok", got)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, http.MethodPost, "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("status = %d, want 201; body = %s", rec.Code, rec.Body)
	}
	created := decode[Book](t, rec)
	want := Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"}
	if created.ID <= 0 || created != want {
		t.Errorf("created = %+v, want %+v with positive ID", created, want)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}

	rec = do(t, h, http.MethodGet, "/books/1", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("get status = %d, want 200", rec.Code)
	}
	if got := decode[Book](t, rec); got != want {
		t.Errorf("got = %+v, want %+v", got, want)
	}
}

func TestCreateValidation(t *testing.T) {
	h := newTestHandler(t)

	tests := []struct {
		name       string
		body       string
		wantFields []string
	}{
		{"missing title", `{"author":"A"}`, []string{"title"}},
		{"missing author", `{"title":"T"}`, []string{"author"}},
		{"missing both", `{}`, []string{"title", "author"}},
		{"blank title", `{"title":"   ","author":"A"}`, []string{"title"}},
		{"negative year", `{"title":"T","author":"A","year":-1}`, []string{"year"}},
		{"malformed JSON", `{"title":`, nil},
		{"wrong type", `{"title":"T","author":"A","year":"1965"}`, nil},
		{"trailing data", `{"title":"T","author":"A"}{}`, nil},
		{"empty body", ``, nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, h, http.MethodPost, "/books", tt.body)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("status = %d, want 400; body = %s", rec.Code, rec.Body)
			}
			resp := decode[errorResponse](t, rec)
			if resp.Error == "" {
				t.Error("error message is empty")
			}
			if len(resp.Details) != len(tt.wantFields) {
				t.Errorf("details = %v, want fields %v", resp.Details, tt.wantFields)
			}
			for _, f := range tt.wantFields {
				if resp.Details[f] == "" {
					t.Errorf("details missing field %q: %v", f, resp.Details)
				}
			}
		})
	}

	// Nothing should have been stored by the rejected requests.
	if books := decode[[]Book](t, do(t, h, http.MethodGet, "/books", "")); len(books) != 0 {
		t.Errorf("books = %v, want none", books)
	}
}

func TestListBooks(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, http.MethodGet, "/books", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if body := strings.TrimSpace(rec.Body.String()); body != "[]" {
		t.Errorf("empty list body = %s, want []", body)
	}

	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	mustCreate(t, h, `{"title":"Emma","author":"Jane Austen","year":1815}`)
	mustCreate(t, h, `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)

	if books := decode[[]Book](t, do(t, h, http.MethodGet, "/books", "")); len(books) != 3 {
		t.Errorf("len(all) = %d, want 3", len(books))
	}

	books := decode[[]Book](t, do(t, h, http.MethodGet, "/books?author=Frank+Herbert", ""))
	if len(books) != 2 || books[0].Title != "Dune" || books[1].Title != "Dune Messiah" {
		t.Errorf("filtered = %+v, want Dune and Dune Messiah", books)
	}

	books = decode[[]Book](t, do(t, h, http.MethodGet, "/books?author=jane%20austen", ""))
	if len(books) != 1 || books[0].Title != "Emma" {
		t.Errorf("case-insensitive filter = %+v, want Emma", books)
	}

	books = decode[[]Book](t, do(t, h, http.MethodGet, "/books?author=Nobody", ""))
	if len(books) != 0 {
		t.Errorf("unknown author = %+v, want none", books)
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestHandler(t)
	mustCreate(t, h, `{"title":"Dune","author":"F. Herbert","year":1965,"isbn":"123"}`)

	rec := do(t, h, http.MethodPut, "/books/1", `{"title":"Dune","author":"Frank Herbert","year":1966}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body = %s", rec.Code, rec.Body)
	}
	// PUT replaces the whole resource, so the omitted isbn is cleared.
	want := Book{ID: 1, Title: "Dune", Author: "Frank Herbert", Year: 1966}
	if got := decode[Book](t, rec); got != want {
		t.Errorf("response = %+v, want %+v", got, want)
	}
	if got := decode[Book](t, do(t, h, http.MethodGet, "/books/1", "")); got != want {
		t.Errorf("stored = %+v, want %+v", got, want)
	}

	if rec := do(t, h, http.MethodPut, "/books/1", `{"title":"Dune"}`); rec.Code != http.StatusBadRequest {
		t.Errorf("invalid update status = %d, want 400", rec.Code)
	}
	if got := decode[Book](t, do(t, h, http.MethodGet, "/books/1", "")); got != want {
		t.Errorf("after rejected update = %+v, want %+v", got, want)
	}

	if rec := do(t, h, http.MethodPut, "/books/99", `{"title":"T","author":"A"}`); rec.Code != http.StatusNotFound {
		t.Errorf("missing update status = %d, want 404", rec.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	h := newTestHandler(t)
	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert"}`)

	rec := do(t, h, http.MethodDelete, "/books/1", "")
	if rec.Code != http.StatusNoContent {
		t.Fatalf("status = %d, want 204", rec.Code)
	}
	if rec.Body.Len() != 0 {
		t.Errorf("body = %q, want empty", rec.Body)
	}
	if rec := do(t, h, http.MethodGet, "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Errorf("get after delete status = %d, want 404", rec.Code)
	}
	if rec := do(t, h, http.MethodDelete, "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Errorf("second delete status = %d, want 404", rec.Code)
	}
}

func TestNotFoundAndBadID(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, http.MethodGet, "/books/42", "")
	if rec.Code != http.StatusNotFound {
		t.Errorf("status = %d, want 404", rec.Code)
	}
	if resp := decode[errorResponse](t, rec); resp.Error == "" {
		t.Error("error message is empty")
	}

	for _, id := range []string{"abc", "0", "-1", "1.5"} {
		for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
			rec := do(t, h, method, "/books/"+id, `{"title":"T","author":"A"}`)
			if rec.Code != http.StatusBadRequest {
				t.Errorf("%s /books/%s status = %d, want 400", method, id, rec.Code)
			}
		}
	}

	if rec := do(t, h, http.MethodPatch, "/books/1", ""); rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("PATCH status = %d, want 405", rec.Code)
	}
}

func TestPersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := NewStore(path)
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	mustCreate(t, NewHandler(store), `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	store, err = NewStore(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer store.Close()
	got := decode[Book](t, do(t, NewHandler(store), http.MethodGet, "/books/1", ""))
	if got.Title != "Dune" || got.Author != "Frank Herbert" || got.Year != 1965 {
		t.Errorf("after reopen = %+v", got)
	}
}
