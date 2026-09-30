package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	store, err := NewStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatal(err)
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
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode %q: %v", rec.Body.String(), err)
	}
	return v
}

func expectStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d (body: %s)", rec.Code, want, rec.Body.String())
	}
}

func TestHealth(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, "GET", "/health", "")
	expectStatus(t, rec, http.StatusOK)
	if got := decode[map[string]string](t, rec)["status"]; got != "ok" {
		t.Fatalf("status = %q", got)
	}
}

func TestCreateAndGet(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, "POST", "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	expectStatus(t, rec, http.StatusCreated)
	created := decode[Book](t, rec)
	if created.ID == 0 || created.Title != "Dune" || created.Year != 1965 {
		t.Fatalf("unexpected book: %+v", created)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Fatalf("Location = %q", loc)
	}

	rec = do(t, h, "GET", "/books/1", "")
	expectStatus(t, rec, http.StatusOK)
	if got := decode[Book](t, rec); got != created {
		t.Fatalf("got %+v, want %+v", got, created)
	}
}

func TestValidation(t *testing.T) {
	h := newTestServer(t)
	cases := map[string]struct {
		body   string
		status int
	}{
		"missing title":  {`{"author":"A"}`, http.StatusUnprocessableEntity},
		"blank title":    {`{"title":"   ","author":"A"}`, http.StatusUnprocessableEntity},
		"missing author": {`{"title":"T"}`, http.StatusUnprocessableEntity},
		"negative year":  {`{"title":"T","author":"A","year":-1}`, http.StatusUnprocessableEntity},
		"malformed json": {`{"title":`, http.StatusBadRequest},
		"wrong type":     {`{"title":"T","author":"A","year":"x"}`, http.StatusBadRequest},
		"unknown field":  {`{"title":"T","author":"A","foo":1}`, http.StatusBadRequest},
		"empty body":     {``, http.StatusBadRequest},
	}
	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			expectStatus(t, do(t, h, "POST", "/books", tc.body), tc.status)
			// PUT validates the body before looking up the book.
			expectStatus(t, do(t, h, "PUT", "/books/1", tc.body), tc.status)
		})
	}
	if books := decode[[]Book](t, do(t, h, "GET", "/books", "")); len(books) != 0 {
		t.Fatalf("invalid requests created books: %+v", books)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	h := newTestServer(t)
	expectStatus(t, do(t, h, "GET", "/books", ""), http.StatusOK)
	if got := do(t, h, "GET", "/books", "").Body.String(); strings.TrimSpace(got) != "[]" {
		t.Fatalf("empty list = %q, want []", got)
	}

	for _, b := range []string{
		`{"title":"Dune","author":"Frank Herbert"}`,
		`{"title":"Emma","author":"Jane Austen"}`,
		`{"title":"Persuasion","author":"Jane Austen"}`,
	} {
		expectStatus(t, do(t, h, "POST", "/books", b), http.StatusCreated)
	}

	if all := decode[[]Book](t, do(t, h, "GET", "/books", "")); len(all) != 3 {
		t.Fatalf("len(all) = %d", len(all))
	}
	austen := decode[[]Book](t, do(t, h, "GET", "/books?author=Jane+Austen", ""))
	if len(austen) != 2 || austen[0].Title != "Emma" || austen[1].Title != "Persuasion" {
		t.Fatalf("austen = %+v", austen)
	}
	none := do(t, h, "GET", "/books?author=Nobody", "")
	expectStatus(t, none, http.StatusOK)
	if strings.TrimSpace(none.Body.String()) != "[]" {
		t.Fatalf("no-match body = %q", none.Body.String())
	}
}

func TestUpdate(t *testing.T) {
	h := newTestServer(t)
	expectStatus(t, do(t, h, "POST", "/books", `{"title":"Old","author":"A","year":2000}`), http.StatusCreated)

	rec := do(t, h, "PUT", "/books/1", `{"title":"New","author":"B","year":2001,"isbn":"123"}`)
	expectStatus(t, rec, http.StatusOK)
	want := Book{ID: 1, Title: "New", Author: "B", Year: 2001, ISBN: "123"}
	if got := decode[Book](t, rec); got != want {
		t.Fatalf("got %+v, want %+v", got, want)
	}
	if got := decode[Book](t, do(t, h, "GET", "/books/1", "")); got != want {
		t.Fatalf("persisted %+v, want %+v", got, want)
	}

	expectStatus(t, do(t, h, "PUT", "/books/99", `{"title":"x","author":"y"}`), http.StatusNotFound)
}

func TestDelete(t *testing.T) {
	h := newTestServer(t)
	expectStatus(t, do(t, h, "POST", "/books", `{"title":"T","author":"A"}`), http.StatusCreated)

	expectStatus(t, do(t, h, "DELETE", "/books/1", ""), http.StatusNoContent)
	expectStatus(t, do(t, h, "GET", "/books/1", ""), http.StatusNotFound)
	expectStatus(t, do(t, h, "DELETE", "/books/1", ""), http.StatusNotFound)
}

func TestNotFoundAndBadID(t *testing.T) {
	h := newTestServer(t)
	expectStatus(t, do(t, h, "GET", "/books/42", ""), http.StatusNotFound)
	for _, id := range []string{"abc", "0", "-3"} {
		expectStatus(t, do(t, h, "GET", "/books/"+id, ""), http.StatusBadRequest)
	}
	rec := do(t, h, "GET", "/books/42", "")
	if msg := decode[map[string]string](t, rec)["error"]; msg == "" {
		t.Fatal("expected error message in JSON body")
	}
}

func TestPersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "persist.db")
	s1, err := NewStore(path)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := s1.Create(Book{Title: "T", Author: "A"}); err != nil {
		t.Fatal(err)
	}
	s1.Close()

	s2, err := NewStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer s2.Close()
	books, err := s2.List("")
	if err != nil || len(books) != 1 {
		t.Fatalf("books = %+v, err = %v", books, err)
	}
}
