package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	db, err := OpenDB(":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	return NewServer(db)
}

func do(t *testing.T, s *Server, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	rec := httptest.NewRecorder()
	s.ServeHTTP(rec, req)
	return rec
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode %q: %v", rec.Body.String(), err)
	}
	return v
}

const dune = `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`

func TestHealth(t *testing.T) {
	s := newTestServer(t)
	rec := do(t, s, http.MethodGet, "/health", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if got := decode[map[string]string](t, rec)["status"]; got != "ok" {
		t.Fatalf("status = %q, want ok", got)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	s := newTestServer(t)
	rec := do(t, s, http.MethodPost, "/books", dune)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d, body %s", rec.Code, rec.Body)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Fatalf("content-type = %q", ct)
	}
	created := decode[Book](t, rec)
	if created.ID == 0 || created.Title != "Dune" || created.Author != "Frank Herbert" ||
		created.Year != 1965 || created.ISBN != "9780441013593" {
		t.Fatalf("unexpected book: %+v", created)
	}

	rec = do(t, s, http.MethodGet, "/books/1", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("get status = %d", rec.Code)
	}
	if got := decode[Book](t, rec); got != created {
		t.Fatalf("got %+v, want %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	s := newTestServer(t)
	cases := map[string]string{
		"missing title":  `{"author":"A"}`,
		"missing author": `{"title":"T"}`,
		"blank title":    `{"title":"   ","author":"A"}`,
		"invalid json":   `{not json`,
		"empty body":     ``,
	}
	for name, body := range cases {
		t.Run(name, func(t *testing.T) {
			rec := do(t, s, http.MethodPost, "/books", body)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("status = %d, want 400", rec.Code)
			}
			if decode[map[string]any](t, rec)["error"] == nil {
				t.Fatal("expected error field")
			}
		})
	}
	rec := do(t, s, http.MethodGet, "/books", "")
	if n := len(decode[[]Book](t, rec)); n != 0 {
		t.Fatalf("invalid requests created %d books", n)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	s := newTestServer(t)

	rec := do(t, s, http.MethodGet, "/books", "")
	if rec.Code != http.StatusOK || strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Fatalf("empty list: status %d body %q", rec.Code, rec.Body)
	}

	do(t, s, http.MethodPost, "/books", dune)
	do(t, s, http.MethodPost, "/books", `{"title":"Emma","author":"Jane Austen","year":1815}`)
	do(t, s, http.MethodPost, "/books", `{"title":"Persuasion","author":"Jane Austen","year":1817}`)

	if n := len(decode[[]Book](t, do(t, s, http.MethodGet, "/books", ""))); n != 3 {
		t.Fatalf("list returned %d books, want 3", n)
	}

	books := decode[[]Book](t, do(t, s, http.MethodGet, "/books?author=Jane+Austen", ""))
	if len(books) != 2 {
		t.Fatalf("filter returned %d books, want 2", len(books))
	}
	for _, b := range books {
		if b.Author != "Jane Austen" {
			t.Fatalf("unexpected author %q", b.Author)
		}
	}

	if n := len(decode[[]Book](t, do(t, s, http.MethodGet, "/books?author=Nobody", ""))); n != 0 {
		t.Fatalf("unknown author returned %d books", n)
	}
}

func TestUpdateBook(t *testing.T) {
	s := newTestServer(t)
	do(t, s, http.MethodPost, "/books", dune)

	rec := do(t, s, http.MethodPut, "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("update status = %d, body %s", rec.Code, rec.Body)
	}
	got := decode[Book](t, do(t, s, http.MethodGet, "/books/1", ""))
	if got.Title != "Dune Messiah" || got.Year != 1969 || got.ISBN != "" {
		t.Fatalf("unexpected book after update: %+v", got)
	}

	if rec := do(t, s, http.MethodPut, "/books/1", `{"title":"","author":"X"}`); rec.Code != http.StatusBadRequest {
		t.Fatalf("invalid update status = %d, want 400", rec.Code)
	}
	if rec := do(t, s, http.MethodPut, "/books/99", dune); rec.Code != http.StatusNotFound {
		t.Fatalf("missing update status = %d, want 404", rec.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	s := newTestServer(t)
	do(t, s, http.MethodPost, "/books", dune)

	if rec := do(t, s, http.MethodDelete, "/books/1", ""); rec.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, want 204", rec.Code)
	}
	if rec := do(t, s, http.MethodGet, "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Fatalf("get after delete = %d, want 404", rec.Code)
	}
	if rec := do(t, s, http.MethodDelete, "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Fatalf("second delete = %d, want 404", rec.Code)
	}
}

func TestNotFoundAndBadID(t *testing.T) {
	s := newTestServer(t)
	if rec := do(t, s, http.MethodGet, "/books/42", ""); rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", rec.Code)
	}
	if rec := do(t, s, http.MethodGet, "/books/abc", ""); rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", rec.Code)
	}
}
