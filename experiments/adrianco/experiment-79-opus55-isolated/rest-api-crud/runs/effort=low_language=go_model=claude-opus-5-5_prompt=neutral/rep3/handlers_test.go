package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
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
		t.Errorf("Content-Type = %q, want application/json", ct)
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
		t.Errorf("got = %+v, want %+v", got, want)
	}
}

func TestCreateValidation(t *testing.T) {
	h := newTestHandler(t)

	cases := []struct {
		name, body string
		status     int
		field      string
	}{
		{"missing title", `{"author":"A"}`, http.StatusUnprocessableEntity, "title"},
		{"missing author", `{"title":"T"}`, http.StatusUnprocessableEntity, "author"},
		{"blank title", `{"title":"   ","author":"A"}`, http.StatusUnprocessableEntity, "title"},
		{"negative year", `{"title":"T","author":"A","year":-1}`, http.StatusUnprocessableEntity, "year"},
		{"malformed json", `{"title":`, http.StatusBadRequest, ""},
		{"wrong type", `{"title":"T","author":"A","year":"x"}`, http.StatusBadRequest, ""},
		{"empty body", ``, http.StatusBadRequest, ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := do(t, h, "POST", "/books", tc.body)
			wantStatus(t, rec, tc.status)
			resp := decode[struct {
				Error  string            `json:"error"`
				Fields map[string]string `json:"fields"`
			}](t, rec)
			if resp.Error == "" {
				t.Error("expected an error message")
			}
			if tc.field != "" && resp.Fields[tc.field] == "" {
				t.Errorf("expected a problem for field %q, got %v", tc.field, resp.Fields)
			}
		})
	}

	// Nothing invalid should have been stored.
	if books := decode[[]Book](t, do(t, h, "GET", "/books", "")); len(books) != 0 {
		t.Errorf("expected no books, got %v", books)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, "GET", "/books", "")
	wantStatus(t, rec, http.StatusOK)
	if body := strings.TrimSpace(rec.Body.String()); body != "[]" {
		t.Errorf("empty list body = %q, want []", body)
	}

	for _, body := range []string{
		dune,
		`{"title":"Emma","author":"Jane Austen","year":1815}`,
		`{"title":"Children of Dune","author":"Frank Herbert","year":1976}`,
	} {
		wantStatus(t, do(t, h, "POST", "/books", body), http.StatusCreated)
	}

	if books := decode[[]Book](t, do(t, h, "GET", "/books", "")); len(books) != 3 {
		t.Fatalf("got %d books, want 3", len(books))
	}

	books := decode[[]Book](t, do(t, h, "GET", "/books?author=frank+herbert", ""))
	if len(books) != 2 {
		t.Fatalf("got %d books for author filter, want 2", len(books))
	}
	for _, b := range books {
		if b.Author != "Frank Herbert" {
			t.Errorf("unexpected author %q in filtered list", b.Author)
		}
	}

	if books := decode[[]Book](t, do(t, h, "GET", "/books?author=Nobody", "")); len(books) != 0 {
		t.Errorf("got %d books for unknown author, want 0", len(books))
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
		t.Errorf("stored = %+v, want %+v", got, want)
	}

	wantStatus(t, do(t, h, "PUT", "/books/1", `{"title":"","author":"X"}`), http.StatusUnprocessableEntity)
	wantStatus(t, do(t, h, "PUT", "/books/99", dune), http.StatusNotFound)
}

func TestDelete(t *testing.T) {
	h := newTestHandler(t)
	wantStatus(t, do(t, h, "POST", "/books", dune), http.StatusCreated)

	rec := do(t, h, "DELETE", "/books/1", "")
	wantStatus(t, rec, http.StatusNoContent)
	if rec.Body.Len() != 0 {
		t.Errorf("expected empty body, got %q", rec.Body.String())
	}

	wantStatus(t, do(t, h, "GET", "/books/1", ""), http.StatusNotFound)
	wantStatus(t, do(t, h, "DELETE", "/books/1", ""), http.StatusNotFound)
}

func TestNotFoundAndBadID(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, "GET", "/books/42", "")
	wantStatus(t, rec, http.StatusNotFound)
	if decode[map[string]string](t, rec)["error"] == "" {
		t.Error("expected an error message")
	}

	wantStatus(t, do(t, h, "GET", "/books/abc", ""), http.StatusBadRequest)
	wantStatus(t, do(t, h, "DELETE", "/books/0", ""), http.StatusBadRequest)
	wantStatus(t, do(t, h, "PATCH", "/books/1", ""), http.StatusMethodNotAllowed)
}

func TestPersistsToFile(t *testing.T) {
	path := t.TempDir() + "/books.db"

	store, err := NewStore(path)
	if err != nil {
		t.Fatal(err)
	}
	wantStatus(t, do(t, NewHandler(store), "POST", "/books", dune), http.StatusCreated)
	store.Close()

	store, err = NewStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer store.Close()
	if got := decode[Book](t, do(t, NewHandler(store), "GET", "/books/1", "")); got.Title != "Dune" {
		t.Errorf("after reopen got %+v, want Dune", got)
	}
}
