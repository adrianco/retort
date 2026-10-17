package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"testing"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

func do(t *testing.T, s *Server, method, path string, body any) *httptest.ResponseRecorder {
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
	s.ServeHTTP(rec, req)
	return rec
}

func expectStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d; body: %s", rec.Code, want, rec.Body.String())
	}
}

func decodeBookResp(t *testing.T, rec *httptest.ResponseRecorder) Book {
	t.Helper()
	var b Book
	if err := json.Unmarshal(rec.Body.Bytes(), &b); err != nil {
		t.Fatalf("decode book: %v; body: %s", err, rec.Body.String())
	}
	return b
}

func TestBookLifecycle(t *testing.T) {
	s := newTestServer(t)

	// Create
	rec := do(t, s, http.MethodPost, "/books", map[string]any{
		"title": "The Go Programming Language", "author": "Donovan & Kernighan",
		"year": 2015, "isbn": "978-0134190570",
	})
	expectStatus(t, rec, http.StatusCreated)
	created := decodeBookResp(t, rec)
	if created.ID == 0 || created.Title != "The Go Programming Language" || created.Year != 2015 {
		t.Fatalf("unexpected created book: %+v", created)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/"+strconv.FormatInt(created.ID, 10) {
		t.Errorf("Location = %q", loc)
	}

	// Get
	rec = do(t, s, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	expectStatus(t, rec, http.StatusOK)
	if got := decodeBookResp(t, rec); got != created {
		t.Errorf("get = %+v, want %+v", got, created)
	}

	// Update
	rec = do(t, s, http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10), map[string]any{
		"title": "The Go Programming Language (2nd ed)", "author": "Donovan & Kernighan",
		"year": 2026, "isbn": "",
	})
	expectStatus(t, rec, http.StatusOK)
	updated := decodeBookResp(t, rec)
	if updated.ID != created.ID || updated.Year != 2026 || updated.ISBN != "" {
		t.Errorf("unexpected updated book: %+v", updated)
	}

	// Delete
	rec = do(t, s, http.MethodDelete, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	expectStatus(t, rec, http.StatusNoContent)

	rec = do(t, s, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	expectStatus(t, rec, http.StatusNotFound)
}

func TestListWithAuthorFilter(t *testing.T) {
	s := newTestServer(t)
	for _, b := range []map[string]any{
		{"title": "A", "author": "Ursula K. Le Guin"},
		{"title": "B", "author": "Isaac Asimov"},
		{"title": "C", "author": "ursula k. le guin"},
	} {
		expectStatus(t, do(t, s, http.MethodPost, "/books", b), http.StatusCreated)
	}

	rec := do(t, s, http.MethodGet, "/books", nil)
	expectStatus(t, rec, http.StatusOK)
	var all []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &all); err != nil {
		t.Fatal(err)
	}
	if len(all) != 3 {
		t.Fatalf("len(all) = %d, want 3", len(all))
	}

	rec = do(t, s, http.MethodGet, "/books?author=Ursula+K.+Le+Guin", nil)
	expectStatus(t, rec, http.StatusOK)
	var filtered []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &filtered); err != nil {
		t.Fatal(err)
	}
	if len(filtered) != 2 {
		t.Fatalf("len(filtered) = %d, want 2", len(filtered))
	}

	rec = do(t, s, http.MethodGet, "/books?author=Nobody", nil)
	expectStatus(t, rec, http.StatusOK)
	if got := bytes.TrimSpace(rec.Body.Bytes()); string(got) != "[]" {
		t.Errorf("empty list body = %s, want []", got)
	}
}

func TestValidation(t *testing.T) {
	s := newTestServer(t)

	cases := []struct {
		name string
		body string
	}{
		{"missing title", `{"author":"X"}`},
		{"missing author", `{"title":"X"}`},
		{"blank title", `{"title":"   ","author":"X"}`},
		{"year out of range", `{"title":"X","author":"Y","year":-5}`},
		{"unknown field", `{"title":"X","author":"Y","pages":10}`},
		{"malformed json", `{"title":`},
		{"trailing data", `{"title":"X","author":"Y"} {}`},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(tc.body))
			rec := httptest.NewRecorder()
			s.ServeHTTP(rec, req)
			expectStatus(t, rec, http.StatusBadRequest)
			var e errorBody
			if err := json.Unmarshal(rec.Body.Bytes(), &e); err != nil || e.Error == "" {
				t.Errorf("expected JSON error body, got %s", rec.Body.String())
			}
		})
	}

	// PUT is validated the same way, before the ID is checked.
	rec := do(t, s, http.MethodPut, "/books/1", map[string]any{"author": "X"})
	expectStatus(t, rec, http.StatusBadRequest)

	rec = do(t, s, http.MethodGet, "/books/abc", nil)
	expectStatus(t, rec, http.StatusBadRequest)
}

func TestNotFound(t *testing.T) {
	s := newTestServer(t)
	expectStatus(t, do(t, s, http.MethodGet, "/books/999", nil), http.StatusNotFound)
	expectStatus(t, do(t, s, http.MethodPut, "/books/999", map[string]any{"title": "X", "author": "Y"}), http.StatusNotFound)
	expectStatus(t, do(t, s, http.MethodDelete, "/books/999", nil), http.StatusNotFound)
}

func TestHealth(t *testing.T) {
	s := newTestServer(t)
	rec := do(t, s, http.MethodGet, "/health", nil)
	expectStatus(t, rec, http.StatusOK)
	var body map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body["status"] != "ok" {
		t.Errorf("health status = %q", body["status"])
	}
}
