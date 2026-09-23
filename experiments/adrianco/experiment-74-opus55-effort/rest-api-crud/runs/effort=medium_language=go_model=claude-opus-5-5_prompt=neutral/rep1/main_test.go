package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return (&Server{store: store}).Routes()
}

func do(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	var req *http.Request
	if body == "" {
		req = httptest.NewRequest(method, path, nil)
	} else {
		req = httptest.NewRequest(method, path, bytes.NewBufferString(body))
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
		t.Fatalf("decode %q: %v", rec.Body.String(), err)
	}
	return v
}

func expectStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d; body: %s", rec.Code, want, rec.Body.String())
	}
}

func TestHealth(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, "GET", "/health", "")
	expectStatus(t, rec, http.StatusOK)
	if got := decode[map[string]string](t, rec)["status"]; got != "ok" {
		t.Fatalf("status field = %q", got)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Fatalf("content-type = %q", ct)
	}
}

func TestCRUDLifecycle(t *testing.T) {
	h := newTestServer(t)

	rec := do(t, h, "POST", "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}`)
	expectStatus(t, rec, http.StatusCreated)
	created := decode[Book](t, rec)
	if created.ID == 0 || created.Title != "Dune" || created.Year != 1965 {
		t.Fatalf("unexpected created book: %+v", created)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Fatalf("Location = %q", loc)
	}

	rec = do(t, h, "GET", "/books/1", "")
	expectStatus(t, rec, http.StatusOK)
	if got := decode[Book](t, rec); got != created {
		t.Fatalf("get = %+v, want %+v", got, created)
	}

	rec = do(t, h, "PUT", "/books/1", `{"title":"Dune (Deluxe)","author":"Frank Herbert","year":2019}`)
	expectStatus(t, rec, http.StatusOK)
	if got := decode[Book](t, rec); got.Title != "Dune (Deluxe)" || got.Year != 2019 || got.ISBN != "" {
		t.Fatalf("update = %+v", got)
	}
	rec = do(t, h, "GET", "/books/1", "")
	if got := decode[Book](t, rec); got.Title != "Dune (Deluxe)" {
		t.Fatalf("update not persisted: %+v", got)
	}

	rec = do(t, h, "DELETE", "/books/1", "")
	expectStatus(t, rec, http.StatusNoContent)
	expectStatus(t, do(t, h, "GET", "/books/1", ""), http.StatusNotFound)
	expectStatus(t, do(t, h, "DELETE", "/books/1", ""), http.StatusNotFound)
}

func TestListWithAuthorFilter(t *testing.T) {
	h := newTestServer(t)

	rec := do(t, h, "GET", "/books", "")
	expectStatus(t, rec, http.StatusOK)
	if rec.Body.String() != "[]\n" {
		t.Fatalf("empty list body = %q, want []", rec.Body.String())
	}

	for _, body := range []string{
		`{"title":"Emma","author":"Jane Austen"}`,
		`{"title":"Persuasion","author":"Jane Austen"}`,
		`{"title":"Ulysses","author":"James Joyce"}`,
	} {
		expectStatus(t, do(t, h, "POST", "/books", body), http.StatusCreated)
	}

	all := decode[[]Book](t, do(t, h, "GET", "/books", ""))
	if len(all) != 3 {
		t.Fatalf("list all = %d books, want 3", len(all))
	}

	austen := decode[[]Book](t, do(t, h, "GET", "/books?author=jane%20austen", ""))
	if len(austen) != 2 {
		t.Fatalf("filtered = %d books, want 2", len(austen))
	}
	for _, b := range austen {
		if b.Author != "Jane Austen" {
			t.Fatalf("unexpected author %q", b.Author)
		}
	}

	none := decode[[]Book](t, do(t, h, "GET", "/books?author=Nobody", ""))
	if len(none) != 0 {
		t.Fatalf("expected no books, got %d", len(none))
	}
}

func TestValidation(t *testing.T) {
	h := newTestServer(t)

	cases := []struct {
		name, body string
		field      string
	}{
		{"missing title", `{"author":"A"}`, "title"},
		{"missing author", `{"title":"T"}`, "author"},
		{"blank title", `{"title":"   ","author":"A"}`, "title"},
		{"negative year", `{"title":"T","author":"A","year":-5}`, "year"},
		{"bad isbn", `{"title":"T","author":"A","isbn":"abc"}`, "isbn"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := do(t, h, "POST", "/books", tc.body)
			expectStatus(t, rec, http.StatusBadRequest)
			resp := decode[struct {
				Fields map[string]string `json:"fields"`
			}](t, rec)
			if _, ok := resp.Fields[tc.field]; !ok {
				t.Fatalf("expected error for field %q, got %v", tc.field, resp.Fields)
			}
		})
	}

	expectStatus(t, do(t, h, "POST", "/books", `not json`), http.StatusBadRequest)
	expectStatus(t, do(t, h, "POST", "/books", `{"title":"T","author":"A","extra":1}`), http.StatusBadRequest)

	// Update must validate as well.
	expectStatus(t, do(t, h, "POST", "/books", `{"title":"T","author":"A"}`), http.StatusCreated)
	expectStatus(t, do(t, h, "PUT", "/books/1", `{"title":"","author":"A"}`), http.StatusBadRequest)
}

func TestNotFoundAndBadIDs(t *testing.T) {
	h := newTestServer(t)
	expectStatus(t, do(t, h, "GET", "/books/999", ""), http.StatusNotFound)
	expectStatus(t, do(t, h, "PUT", "/books/999", `{"title":"T","author":"A"}`), http.StatusNotFound)
	expectStatus(t, do(t, h, "GET", "/books/abc", ""), http.StatusBadRequest)
	expectStatus(t, do(t, h, "DELETE", "/books/0", ""), http.StatusBadRequest)
	expectStatus(t, do(t, h, "PATCH", "/books/1", ""), http.StatusMethodNotAllowed)
}
