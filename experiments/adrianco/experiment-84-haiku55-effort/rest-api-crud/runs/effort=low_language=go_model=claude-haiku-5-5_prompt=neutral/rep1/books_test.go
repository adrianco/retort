package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

func do(t *testing.T, s *Server, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	var req *http.Request
	if body == "" {
		req = httptest.NewRequest(method, path, nil)
	} else {
		req = httptest.NewRequest(method, path, bytes.NewBufferString(body))
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	s.ServeHTTP(rec, req)
	return rec
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode body %q: %v", rec.Body.String(), err)
	}
	return v
}

func expectStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d; body: %s", rec.Code, want, rec.Body.String())
	}
}

const dune = `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`

func TestCreateAndGetBook(t *testing.T) {
	s := newTestServer(t)

	rec := do(t, s, http.MethodPost, "/books", dune)
	expectStatus(t, rec, http.StatusCreated)
	created := decode[Book](t, rec)
	if created.ID == 0 || created.Title != "Dune" || created.Author != "Frank Herbert" || created.Year != 1965 {
		t.Fatalf("unexpected created book: %+v", created)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}

	rec = do(t, s, http.MethodGet, "/books/1", "")
	expectStatus(t, rec, http.StatusOK)
	got := decode[Book](t, rec)
	if got != created {
		t.Errorf("GET returned %+v, want %+v", got, created)
	}

	rec = do(t, s, http.MethodGet, "/books/999", "")
	expectStatus(t, rec, http.StatusNotFound)
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	s := newTestServer(t)
	do(t, s, http.MethodPost, "/books", dune)
	do(t, s, http.MethodPost, "/books", `{"title":"Emma","author":"Jane Austen","year":1815}`)
	do(t, s, http.MethodPost, "/books", `{"title":"Children of Dune","author":"Frank Herbert","year":1976}`)

	all := decode[[]Book](t, do(t, s, http.MethodGet, "/books", ""))
	if len(all) != 3 {
		t.Fatalf("list all: got %d books, want 3", len(all))
	}

	rec := do(t, s, http.MethodGet, "/books?author=Frank+Herbert", "")
	expectStatus(t, rec, http.StatusOK)
	filtered := decode[[]Book](t, rec)
	if len(filtered) != 2 {
		t.Fatalf("filtered: got %d books, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Frank Herbert" {
			t.Errorf("filter leaked book by %q", b.Author)
		}
	}

	empty := decode[[]Book](t, do(t, s, http.MethodGet, "/books?author=Nobody", ""))
	if empty == nil || len(empty) != 0 {
		t.Errorf("expected empty JSON array, got %v", empty)
	}
}

func TestUpdateAndDeleteBook(t *testing.T) {
	s := newTestServer(t)
	do(t, s, http.MethodPost, "/books", dune)

	rec := do(t, s, http.MethodPut, "/books/1", `{"title":"Dune (Revised)","author":"Frank Herbert","year":1966,"isbn":""}`)
	expectStatus(t, rec, http.StatusOK)
	updated := decode[Book](t, rec)
	if updated.ID != 1 || updated.Title != "Dune (Revised)" || updated.Year != 1966 {
		t.Fatalf("unexpected update result: %+v", updated)
	}

	rec = do(t, s, http.MethodPut, "/books/42", dune)
	expectStatus(t, rec, http.StatusNotFound)

	rec = do(t, s, http.MethodDelete, "/books/1", "")
	expectStatus(t, rec, http.StatusNoContent)

	rec = do(t, s, http.MethodGet, "/books/1", "")
	expectStatus(t, rec, http.StatusNotFound)

	rec = do(t, s, http.MethodDelete, "/books/1", "")
	expectStatus(t, rec, http.StatusNotFound)
}

func TestValidation(t *testing.T) {
	s := newTestServer(t)

	cases := []struct {
		name string
		body string
		code int
	}{
		{"missing title", `{"author":"A","year":2000}`, http.StatusUnprocessableEntity},
		{"blank author", `{"title":"T","author":"   ","year":2000}`, http.StatusUnprocessableEntity},
		{"year too small", `{"title":"T","author":"A","year":100}`, http.StatusUnprocessableEntity},
		{"malformed json", `{"title":`, http.StatusBadRequest},
		{"unknown field", `{"title":"T","author":"A","year":2000,"pages":3}`, http.StatusBadRequest},
		{"empty body", ``, http.StatusBadRequest},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := do(t, s, http.MethodPost, "/books", tc.body)
			expectStatus(t, rec, tc.code)
		})
	}

	rec := do(t, s, http.MethodPost, "/books", `{"author":"","year":2000}`)
	body := decode[struct {
		Fields map[string]string `json:"fields"`
	}](t, rec)
	if body.Fields["title"] == "" || body.Fields["author"] == "" {
		t.Errorf("expected title and author field errors, got %v", body.Fields)
	}

	rec = do(t, s, http.MethodGet, "/books/abc", "")
	expectStatus(t, rec, http.StatusBadRequest)
}

func TestHealth(t *testing.T) {
	s := newTestServer(t)
	rec := do(t, s, http.MethodGet, "/health", "")
	expectStatus(t, rec, http.StatusOK)
	if h := decode[map[string]string](t, rec); h["status"] != "ok" {
		t.Errorf("health = %v, want status ok", h)
	}
}
