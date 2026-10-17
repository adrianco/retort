package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
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

func do(t *testing.T, srv http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode body: %v", err)
		}
	}
	req := httptest.NewRequest(method, path, &buf)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	return rec
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.NewDecoder(rec.Body).Decode(&v); err != nil {
		t.Fatalf("decode response %q: %v", rec.Body.String(), err)
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
	srv := newTestServer(t)
	rec := do(t, srv, http.MethodGet, "/health", nil)
	expectStatus(t, rec, http.StatusOK)
	got := decode[map[string]string](t, rec)
	if got["status"] != "ok" {
		t.Fatalf("health status = %q, want ok", got["status"])
	}
}

func TestBookCRUDLifecycle(t *testing.T) {
	srv := newTestServer(t)

	// Create
	rec := do(t, srv, http.MethodPost, "/books", BookInput{
		Title: "The Go Programming Language", Author: "Donovan", Year: 2015, ISBN: "978-0134190570",
	})
	expectStatus(t, rec, http.StatusCreated)
	created := decode[Book](t, rec)
	if created.ID == 0 || created.Title != "The Go Programming Language" || created.Year != 2015 {
		t.Fatalf("unexpected created book: %+v", created)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/"+itoa(created.ID) {
		t.Fatalf("Location = %q", loc)
	}
	path := "/books/" + itoa(created.ID)

	// Get
	rec = do(t, srv, http.MethodGet, path, nil)
	expectStatus(t, rec, http.StatusOK)
	if got := decode[Book](t, rec); got != created {
		t.Fatalf("get = %+v, want %+v", got, created)
	}

	// Update
	rec = do(t, srv, http.MethodPut, path, BookInput{
		Title: "Updated Title", Author: "Donovan", Year: 2016,
	})
	expectStatus(t, rec, http.StatusOK)
	updated := decode[Book](t, rec)
	if updated.ID != created.ID || updated.Title != "Updated Title" || updated.Year != 2016 || updated.ISBN != "" {
		t.Fatalf("unexpected updated book: %+v", updated)
	}

	// Delete
	rec = do(t, srv, http.MethodDelete, path, nil)
	expectStatus(t, rec, http.StatusNoContent)

	rec = do(t, srv, http.MethodGet, path, nil)
	expectStatus(t, rec, http.StatusNotFound)
}

func TestListAndAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	for _, in := range []BookInput{
		{Title: "A", Author: "Ursula K. Le Guin"},
		{Title: "B", Author: "Terry Pratchett"},
		{Title: "C", Author: "ursula k. le guin"},
	} {
		expectStatus(t, do(t, srv, http.MethodPost, "/books", in), http.StatusCreated)
	}

	rec := do(t, srv, http.MethodGet, "/books", nil)
	expectStatus(t, rec, http.StatusOK)
	if all := decode[[]Book](t, rec); len(all) != 3 {
		t.Fatalf("list all = %d books, want 3", len(all))
	}

	rec = do(t, srv, http.MethodGet, "/books?author=Ursula%20K.%20Le%20Guin", nil)
	expectStatus(t, rec, http.StatusOK)
	filtered := decode[[]Book](t, rec)
	if len(filtered) != 2 {
		t.Fatalf("filtered = %d books, want 2 (case-insensitive)", len(filtered))
	}

	rec = do(t, srv, http.MethodGet, "/books?author=Nobody", nil)
	expectStatus(t, rec, http.StatusOK)
	if empty := decode[[]Book](t, rec); empty == nil || len(empty) != 0 {
		t.Fatalf("expected empty JSON array, got %v", empty)
	}
}

func TestCreateValidation(t *testing.T) {
	srv := newTestServer(t)
	cases := []struct {
		name  string
		body  BookInput
		field string
	}{
		{"missing title", BookInput{Author: "X"}, "title"},
		{"missing author", BookInput{Title: "X"}, "author"},
		{"blank title", BookInput{Title: "   ", Author: "X"}, "title"},
		{"negative year", BookInput{Title: "X", Author: "Y", Year: -1}, "year"},
		{"bad isbn", BookInput{Title: "X", Author: "Y", ISBN: "abc"}, "isbn"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := do(t, srv, http.MethodPost, "/books", tc.body)
			expectStatus(t, rec, http.StatusUnprocessableEntity)
			got := decode[struct {
				Fields map[string]string `json:"fields"`
			}](t, rec)
			if _, ok := got.Fields[tc.field]; !ok {
				t.Fatalf("expected error on field %q, got %v", tc.field, got.Fields)
			}
		})
	}
}

func TestMalformedRequests(t *testing.T) {
	srv := newTestServer(t)

	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString("{not json"))
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	expectStatus(t, rec, http.StatusBadRequest)

	rec = do(t, srv, http.MethodGet, "/books/abc", nil)
	expectStatus(t, rec, http.StatusBadRequest)

	rec = do(t, srv, http.MethodGet, "/books/0", nil)
	expectStatus(t, rec, http.StatusBadRequest)

	rec = do(t, srv, http.MethodPut, "/books/999", BookInput{Title: "X", Author: "Y"})
	expectStatus(t, rec, http.StatusNotFound)

	rec = do(t, srv, http.MethodDelete, "/books/999", nil)
	expectStatus(t, rec, http.StatusNotFound)
}

func TestValidationRejectsUpdateWithoutRequiredFields(t *testing.T) {
	srv := newTestServer(t)
	created := decode[Book](t, do(t, srv, http.MethodPost, "/books", BookInput{Title: "X", Author: "Y"}))
	rec := do(t, srv, http.MethodPut, "/books/"+itoa(created.ID), BookInput{Title: "X"})
	expectStatus(t, rec, http.StatusUnprocessableEntity)
}

func itoa(n int64) string {
	return strconv.FormatInt(n, 10)
}
