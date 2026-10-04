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
	if rec.Body.Len() > 0 {
		if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
			t.Errorf("%s %s: Content-Type = %q, want application/json", method, path, ct)
		}
	}
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

func mustCreate(t *testing.T, h http.Handler, body string) Book {
	t.Helper()
	rec := do(t, h, http.MethodPost, "/books", body)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: status = %d, body = %s", rec.Code, rec.Body.String())
	}
	return decode[Book](t, rec)
}

func TestHealth(t *testing.T) {
	rec := do(t, newTestHandler(t), http.MethodGet, "/health", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if got := decode[map[string]string](t, rec)["status"]; got != "ok" {
		t.Errorf("status field = %q, want ok", got)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, http.MethodPost, "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("status = %d, want 201; body = %s", rec.Code, rec.Body.String())
	}
	created := decode[Book](t, rec)
	want := Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"}
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
	cases := []struct {
		name, body string
		wantStatus int
	}{
		{"missing title", `{"author":"A"}`, http.StatusBadRequest},
		{"missing author", `{"title":"T"}`, http.StatusBadRequest},
		{"blank title", `{"title":"   ","author":"A"}`, http.StatusBadRequest},
		{"empty object", `{}`, http.StatusBadRequest},
		{"negative year", `{"title":"T","author":"A","year":-1}`, http.StatusBadRequest},
		{"wrong type", `{"title":"T","author":"A","year":"1999"}`, http.StatusBadRequest},
		{"malformed json", `{"title":`, http.StatusBadRequest},
		{"empty body", ``, http.StatusBadRequest},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := do(t, h, http.MethodPost, "/books", tc.body)
			if rec.Code != tc.wantStatus {
				t.Fatalf("status = %d, want %d; body = %s", rec.Code, tc.wantStatus, rec.Body.String())
			}
			if decode[map[string]any](t, rec)["error"] == nil {
				t.Errorf("response has no error field: %s", rec.Body.String())
			}
		})
	}

	// Nothing should have been stored by the rejected requests.
	if books := decode[[]Book](t, do(t, h, http.MethodGet, "/books", "")); len(books) != 0 {
		t.Errorf("books after invalid creates = %+v, want none", books)
	}
}

func TestValidationReportsAllProblems(t *testing.T) {
	rec := do(t, newTestHandler(t), http.MethodPost, "/books", `{}`)
	body := rec.Body.String()
	for _, want := range []string{"title is required", "author is required"} {
		if !strings.Contains(body, want) {
			t.Errorf("body %s does not mention %q", body, want)
		}
	}
}

func TestListBooksAndAuthorFilter(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, http.MethodGet, "/books", "")
	if rec.Code != http.StatusOK || strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Fatalf("empty list: status = %d, body = %q, want 200 []", rec.Code, rec.Body.String())
	}

	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	mustCreate(t, h, `{"title":"Emma","author":"Jane Austen","year":1815}`)
	mustCreate(t, h, `{"title":"Persuasion","author":"Jane Austen","year":1817}`)

	if books := decode[[]Book](t, do(t, h, http.MethodGet, "/books", "")); len(books) != 3 {
		t.Fatalf("list all: got %d books, want 3", len(books))
	}

	for _, query := range []string{"Jane+Austen", "jane%20austen"} {
		books := decode[[]Book](t, do(t, h, http.MethodGet, "/books?author="+query, ""))
		if len(books) != 2 || books[0].Title != "Emma" || books[1].Title != "Persuasion" {
			t.Errorf("author=%s: got %+v, want Emma and Persuasion", query, books)
		}
	}

	rec = do(t, h, http.MethodGet, "/books?author=Nobody", "")
	if rec.Code != http.StatusOK || strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Errorf("no match: status = %d, body = %q, want 200 []", rec.Code, rec.Body.String())
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestHandler(t)
	mustCreate(t, h, `{"title":"Dune","author":"F. Herbert","year":1965,"isbn":"x"}`)

	rec := do(t, h, http.MethodPut, "/books/1",
		`{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"y"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body = %s", rec.Code, rec.Body.String())
	}
	want := Book{ID: 1, Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969, ISBN: "y"}
	if got := decode[Book](t, rec); got != want {
		t.Errorf("response = %+v, want %+v", got, want)
	}
	if got := decode[Book](t, do(t, h, http.MethodGet, "/books/1", "")); got != want {
		t.Errorf("persisted = %+v, want %+v", got, want)
	}

	// Invalid updates are rejected and leave the book untouched.
	if rec := do(t, h, http.MethodPut, "/books/1", `{"title":"","author":"X"}`); rec.Code != http.StatusBadRequest {
		t.Errorf("invalid update status = %d, want 400", rec.Code)
	}
	if got := decode[Book](t, do(t, h, http.MethodGet, "/books/1", "")); got != want {
		t.Errorf("after invalid update = %+v, want %+v", got, want)
	}

	if rec := do(t, h, http.MethodPut, "/books/99", `{"title":"T","author":"A"}`); rec.Code != http.StatusNotFound {
		t.Errorf("update missing status = %d, want 404", rec.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	h := newTestHandler(t)
	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert"}`)

	rec := do(t, h, http.MethodDelete, "/books/1", "")
	if rec.Code != http.StatusNoContent || rec.Body.Len() != 0 {
		t.Fatalf("delete: status = %d, body = %q, want 204 with empty body", rec.Code, rec.Body.String())
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
	cases := []struct {
		method, path string
		wantStatus   int
	}{
		{http.MethodGet, "/books/42", http.StatusNotFound},
		{http.MethodGet, "/books/abc", http.StatusBadRequest},
		{http.MethodGet, "/books/0", http.StatusBadRequest},
		{http.MethodDelete, "/books/abc", http.StatusBadRequest},
		{http.MethodPut, "/books/abc", http.StatusBadRequest},
		{http.MethodPatch, "/books/1", http.StatusMethodNotAllowed},
		{http.MethodGet, "/nope", http.StatusNotFound},
	}
	for _, tc := range cases {
		rec := do(t, h, tc.method, tc.path, `{"title":"T","author":"A"}`)
		if rec.Code != tc.wantStatus {
			t.Errorf("%s %s: status = %d, want %d", tc.method, tc.path, rec.Code, tc.wantStatus)
		}
		if decode[map[string]string](t, rec)["error"] == "" {
			t.Errorf("%s %s: no error field in %s", tc.method, tc.path, rec.Body.String())
		}
	}
}

func TestDataPersistsAcrossReopen(t *testing.T) {
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
		t.Errorf("after reopen = %+v, want Dune by Frank Herbert (1965)", got)
	}
}
