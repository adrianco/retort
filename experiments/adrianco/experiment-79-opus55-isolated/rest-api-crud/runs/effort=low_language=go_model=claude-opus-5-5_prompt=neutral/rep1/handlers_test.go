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
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
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

func wantStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d (body: %s)", rec.Code, want, rec.Body.String())
	}
}

const dune = `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`

func TestHealth(t *testing.T) {
	rec := do(t, newTestServer(t), "GET", "/health", "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[map[string]string](t, rec)["status"]; got != "ok" {
		t.Errorf("status = %q, want ok", got)
	}
}

func TestCreateAndGet(t *testing.T) {
	h := newTestServer(t)

	rec := do(t, h, "POST", "/books", dune)
	wantStatus(t, rec, http.StatusCreated)
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q", ct)
	}
	created := decode[Book](t, rec)
	want := Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"}
	if created.ID == 0 || created != want {
		t.Fatalf("created = %+v, want %+v", created, want)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q", loc)
	}

	rec = do(t, h, "GET", "/books/1", "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[Book](t, rec); got != want {
		t.Errorf("got %+v, want %+v", got, want)
	}
}

func TestCreateValidation(t *testing.T) {
	h := newTestServer(t)
	cases := map[string]string{
		"missing title":  `{"author":"A"}`,
		"missing author": `{"title":"T"}`,
		"blank title":    `{"title":"   ","author":"A"}`,
		"negative year":  `{"title":"T","author":"A","year":-1}`,
		"malformed json": `{"title":`,
		"wrong type":     `{"title":"T","author":"A","year":"x"}`,
		"empty body":     ``,
	}
	for name, body := range cases {
		t.Run(name, func(t *testing.T) {
			rec := do(t, h, "POST", "/books", body)
			wantStatus(t, rec, http.StatusBadRequest)
			if decode[map[string]any](t, rec)["error"] == nil {
				t.Errorf("no error field in %s", rec.Body.String())
			}
		})
	}

	rec := do(t, h, "GET", "/books", "")
	if got := decode[[]Book](t, rec); len(got) != 0 {
		t.Errorf("invalid requests stored books: %+v", got)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	h := newTestServer(t)

	rec := do(t, h, "GET", "/books", "")
	wantStatus(t, rec, http.StatusOK)
	if body := strings.TrimSpace(rec.Body.String()); body != "[]" {
		t.Errorf("empty list body = %q, want []", body)
	}

	for _, b := range []string{
		dune,
		`{"title":"Emma","author":"Jane Austen","year":1815}`,
		`{"title":"Persuasion","author":"Jane Austen","year":1817}`,
	} {
		wantStatus(t, do(t, h, "POST", "/books", b), http.StatusCreated)
	}

	if got := decode[[]Book](t, do(t, h, "GET", "/books", "")); len(got) != 3 {
		t.Fatalf("got %d books, want 3", len(got))
	}

	got := decode[[]Book](t, do(t, h, "GET", "/books?author=Jane+Austen", ""))
	if len(got) != 2 || got[0].Title != "Emma" || got[1].Title != "Persuasion" {
		t.Errorf("filtered = %+v", got)
	}

	if got := decode[[]Book](t, do(t, h, "GET", "/books?author=Nobody", "")); len(got) != 0 {
		t.Errorf("unknown author returned %+v", got)
	}
}

func TestUpdate(t *testing.T) {
	h := newTestServer(t)
	wantStatus(t, do(t, h, "POST", "/books", dune), http.StatusCreated)

	rec := do(t, h, "PUT", "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
	wantStatus(t, rec, http.StatusOK)

	got := decode[Book](t, do(t, h, "GET", "/books/1", ""))
	want := Book{ID: 1, Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969}
	if got != want {
		t.Errorf("got %+v, want %+v", got, want)
	}

	wantStatus(t, do(t, h, "PUT", "/books/1", `{"title":"","author":"X"}`), http.StatusBadRequest)
	wantStatus(t, do(t, h, "PUT", "/books/99", dune), http.StatusNotFound)
}

func TestDelete(t *testing.T) {
	h := newTestServer(t)
	wantStatus(t, do(t, h, "POST", "/books", dune), http.StatusCreated)

	wantStatus(t, do(t, h, "DELETE", "/books/1", ""), http.StatusNoContent)
	wantStatus(t, do(t, h, "GET", "/books/1", ""), http.StatusNotFound)
	wantStatus(t, do(t, h, "DELETE", "/books/1", ""), http.StatusNotFound)
}

func TestBadIDAndNotFound(t *testing.T) {
	h := newTestServer(t)
	wantStatus(t, do(t, h, "GET", "/books/abc", ""), http.StatusBadRequest)
	wantStatus(t, do(t, h, "GET", "/books/0", ""), http.StatusBadRequest)
	wantStatus(t, do(t, h, "GET", "/books/42", ""), http.StatusNotFound)
	wantStatus(t, do(t, h, "PATCH", "/books/1", ""), http.StatusMethodNotAllowed)
}

func TestPersistsToFile(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := NewStore(path)
	if err != nil {
		t.Fatal(err)
	}
	wantStatus(t, do(t, NewServer(store), "POST", "/books", dune), http.StatusCreated)
	store.Close()

	store, err = NewStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer store.Close()
	got := decode[Book](t, do(t, NewServer(store), "GET", "/books/1", ""))
	if got.Title != "Dune" {
		t.Errorf("after reopen got %+v", got)
	}
}
