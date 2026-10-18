package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("open store: %v", err)
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
	if err := json.NewDecoder(bytes.NewReader(rec.Body.Bytes())).Decode(&v); err != nil {
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

func TestHealth(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, http.MethodGet, "/health", "")
	expectStatus(t, rec, http.StatusOK)
	if got := decode[map[string]string](t, rec)["status"]; got != "ok" {
		t.Fatalf("status field = %q, want ok", got)
	}
}

func TestBookCRUD(t *testing.T) {
	h := newTestServer(t)

	// Create
	rec := do(t, h, http.MethodPost, "/books", dune)
	expectStatus(t, rec, http.StatusCreated)
	created := decode[Book](t, rec)
	if created.ID == 0 || created.Title != "Dune" || created.Year != 1965 {
		t.Fatalf("unexpected created book: %+v", created)
	}

	// Get
	rec = do(t, h, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), "")
	expectStatus(t, rec, http.StatusOK)
	if got := decode[Book](t, rec); got != created {
		t.Fatalf("get = %+v, want %+v", got, created)
	}

	// Update
	rec = do(t, h, http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10),
		`{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":""}`)
	expectStatus(t, rec, http.StatusOK)
	updated := decode[Book](t, rec)
	if updated.ID != created.ID || updated.Title != "Dune Messiah" || updated.Year != 1969 {
		t.Fatalf("unexpected updated book: %+v", updated)
	}

	// Delete
	rec = do(t, h, http.MethodDelete, "/books/"+strconv.FormatInt(created.ID, 10), "")
	expectStatus(t, rec, http.StatusNoContent)

	// Gone
	rec = do(t, h, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), "")
	expectStatus(t, rec, http.StatusNotFound)
}

func TestListWithAuthorFilter(t *testing.T) {
	h := newTestServer(t)
	expectStatus(t, do(t, h, http.MethodPost, "/books", dune), http.StatusCreated)
	expectStatus(t, do(t, h, http.MethodPost, "/books",
		`{"title":"Children of Dune","author":"Frank Herbert","year":1976}`), http.StatusCreated)
	expectStatus(t, do(t, h, http.MethodPost, "/books",
		`{"title":"Neuromancer","author":"William Gibson","year":1984}`), http.StatusCreated)

	all := decode[[]Book](t, do(t, h, http.MethodGet, "/books", ""))
	if len(all) != 3 {
		t.Fatalf("list all: got %d books, want 3", len(all))
	}

	herbert := decode[[]Book](t, do(t, h, http.MethodGet, "/books?author=Frank+Herbert", ""))
	if len(herbert) != 2 {
		t.Fatalf("filter by author: got %d books, want 2", len(herbert))
	}
	for _, b := range herbert {
		if b.Author != "Frank Herbert" {
			t.Fatalf("filter leaked book by %q", b.Author)
		}
	}

	none := decode[[]Book](t, do(t, h, http.MethodGet, "/books?author=Nobody", ""))
	if none == nil || len(none) != 0 {
		t.Fatalf("empty filter result = %#v, want empty non-nil slice", none)
	}
}

func TestValidation(t *testing.T) {
	h := newTestServer(t)

	cases := map[string]string{
		"missing title":  `{"author":"A","year":2000}`,
		"blank author":   `{"title":"T","author":"   ","year":2000}`,
		"negative year":  `{"title":"T","author":"A","year":-5}`,
		"malformed JSON": `{"title":`,
		"unknown field":  `{"title":"T","author":"A","pages":10}`,
		"empty body":     ``,
	}
	for name, body := range cases {
		t.Run(name, func(t *testing.T) {
			expectStatus(t, do(t, h, http.MethodPost, "/books", body), http.StatusBadRequest)
		})
	}

	rec := do(t, h, http.MethodPost, "/books", `{"author":"A"}`)
	body := decode[map[string]any](t, rec)
	fields, _ := body["fields"].(map[string]any)
	if _, ok := fields["title"]; !ok {
		t.Fatalf("expected title field error, got %v", body)
	}
}

func TestNotFoundAndBadIDs(t *testing.T) {
	h := newTestServer(t)

	expectStatus(t, do(t, h, http.MethodGet, "/books/999", ""), http.StatusNotFound)
	expectStatus(t, do(t, h, http.MethodPut, "/books/999", dune), http.StatusNotFound)
	expectStatus(t, do(t, h, http.MethodDelete, "/books/999", ""), http.StatusNotFound)
	expectStatus(t, do(t, h, http.MethodGet, "/books/abc", ""), http.StatusBadRequest)
	expectStatus(t, do(t, h, http.MethodGet, "/books/0", ""), http.StatusBadRequest)
	expectStatus(t, do(t, h, http.MethodGet, "/nope", ""), http.StatusNotFound)
}
